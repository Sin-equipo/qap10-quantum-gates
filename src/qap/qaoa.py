"""A small, transparent QAOA experiment built with Qiskit circuits.

Two ansatz families are supported:

* ``"x"``: standard QAOA (Hadamard start, transverse-field RX mixer). Both
  row and column one-hot constraints are enforced only through the penalty.
* ``"xy"``: constraint-preserving ansatz. Each flight starts at a fixed
  gate (a valid permutation) and a ring XY mixer inside every row swaps the
  excitation between gates, so "one gate per flight" holds exactly in the
  noiseless circuit; only the column constraint is left to the penalty.

The Hamiltonian is normalised before the circuit is built so that the
variational angles live on a sensible scale regardless of the penalty.
"""

from __future__ import annotations

from collections import Counter
from itertools import permutations
from time import perf_counter

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit import ParameterVector
from qiskit.circuit.library import PauliEvolutionGate, XXPlusYYGate
from qiskit.quantum_info import SparsePauliOp
from qiskit.providers.fake_provider import GenericBackendV2
from qiskit_aer import AerSimulator
from qiskit_aer.primitives import SamplerV2
from scipy.optimize import linear_sum_assignment, minimize

from .instance import QAPInstance

MAX_N = 4


def _qubo(instance: QAPInstance, penalty: float) -> tuple[float, np.ndarray, dict]:
    """Build C(x) + penalty * (row one-hot violations + column violations)."""
    n = instance.n
    linear = np.zeros(n * n, dtype=float)
    quadratic: dict[tuple[int, int], float] = {}

    def add_pair(a: int, b: int, value: float) -> None:
        if a == b:
            linear[a] += value
        else:
            key = (min(a, b), max(a, b))
            quadratic[key] = quadratic.get(key, 0.0) + value

    offset = 0.0
    if instance.linear is not None:
        linear += instance.linear.reshape(-1).astype(float)
    for i in range(n):
        for k in range(i + 1, n):
            for j in range(n):
                for ell in range(n):
                    if j != ell:
                        add_pair(i * n + j, k * n + ell,
                                 float(instance.flows[i, k] * instance.distances[j, ell]))

    # Every row and column must contain exactly one selected binary variable.
    for i in range(n):
        ids = [i * n + j for j in range(n)]
        offset += penalty
        for a in ids:
            linear[a] -= penalty
        for p, a in enumerate(ids):
            for b in ids[p + 1:]:
                add_pair(a, b, 2 * penalty)
    for j in range(n):
        ids = [i * n + j for i in range(n)]
        offset += penalty
        for a in ids:
            linear[a] -= penalty
        for p, a in enumerate(ids):
            for b in ids[p + 1:]:
                add_pair(a, b, 2 * penalty)
    quadratic = {key: value for key, value in quadratic.items() if abs(value) > 1e-12}
    return offset, linear, quadratic


def _pauli_coefficients(offset: float, linear: np.ndarray,
                        quadratic: dict[tuple[int, int], float]):
    """Convert a QUBO with x=(1-Z)/2 into H=c+sum hZ+sum JZZ."""
    h = -linear / 2.0
    c = offset + float(linear.sum()) / 2.0
    zz = {}
    for (a, b), value in quadratic.items():
        c += value / 4.0
        h[a] -= value / 4.0
        h[b] -= value / 4.0
        zz[(a, b)] = value / 4.0
    return c, h, zz


def certified_penalty(instance: QAPInstance) -> float:
    """Smallest penalty from a simple bound that makes every QUBO minimum feasible.

    Leaving flight i unassigned saves at most sum_k F_ik * max(D) of assignment
    cost, while it costs at least ``penalty`` in the row term. With F, D >= 0,
    adding extra ones never lowers the cost, so any penalty above this bound
    makes the QUBO ground state a valid permutation. A non-negative linear term
    adds at most max_j L_ij to what an empty row can save.
    """
    per_row = instance.flows.sum(axis=1) * instance.distances.max()
    if instance.linear is not None:
        per_row = per_row + instance.linear.max(axis=1)
    return float(per_row.max()) + 1.0


