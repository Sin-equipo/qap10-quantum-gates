"""Exact permutation baseline for small QAP instances."""

from itertools import permutations
from time import perf_counter

from .instance import QAPInstance


def solve_exact(instance: QAPInstance) -> dict:
    start = perf_counter()
    best_cost = None
    best_assignment = None
    evaluated = 0
    for assignment in permutations(range(instance.n)):
        cost = instance.cost(assignment)
        evaluated += 1
        if best_cost is None or cost < best_cost:
            best_cost, best_assignment = cost, assignment
    elapsed = perf_counter() - start
    return {
        "method": "enumeración exacta de permutaciones",
        "assignment": list(best_assignment),
        "cost": int(best_cost),
        "feasible": True,
        "candidates": evaluated,
        "seconds": elapsed,
    }
