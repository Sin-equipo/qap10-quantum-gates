"""Recorded runs for the visual demo (results/visual_demo.json).

Every function returns plain JSON-ready dicts. ``lns_run`` and ``qaoa_run`` are
also what the app calls for a live run, so recorded and live runs share one format.
All assignment costs are recomputed with ``QAPInstance.cost`` before returning.
"""

from __future__ import annotations

from itertools import permutations
from math import factorial
from time import perf_counter

import numpy as np

from .hybrid import lns
from .instance import QAPInstance, load_qap10
from .qaoa import solve_qaoa

SCHEMA_VERSION = "1.0"
GRID_COLUMNS = 4

LNS_DEFAULTS = {"k": 3, "iterations": 60, "reps": 2, "maxiter": 60, "shots": 512,
                "stall_limit": 12, "kick": 4}
QAOA_DEFAULTS = {"maxiter": 100, "shots": 2048, "alpha": 1.0}


def gate_layout(instance: QAPInstance) -> dict:
    """Gate g at (row g // 4, column g % 4); checks it reproduces D exactly."""
    coords = [{"gate": g, "row": g // GRID_COLUMNS, "col": g % GRID_COLUMNS}
              for g in range(instance.n)]
    for a in coords:
        for b in coords:
            manhattan = 2 * (abs(a["row"] - b["row"]) + abs(a["col"] - b["col"]))
            if manhattan != instance.distances[a["gate"], b["gate"]]:
                raise ValueError("La cuadrícula 3x4 no reproduce D")
    return {"columns": GRID_COLUMNS, "rows": -(-instance.n // GRID_COLUMNS), "coords": coords,
            "distance_rule": "D[a][b] = 2 * (|fila_a - fila_b| + |col_a - col_b|)"}


def exact_profile(instance: QAPInstance) -> dict:
    """Optimum, every optimal assignment and mean random cost, by full enumeration."""
    n = instance.n
    rows, cols = np.triu_indices(n, 1)
    pair_flows = instance.flows[rows, cols]
    tic = perf_counter()
    best, optimal, total = None, [], 0
    for first in range(n):
        rest = [g for g in range(n) if g != first]
        block = np.array([(first,) + p for p in permutations(rest)], dtype=np.int8).reshape(-1, n)
        costs = (pair_flows * instance.distances[block[:, rows], block[:, cols]]).sum(axis=1)
        total += int(costs.sum())
        low = int(costs.min())
        if best is None or low < best:
            best, optimal = low, []
        if low == best:
            optimal += block[costs == best].tolist()
    seconds = perf_counter() - tic
    for assignment in optimal:
        assert instance.cost(assignment) == best
    return {"n": n, "optimum": best, "optimal_assignments": optimal,
            "optimal_count": len(optimal), "assignments": factorial(n),
            "p_optimal_random": len(optimal) / factorial(n),
            "mean_random_cost": total / factorial(n), "seconds": seconds,
            "trivial": len(optimal) == factorial(n)}


def lns_run(n: int, subsolver: str, seed: int = 0, **overrides) -> dict:
    """One LNS run on the leading N x N block, with its per-iteration events."""
    config = {**LNS_DEFAULTS, **overrides}
    instance = load_qap10().subinstance(n)
    run = lns(instance, subsolver=subsolver, seed=seed, trace=True, **config)
    for event in run["events"]:
        for key in ("candidate", "assignment_after_move", "assignment", "best_assignment"):
            cost_key = {"candidate": "candidate_cost", "assignment_after_move": "cost_after_move",
                        "assignment": "cost", "best_assignment": "best_cost"}[key]
            if instance.cost(event[key]) != event[cost_key]:
                raise AssertionError(f"Costo inconsistente en {key}, iteración {event['iteration']}")
    return {
        "id": f"lns_n{n}_{subsolver}_s{seed}",
        "kind": "lns",
        "n": n,
        "subsolver": subsolver,
        "seed": seed,
        "config": config,
        "start_assignment": run["start_assignment"],
        "start_cost": run["start_cost"],
        "final_assignment": run["assignment"],
        "final_cost": run["cost"],
        "kicks": run["kicks"],
        "seconds": run["seconds"],
        "qaoa_calls": run.get("qaoa_calls"),
        "qaoa_subproblem_hit_rate": run.get("qaoa_subproblem_hit_rate"),
        "events": run["events"],
    }


def qaoa_run(n: int, mixer: str, reps: int, seed: int, resources: bool = False,
             **overrides) -> dict:
    """One direct QAOA run (N <= 4) with every shot decoded in read-out order."""
    config = {**QAOA_DEFAULTS, **overrides}
    instance = load_qap10().subinstance(n)
    result = solve_qaoa(instance, mixer=mixer, reps=reps, seed=seed, resources=resources,
                        return_samples=True, **config)
    for sample in result["samples"]["unique"]:
        if sample["valid"] and instance.cost(sample["assignment"]) != sample["cost"]:
            raise AssertionError("Costo inconsistente en una muestra válida")
    keys = ("qubits", "penalty", "penalty_certified_bound", "ground_state_feasible",
            "hamiltonian_scale", "start_assignment", "start_cost", "optimum", "p_feasible",
            "p_optimal", "p_optimal_random_permutation", "gain_vs_random_permutation",
            "raw_feasible_fraction", "raw_optimal_shots", "raw_best_assignment", "raw_best_cost",
            "objective_final", "optimizer_evaluations", "train_seconds", "sample_seconds")
    return {
        "id": f"qaoa_n{n}_{mixer}_p{reps}_s{seed}",
        "kind": "qaoa_direct",
        "n": n,
        "mixer": mixer,
        "reps": reps,
        "seed": seed,
        "config": {"reps": reps, "mixer": mixer, **config},
        **{key: result[key] for key in keys},
        # Optimiser steps: penalised energy per evaluation, not gate assignments.
        "objective_history": result["objective_history"],
        "resources": result.get("resources"),
        "samples": result["samples"],
    }
