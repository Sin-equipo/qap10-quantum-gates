"""Exact permutation baseline for small QAP instances."""

from itertools import permutations
from time import perf_counter

import numpy as np

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


def solve_exact_blocks(instance: QAPInstance) -> dict:
    """Exact enumeration for N=10 in constant memory: one numpy block per first gate.

    Each block holds the (N-1)! permutations that start with a given gate, so at
    most 9! = 362,880 assignments are in memory at once; nothing else is stored.
    """
    if instance.linear is not None:
        raise ValueError("solve_exact_blocks no admite término lineal")
    n = instance.n
    rows, cols = np.triu_indices(n, 1)
    pair_flows = instance.flows[rows, cols]
    start = perf_counter()
    best_cost, best_assignment = None, None
    for first in range(n):
        rest = [gate for gate in range(n) if gate != first]
        block = np.array([(first,) + perm for perm in permutations(rest)], dtype=np.int8)
        costs = (pair_flows * instance.distances[block[:, rows], block[:, cols]]).sum(axis=1)
        index = int(costs.argmin())
        if best_cost is None or costs[index] < best_cost:
            best_cost, best_assignment = int(costs[index]), block[index].tolist()
    elapsed = perf_counter() - start
    return {
        "method": "enumeración exacta por bloques (numpy)",
        "assignment": best_assignment,
        "cost": best_cost,
        "feasible": True,
        "candidates": int(np.prod(range(1, n + 1))),
        "seconds": elapsed,
    }
