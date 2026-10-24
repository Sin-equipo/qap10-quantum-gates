"""A small, transparent QAOA experiment built with Qiskit circuits."""

from __future__ import annotations

from collections import Counter
from time import perf_counter

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from scipy.optimize import linear_sum_assignment, minimize

from .instance import QAPInstance


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


def _circuit(params: np.ndarray, n_qubits: int, p: int,
             h: np.ndarray, zz: dict[tuple[int, int], float]) -> QuantumCircuit:
    qc = QuantumCircuit(n_qubits)
    qc.h(range(n_qubits))
    for layer in range(p):
        gamma, beta = params[2 * layer:2 * layer + 2]
        for q, coeff in enumerate(h):
            if coeff:
                qc.rz(2 * gamma * coeff, q)
        for (a, b), coeff in zz.items():
            if coeff:
                qc.rzz(2 * gamma * coeff, a, b)
        for q in range(n_qubits):
            qc.rx(2 * beta, q)
    return qc


def solve_qaoa(instance: QAPInstance, *, seed: int = 7, shots: int = 2048,
               reps: int = 1, maxiter: int = 35, penalty: float | None = None) -> dict:
    """Run a statevector QAOA experiment; intentionally limited to N <= 4."""
    if instance.n > 4:
        raise ValueError("QAOA statevector está limitado a N<=4 (16 qubits)")
    if penalty is None:
        penalty = float(max(1, np.max(instance.flows) * np.max(instance.distances) * instance.n))
    offset, linear, quadratic = _qubo(instance, penalty)
    constant, h, zz = _pauli_coefficients(offset, linear, quadratic)
    rng = np.random.default_rng(seed)
    n_qubits = instance.n * instance.n

    def expectation(params: np.ndarray) -> float:
        state = Statevector.from_instruction(_circuit(params, n_qubits, reps, h, zz))
        probs = np.abs(state.data) ** 2
        energies = np.full(1 << n_qubits, constant, dtype=float)
        for q, coeff in enumerate(h):
            bits = (np.arange(1 << n_qubits) >> q) & 1
            energies += coeff * (1 - 2 * bits)
        for (a, b), coeff in zz.items():
            bits_a = (np.arange(1 << n_qubits) >> a) & 1
            bits_b = (np.arange(1 << n_qubits) >> b) & 1
            energies += coeff * (1 - 2 * bits_a) * (1 - 2 * bits_b)
        return float(probs @ energies)

    start = perf_counter()
    result = minimize(expectation, rng.uniform(0, np.pi, 2 * reps), method="COBYLA",
                      options={"maxiter": maxiter, "rhobeg": 0.5})
    # Sample optimized Qiskit statevector probabilities with a fixed seed.
    # Statevector indices use little-endian qubit numbering, matching x[i,j].
    state = Statevector.from_instruction(_circuit(result.x, n_qubits, reps, h, zz))
    counts = Counter()
    outcomes = rng.choice(len(state.data), size=shots, p=np.abs(state.data) ** 2)
    for outcome in outcomes:
        bitstring = format(int(outcome), f"0{n_qubits}b")[::-1]
        counts[bitstring] += 1
    elapsed = perf_counter() - start

    feasible_counts: Counter = Counter()
    repaired: dict[tuple[int, ...], int] = {}
    for bitstring, count in counts.items():
        score = np.asarray([int(bit) for bit in bitstring], dtype=float).reshape(instance.n, instance.n)
        rows, cols = linear_sum_assignment(-score)
        assignment = tuple(int(cols[np.where(rows == i)[0][0]]) for i in range(instance.n))
        repaired[assignment] = repaired.get(assignment, 0) + count
        if all(score[i].sum() == 1 for i in range(instance.n)) and all(
            score[:, j].sum() == 1 for j in range(instance.n)
        ):
            feasible_counts[assignment] += count
    if repaired:
        assignment, count = min(repaired.items(), key=lambda item: instance.cost(item[0]))
        cost = instance.cost(assignment)
    else:
        assignment, count, cost = None, 0, None
    return {
        "method": f"QAOA Qiskit statevector, p={reps}",
        "assignment": list(assignment) if assignment is not None else None,
        "cost": int(cost) if cost is not None else None,
        "feasible_after_repair": assignment is not None,
        "postprocessing": "reparación clásica por asignación húngara",
        "raw_feasible": bool(feasible_counts),
        "raw_feasible_shots": int(sum(feasible_counts.values())),
        "raw_feasible_fraction": float(sum(feasible_counts.values()) / shots),
        "shots": shots,
        "best_assignment_frequency": int(count),
        "penalty": penalty,
        "qubo_expected_energy": float(result.fun),
        "optimizer_iterations": int(result.nfev),
        "seconds": elapsed,
        "seed": seed,
    }