def _energies(n_qubits: int, constant: float, h: np.ndarray, zz: dict) -> np.ndarray:
    """Diagonal of H for every basis state (little-endian, as in Qiskit)."""
    index = np.arange(1 << n_qubits)
    spins = 1 - 2 * ((index[:, None] >> np.arange(n_qubits)) & 1)
    energies = np.full(index.shape, constant, dtype=float) + spins @ h
    for (a, b), coeff in zz.items():
        energies += coeff * spins[:, a] * spins[:, b]
    return energies


def _feasibility_mask(n: int) -> np.ndarray:
    index = np.arange(1 << (n * n))
    bits = ((index[:, None] >> np.arange(n * n)) & 1).reshape(-1, n, n)
    return (bits.sum(axis=2) == 1).all(axis=1) & (bits.sum(axis=1) == 1).all(axis=1)


def _assignment_index(assignment: tuple[int, ...], n: int) -> int:
    return sum(1 << (i * n + j) for i, j in enumerate(assignment))


def _swap_term(n: int, i: int, k: int, j: int, ell: int) -> SparsePauliOp:
    """Hermitian swap |x_ij x_kl> <-> |x_il x_kj|: flights i, k exchange gates j, l."""
    n_qubits = n * n

    def ladder(q: int, raising: bool) -> SparsePauliOp:
        # x=1 is |1>; raising = |1><0| = (X - iY)/2, lowering = (X + iY)/2.
        sign = -0.5j if raising else 0.5j
        return SparsePauliOp.from_sparse_list([("X", [q], 0.5), ("Y", [q], sign)], n_qubits)

    hop = (ladder(i * n + ell, True).compose(ladder(k * n + j, True))
           .compose(ladder(i * n + j, False)).compose(ladder(k * n + ell, False)))
    return (hop + hop.adjoint()).simplify()


def _ansatz(n: int, reps: int, h: np.ndarray, zz: dict, mixer: str,
            start: tuple[int, ...] | None = None) -> QuantumCircuit:
    """Parameterised QAOA circuit with gamma_l, beta_l per layer."""
    n_qubits = n * n
    gammas = ParameterVector("gamma", reps)
    betas = ParameterVector("beta", reps)
    qc = QuantumCircuit(n_qubits)
    if mixer == "x":
        qc.h(range(n_qubits))
    else:
        # Start from one valid permutation (flight i at gate start[i]).
        start = start if start is not None else tuple(range(n))
        for i, gate in enumerate(start):
            qc.x(i * n + gate)
    swap_terms = ([_swap_term(n, i, k, j, ell) for i in range(n) for k in range(i + 1, n)
                   for j in range(n) for ell in range(j + 1, n)] if mixer == "perm" else [])
    ring = [(j, (j + 1) % n) for j in range(n)] if n > 2 else [(0, 1)]
    for layer in range(reps):
        for q, coeff in enumerate(h):
            if coeff:
                qc.rz(2 * gammas[layer] * coeff, q)
        for (a, b), coeff in zz.items():
            if coeff:
                qc.rzz(2 * gammas[layer] * coeff, a, b)
        if mixer == "x":
            for q in range(n_qubits):
                qc.rx(2 * betas[layer], q)
        elif mixer == "perm":
            # Each swap term's Pauli strings commute, so one evolution per term is
            # exact and keeps the state inside the N! permutation subspace.
            for term in swap_terms:
                qc.append(PauliEvolutionGate(term, time=betas[layer]), range(n_qubits))
        else:
            # Even then odd ring edges inside each row (flight).
            for parity in (0, 1):
                for i in range(n):
                    for edge, (j, ell) in enumerate(ring):
                        if edge % 2 == parity:
                            qc.append(XXPlusYYGate(2 * betas[layer]), [i * n + j, i * n + ell])
    return qc


