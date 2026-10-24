"""Hybrid Large Neighbourhood Search (LNS) for the full N=10 instance.

Each iteration frees K flights, keeps the other N-K fixed, and asks a subsolver
to redistribute the K freed flights over the K gates they currently occupy.
That subproblem is itself a small QAP with an extra linear term (interaction
with the fixed flights), so the QAOA solver from ``qaoa.py`` runs it on K^2
qubits. The same loop, with the same neighbourhoods, can use a classical exact
subsolver or a random one as controls.
"""

from __future__ import annotations

from itertools import permutations
from time import perf_counter

import numpy as np

from .instance import QAPInstance
from .qaoa import solve_qaoa

SUBSOLVERS = ("qaoa", "exact", "random")


def subproblem(instance: QAPInstance, assignment: list[int],
               flights: list[int]) -> tuple[QAPInstance, list[int], int]:
    """Sub-QAP for ``flights``; returns (subinstance, their gates, constant cost).

    Sub-flight a is ``flights[a]`` and sub-gate b is ``gates[b]``. For any sub
    permutation s, the full cost equals ``constant + sub.cost(s)``.
    """
    gates = [assignment[i] for i in flights]
    fixed = [k for k in range(instance.n) if k not in flights]
    flows = instance.flows[np.ix_(flights, flights)]
    distances = instance.distances[np.ix_(gates, gates)]
    linear = np.zeros((len(flights), len(flights)), dtype=int)
    for a, i in enumerate(flights):
        for b, gate in enumerate(gates):
            linear[a, b] = sum(int(instance.flows[i, k]) * int(instance.distances[gate, assignment[k]])
                               for k in fixed)
    constant = sum(int(instance.flows[k, m]) * int(instance.distances[assignment[k], assignment[m]])
                   for idx, k in enumerate(fixed) for m in fixed[idx + 1:])
    sub = QAPInstance(flows, distances, f"{instance.name}-LNS{len(flights)}", linear)
    return sub, gates, constant


def _choose_flights(rng: np.random.Generator, flows: np.ndarray, k: int) -> list[int]:
    """Half the time K random flights; otherwise a flight plus its strongest partners.

    The choice depends only on ``rng`` and F (never on the current solution), so
    every subsolver sees the same sequence of neighbourhoods for a given seed.
    """
    n = flows.shape[0]
    if rng.random() < 0.5:
        return sorted(int(i) for i in rng.choice(n, size=k, replace=False))
    anchor = int(rng.integers(n))
    weights = flows[anchor].astype(float) + 0.5
    weights[anchor] = 0.0
    partners = rng.choice(n, size=k - 1, replace=False, p=weights / weights.sum())
    return sorted([anchor] + [int(i) for i in partners])


def _exact_sub(sub: QAPInstance) -> tuple[tuple[int, ...], int]:
    best = min(permutations(range(sub.n)), key=sub.cost)
    return best, sub.cost(best)


def lns(instance: QAPInstance, *, subsolver: str = "qaoa", k: int = 3, iterations: int = 60,
        seed: int = 0, reps: int = 2, maxiter: int = 60, shots: int = 512,
        start: list[int] | None = None, stall_limit: int = 12, kick: int = 4) -> dict:
    """Run LNS from a seeded random start; accept equal-or-better moves.

    After ``stall_limit`` iterations without improvement, ``kick`` random flights
    are shuffled (iterated local search) to escape the local optimum. The best
    assignment seen is returned; ``history`` is the best-so-far cost.
    """
    if subsolver not in SUBSOLVERS:
        raise ValueError(f"subsolver debe ser uno de {SUBSOLVERS}")
    n = instance.n
    neighbourhoods = np.random.default_rng(seed)
    sub_rng = np.random.default_rng(seed + 10_000)
    kicks_rng = np.random.default_rng(seed + 30_000)
    current = list(start) if start is not None else [
        int(g) for g in np.random.default_rng(seed + 20_000).permutation(n)]
    current_cost = instance.cost(current)
    start_assignment, start_cost = list(current), current_cost
    best, best_cost = list(current), current_cost

    history = [current_cost]
    current_history = [current_cost]
    stall = kicks = 0
    qaoa_calls = qaoa_hits = 0
    p_optimal: list[float] = []
    tic = perf_counter()
    for _ in range(iterations):
        flights = _choose_flights(neighbourhoods, instance.flows, k)
        sub, gates, constant = subproblem(instance, current, flights)
        if subsolver == "exact":
            choice, _ = _exact_sub(sub)
        elif subsolver == "random":
            choice = tuple(int(g) for g in sub_rng.permutation(k))
        else:
            result = solve_qaoa(sub, mixer="perm", reps=reps, maxiter=maxiter, shots=shots,
                                seed=int(sub_rng.integers(1_000_000)))
            # Perm mixer: every sample is a valid permutation, so no repair is needed.
            choice = tuple(result["raw_best_assignment"])
            qaoa_calls += 1
            qaoa_hits += int(sub.cost(choice) == result["optimum"])
            p_optimal.append(result["p_optimal"])
        candidate = list(current)
        for a, flight in enumerate(flights):
            candidate[flight] = gates[choice[a]]
        candidate_cost = constant + sub.cost(choice)
        if candidate_cost != instance.cost(candidate):
            raise AssertionError("La descomposición del costo no cuadra")
        stall = 0 if candidate_cost < current_cost else stall + 1
        if candidate_cost <= current_cost:
            current, current_cost = candidate, candidate_cost
        if current_cost < best_cost:
            best, best_cost = list(current), current_cost
        if stall_limit and stall >= stall_limit:
            moved = kicks_rng.choice(n, size=kick, replace=False)
            shuffled = [current[i] for i in moved]
            kicks_rng.shuffle(shuffled)
            for flight, gate in zip(moved, shuffled):
                current[int(flight)] = int(gate)
            current_cost = instance.cost(current)
            stall, kicks = 0, kicks + 1
        history.append(best_cost)
        current_history.append(current_cost)
    elapsed = perf_counter() - tic

    out = {
        "subsolver": subsolver,
        "k": k,
        "qubits_per_call": k * k if subsolver == "qaoa" else 0,
        "iterations": iterations,
        "seed": seed,
        "start_assignment": start_assignment,
        "start_cost": start_cost,
        "stall_limit": stall_limit,
        "kick": kick,
        "kicks": kicks,
        "assignment": best,
        "cost": best_cost,
        "feasible": sorted(best) == list(range(n)),
        "history": history,
        "current_history": current_history,
        "seconds": elapsed,
    }
    if subsolver == "qaoa":
        out.update({
            "reps": reps,
            "qaoa_calls": qaoa_calls,
            "qaoa_subproblem_hit_rate": qaoa_hits / max(qaoa_calls, 1),
            "qaoa_mean_p_optimal": float(np.mean(p_optimal)) if p_optimal else None,
        })
    return out
