"""Exact QAP branch and bound with a Gilmore-Lawler lower bound.

The challenge counts each pair once. At a search node with fixed cost C,
remaining interactions M to fixed flights, sorted remaining flow rows A
(ascending, excluding the diagonal) and distance rows B (descending),

    2*C + min_assignment sum(2*M + A @ B.T)

is a lower bound on TWICE the completion cost. Each row's independent
rearrangement minimum relaxes consistency between the remaining flights.
The outer linear assignment still enforces distinct gates. All calculations
and pruning comparisons use integers. Exhausting this tree certifies the
optimum; the heuristic incumbent is never a preloaded reference solution.

Sources: Lawler (1963), doi:10.1287/mnsc.9.4.586;
https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linear_sum_assignment.html
"""

from __future__ import annotations

from itertools import permutations
from math import factorial
from time import perf_counter

import numpy as np
from scipy.optimize import linear_sum_assignment, quadratic_assignment

from .instance import QAPInstance


def lower_bound_matrix(flows: np.ndarray, distances: np.ndarray, linear: np.ndarray) -> np.ndarray:
    """Integer matrix for a bound on twice the residual objective."""
    m = len(flows)
    off = ~np.eye(m, dtype=bool)
    a = np.sort(flows[off].reshape(m, m - 1), axis=1)
    b = np.sort(distances[off].reshape(m, m - 1), axis=1)[:, ::-1]
    return 2 * linear + a @ b.T


def solve_branch_bound(instance: QAPInstance, *, time_limit: float = 1800,
                       progress=None) -> dict:
    """Certify optimum AND count all optima, with O(N)-depth DFS storage.

    On timeout the returned cost is only an upper bound and ``optimum`` is
    None. Neither the incumbent nor root bound is mislabelled a certificate.
    """
    f, d, n = instance.flows, instance.distances, instance.n
    if (not np.array_equal(f, f.T) or not np.array_equal(d, d.T)
            or np.any(np.diag(f)) or np.any(np.diag(d))
            or np.any(f < 0) or np.any(d < 0)):
        raise ValueError("Se requieren matrices simétricas no negativas con diagonal cero")
    linear = np.zeros((n, n), dtype=np.int64) if instance.linear is None else instance.linear
    tic = perf_counter()
    # Data-only classical warm start, never the known benchmark optimum.
    incumbent = list(range(n))
    best = instance.cost(incumbent)
    if instance.linear is None and n > 2:
        for seed in range(8):
            faq = quadratic_assignment(f, d, method="faq", options={"rng": seed, "P0": "randomized"})
            improved = quadratic_assignment(f, d, method="2opt", options={"rng": seed,
                "partial_guess": np.column_stack((np.arange(n), faq.col_ind))})
            candidate = [int(g) for g in improved.col_ind]
            value = instance.cost(candidate)
            if value < best:
                best, incumbent = value, candidate
    initial_upper_bound = best
    warm_start_seconds = perf_counter() - tic
    # Fix highly connected flights first; the order depends only on F.
    order, remaining = [], list(range(n))
    while remaining:
        chosen = max(remaining, key=lambda i: (sum(int(f[i, j]) for j in order),
                                              int(f[i].sum()), -i))
        order.append(chosen)
        remaining.remove(chosen)
    ff = f[np.ix_(order, order)].astype(np.int64)
    a_sorted = []
    for depth in range(n):
        m = n - depth
        sub = ff[depth:, depth:]
        a_sorted.append(np.sort(sub[~np.eye(m, dtype=bool)].reshape(m, m - 1), axis=1))
    # Each gate subset is encountered repeatedly across flight assignments.
    d_cache: dict[int, np.ndarray] = {}
    assignment = [-1] * n
    nodes = leaves = pruned = 0
    optimal_count = 0
    optimal_examples = []
    timed_out = False
    last_report = tic
    root_bound2 = None

    def visit(depth, gates, mask, interaction, fixed_cost):
        nonlocal best, incumbent, nodes, leaves, pruned, optimal_count
        nonlocal timed_out, last_report, root_bound2, optimal_examples
        if timed_out:
            return
        nodes += 1
        if nodes % 4096 == 0:
            now = perf_counter()
            if time_limit and now - tic > time_limit:
                timed_out = True
                return
            if progress and now - last_report > 15:
                progress({"nodes": nodes, "upper_bound": best, "seconds": now - tic})
                last_report = now
        m = len(gates)
        if m <= 2:
            for indices in permutations(range(m)):
                leaves += 1
                value = fixed_cost + sum(int(interaction[i, indices[i]]) for i in range(m))
                if m == 2:
                    value += int(ff[depth, depth + 1]) * int(d[gates[indices[0]], gates[indices[1]]])
                if value <= best:
                    for i, index in enumerate(indices):
                        assignment[order[depth + i]] = int(gates[index])
                    if value < best:
                        best, optimal_count, optimal_examples = value, 0, []
                    incumbent = list(assignment)
                    optimal_count += 1
                    if len(optimal_examples) < 32:
                        optimal_examples.append(list(assignment))
            return
        if mask not in d_cache:
            dd = d[np.ix_(gates, gates)]
            d_cache[mask] = np.sort(dd[~np.eye(m, dtype=bool)].reshape(m, m - 1), axis=1)[:, ::-1]
        bound_matrix = 2 * interaction + a_sorted[depth] @ d_cache[mask].T
        rr, cc = linear_sum_assignment(bound_matrix)
        bound2 = 2 * fixed_cost + int(bound_matrix[rr, cc].sum())
        if depth == 0:
            root_bound2 = bound2
        if bound2 > 2 * best:
            pruned += 1
            return
        for index in np.argsort(bound_matrix[0], kind="stable"):
            gate = int(gates[index])
            rest = np.delete(gates, index)
            assignment[order[depth]] = gate
            next_cost = fixed_cost + int(interaction[0, index])
            next_interaction = (np.delete(interaction[1:], index, axis=1)
                                + ff[depth, depth + 1:, None] * d[gate, rest][None, :])
            visit(depth + 1, rest, mask ^ (1 << gate), next_interaction, next_cost)

    visit(0, np.arange(n), (1 << n) - 1, linear[order].copy(), 0)
    seconds = perf_counter() - tic
    assert instance.cost(incumbent) == best
    complete = not timed_out
    return {"method": "branch_bound_gilmore_lawler", "n": n,
            "status": "optimal" if complete else "time_limit",
            "certified": complete, "optimum": best if complete else None,
            "cost": best, "assignment": incumbent, "feasible": True,
            "lower_bound": best if complete else (root_bound2 + 1) // 2,
            "optimal_count": optimal_count if complete else None,
            "optimal_assignments": optimal_examples if complete else [],
            "nodes": nodes, "leaf_permutations": leaves, "pruned_nodes": pruned,
            "permutations_in_space": factorial(n), "seconds": seconds,
            "warm_start_seconds": warm_start_seconds, "initial_upper_bound": initial_upper_bound,
            "count_all_optima": complete, "cache_subsets": len(d_cache),
            "time_limit_seconds": time_limit}