def _objective(probs: np.ndarray, energies: np.ndarray, order: np.ndarray, alpha: float) -> float:
    """Expected energy (alpha=1) or CVaR_alpha: mean of the lowest alpha tail."""
    if alpha >= 1.0:
        return float(probs @ energies)
    sorted_probs = probs[order]
    cumulative = np.cumsum(sorted_probs)
    weights = np.clip(alpha - (cumulative - sorted_probs), 0.0, sorted_probs)
    return float(weights @ energies[order] / alpha)


def _resources(qc: QuantumCircuit, seed: int) -> dict:
    """Logical and transpiled size of the ansatz on a generic device."""
    backend = GenericBackendV2(num_qubits=qc.num_qubits, seed=seed)
    bound = qc.assign_parameters(np.full(qc.num_parameters, 0.1))
    compiled = transpile(bound, backend=backend, optimization_level=1, seed_transpiler=seed)
    ops = compiled.count_ops()
    two_qubit = sum(count for name, count in ops.items()
                    if name in {"cx", "cz", "ecr", "rzz", "swap", "iswap"})
    return {
        "qubits": qc.num_qubits,
        "logical_depth": int(bound.depth()),
        "transpiled_depth": int(compiled.depth()),
        "transpiled_two_qubit_gates": int(two_qubit),
        "transpile_target": "GenericBackendV2 (cx, id, rz, sx, x)",
    }


