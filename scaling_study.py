"""Scaling study N=1..10 on the leading N x N blocks of QAP10.

For every N: exact optimum (and how many assignments reach it), enumeration
time, mean cost of a random assignment, QUBO size and statevector memory.
Direct QAOA where the full QUBO fits (N <= 4) and hybrid LNS where it does not
(N >= 4). Writes results/scaling.csv and results/scaling.json.
"""

import argparse
import csv
import json
import statistics
from itertools import permutations
from math import factorial
from pathlib import Path
from time import perf_counter

import numpy as np

from src.qap.hybrid import lns
from src.qap.instance import QAPInstance, load_qap10
from src.qap.qaoa import solve_qaoa

CONTROL_OPTIMA = {3: 24, 4: 32, 10: 340}


def exact_profile(instance: QAPInstance) -> dict:
    """Every assignment's cost, one numpy block per first gate (constant memory)."""
    n = instance.n
    rows, cols = np.triu_indices(n, 1)
    pair_flows = instance.flows[rows, cols]
    tic = perf_counter()
    best, count, total, best_assignment = None, 0, 0, None
    for first in range(n):
        rest = [g for g in range(n) if g != first]
        block = np.array([(first,) + p for p in permutations(rest)], dtype=np.int8).reshape(-1, n)
        costs = (pair_flows * instance.distances[block[:, rows], block[:, cols]]).sum(axis=1)
        low = int(costs.min())
        total += int(costs.sum())
        if best is None or low < best:
            best, count, best_assignment = low, 0, block[int(costs.argmin())].tolist()
        if low == best:
            count += int((costs == best).sum())
    return {"optimum": best, "optimal_assignments": count, "assignments": factorial(n),
            "mean_random_cost": total / factorial(n), "exact_seconds": perf_counter() - tic,
            "exact_assignment": best_assignment}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument("--iterations", type=int, default=60, help="iteraciones LNS por corrida")
    args = parser.parse_args()

    base = load_qap10()
    rows = []
    for n in range(1, base.n + 1):
        instance = base.subinstance(n)
        row = {"n": n, **exact_profile(instance)}
        row["control_optimum"] = CONTROL_OPTIMA.get(n)
        row["qubo_qubits"] = n * n
        row["statevector_bytes"] = 16 * 2 ** (n * n)
        row["p_optimal_random"] = row["optimal_assignments"] / row["assignments"]

        if 2 <= n <= 4:
            for mixer in ("x", "perm"):
                runs = [solve_qaoa(instance, mixer=mixer, reps=2, seed=s, resources=(s == 0))
                        for s in range(args.seeds)]
                row[f"qaoa_{mixer}_p_feasible"] = statistics.median(r["p_feasible"] for r in runs)
                row[f"qaoa_{mixer}_p_optimal"] = statistics.median(r["p_optimal"] for r in runs)
                row[f"qaoa_{mixer}_two_qubit_gates"] = runs[0]["resources"]["transpiled_two_qubit_gates"]
                row[f"qaoa_{mixer}_train_seconds"] = statistics.median(r["train_seconds"] for r in runs)

        if n >= 4:
            for subsolver in ("qaoa", "exact"):
                runs = [lns(instance, subsolver=subsolver, k=3, iterations=args.iterations, seed=s)
                        for s in range(args.seeds)]
                costs = [r["cost"] for r in runs]
                row[f"lns_{subsolver}_best"] = min(costs)
                row[f"lns_{subsolver}_median"] = statistics.median(costs)
                row[f"lns_{subsolver}_gap_median"] = 100 * (statistics.median(costs) - row["optimum"]) / row["optimum"]
                row[f"lns_{subsolver}_hits"] = sum(c == row["optimum"] for c in costs)
                row[f"lns_{subsolver}_seconds"] = statistics.median(r["seconds"] for r in runs)

        rows.append(row)
        print(json.dumps({k: (round(v, 4) if isinstance(v, float) else v)
                          for k, v in row.items() if k != "exact_assignment"}, ensure_ascii=False),
              flush=True)

    Path("results/scaling.json").write_text(json.dumps(
        {"config": vars(args), "rows": rows}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    fields = list(dict.fromkeys(key for row in rows for key in row if key != "exact_assignment"))
    with open("results/scaling.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