def solve_qaoa(instance: QAPInstance, *, seed: int = 7, shots: int = 2048,
               reps: int = 1, maxiter: int = 150, penalty: float | None = None,
               penalty_factor: float = 1.0, alpha: float = 1.0, mixer: str = "x",
               normalize: bool = True, resources: bool = False) -> dict:
    """Run a QAOA experiment on Aer; intentionally limited to N <= 4 (16 qubits).

    The optimiser sees the exact statevector expectation (or CVaR); the final
    distribution is then sampled with Aer's SamplerV2 using ``shots`` and ``seed``.
    """
    n = instance.n
    if n > MAX_N:
        raise ValueError(f"QAOA statevector está limitado a N<={MAX_N} ({MAX_N**2} qubits)")
    if mixer not in {"x", "xy", "perm"}:
        raise ValueError("mixer debe ser 'x', 'xy' o 'perm'")
    if penalty is None:
        penalty = certified_penalty(instance) * penalty_factor
    n_qubits = n * n
    offset, linear, quadratic = _qubo(instance, penalty)
    constant, h, zz = _pauli_coefficients(offset, linear, quadratic)
    energies = _energies(n_qubits, constant, h, zz)
    scale = max(np.abs(h).max(), max(abs(v) for v in zz.values())) if normalize else 1.0

    perms = list(permutations(range(n)))
    perm_costs = {perm: instance.cost(perm) for perm in perms}
    rng = np.random.default_rng(seed)
    # Seeded random start, so the optimum is never handed to the circuit for free.
    start = tuple(int(g) for g in rng.permutation(n)) if mixer != "x" else None
    qc = _ansatz(n, reps, h / scale, {k: v / scale for k, v in zz.items()}, mixer, start)

    feasible = _feasibility_mask(n)
    optimum = min(perm_costs.values())
    optimal_states = [_assignment_index(p, n) for p, c in perm_costs.items() if c == optimum]
    order = np.argsort(energies)

    simulator = AerSimulator(method="statevector", seed_simulator=seed)
    trainable = qc.copy()
    trainable.save_statevector()
    trainable = transpile(trainable, simulator)
    history: list[float] = []

    def probabilities(params: np.ndarray) -> np.ndarray:
        bound = trainable.assign_parameters(params)
        state = simulator.run(bound).result().get_statevector()
        return np.abs(np.asarray(state)) ** 2

    def objective(params: np.ndarray) -> float:
        value = _objective(probabilities(params), energies, order, alpha)
        history.append(value)
        return value

    # Qiskit orders parameters by name: beta[0..p-1] before gamma[0..p-1].
    initial = np.concatenate([rng.uniform(0.0, np.pi / 2, reps), rng.uniform(0.0, 0.5, reps)])

    tic = perf_counter()
    result = minimize(objective, initial, method="COBYLA",
                      options={"maxiter": maxiter, "rhobeg": 0.3})
    train_seconds = perf_counter() - tic

    probs = probabilities(result.x)
    measured = qc.assign_parameters(result.x)
    measured.measure_all()
    measured = transpile(measured, simulator)
    sampler = SamplerV2(seed=seed)
    tic = perf_counter()
    counts = sampler.run([measured], shots=shots).result()[0].data.meas.get_counts()
    sample_seconds = perf_counter() - tic

    raw_feasible: Counter = Counter()
    repaired: Counter = Counter()
    for bitstring, count in counts.items():
        x = np.asarray([int(bit) for bit in bitstring[::-1]], dtype=float).reshape(n, n)
        if (x.sum(axis=1) == 1).all() and (x.sum(axis=0) == 1).all():
            raw_feasible[tuple(int(np.argmax(row)) for row in x)] += count
        rows, cols = linear_sum_assignment(-x)
        repaired[tuple(int(cols[np.where(rows == i)[0][0]]) for i in range(n))] += count

    best_raw = min(raw_feasible, key=perm_costs.get) if raw_feasible else None
    best_repaired = min(repaired, key=perm_costs.get)
    p_opt = float(probs[optimal_states].sum())
    p_opt_uniform_bits = len(optimal_states) / (1 << n_qubits)
    p_opt_random_perm = len(optimal_states) / len(perms)
    raw_shots = int(sum(raw_feasible.values()))
    opt_shots = int(sum(c for a, c in raw_feasible.items() if perm_costs[a] == optimum))

    out = {
        "method": f"QAOA Qiskit Aer, mixer={mixer}, p={reps}, CVaR alpha={alpha}",
        "n": n,
        "qubits": n_qubits,
        "mixer": mixer,
        "start_assignment": list(start) if start is not None else None,
        "start_cost": int(perm_costs[start]) if start is not None else None,
        "reps": reps,
        "alpha": alpha,
        "penalty": penalty,
        "penalty_certified_bound": certified_penalty(instance),
        "ground_state_feasible": bool(feasible[int(np.argmin(energies))]),
        "hamiltonian_scale": float(scale),
        "seed": seed,
        "shots": shots,
        "optimum": int(optimum),
        # Exact quantities from the optimised statevector.
        "p_feasible": float(probs[feasible].sum()),
        "p_optimal": p_opt,
        "p_optimal_uniform_bitstring": p_opt_uniform_bits,
        "p_optimal_random_permutation": p_opt_random_perm,
        "gain_vs_random_permutation": p_opt / p_opt_random_perm,
        # Sampled quantities (raw = no repair).
        "raw_feasible_shots": raw_shots,
        "raw_feasible_fraction": raw_shots / shots,
        "raw_optimal_shots": opt_shots,
        "raw_best_assignment": list(best_raw) if best_raw else None,
        "raw_best_cost": int(perm_costs[best_raw]) if best_raw else None,
        "repaired_best_assignment": list(best_repaired),
        "repaired_best_cost": int(perm_costs[best_repaired]),
        "postprocessing": "reparación clásica por asignación húngara (reportada aparte)",
        "objective_final": float(result.fun),
        "objective_history": history,
        "optimizer_evaluations": int(result.nfev),
        "train_seconds": train_seconds,
        "sample_seconds": sample_seconds,
        # Backwards-compatible keys used by run_experiment.py.
        "assignment": list(best_raw) if best_raw else list(best_repaired),
        "cost": int(perm_costs[best_raw]) if best_raw else int(perm_costs[best_repaired]),
        "raw_feasible": bool(raw_feasible),
        "seconds": train_seconds + sample_seconds,
    }
    if resources:
        out["resources"] = _resources(qc, seed)
    return out
