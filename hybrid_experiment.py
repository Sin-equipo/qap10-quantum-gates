"""N=10 experiment: hybrid LNS-QAOA vs. classical controls on the full QAP10.

Writes results/hybrid_n10.json (every run, with convergence histories) and
results/hybrid_n10_summary.csv, and prints a summary table.
"""

import argparse
import csv
import json
import statistics
from pathlib import Path
from time import perf_counter

from scipy.optimize import quadratic_assignment

from src.qap.classical import solve_exact_blocks
from src.qap.hybrid import SUBSOLVERS, lns
from src.qap.instance import load_qap10

REFERENCE = 340


def gap(cost: int) -> float:
    return 100.0 * (cost - REFERENCE) / REFERENCE


def scipy_faq(instance, seed: int) -> dict:
    """SciPy's FAQ heuristic. SciPy's objective sums both (i,k) and (k,i), so the
    cost is recomputed with the challenge convention (each pair once)."""
    tic = perf_counter()
    result = quadratic_assignment(instance.flows, instance.distances, method="faq",
                                  options={"rng": seed, "P0": "randomized"})
    assignment = [int(g) for g in result.col_ind]
    cost = instance.cost(assignment)
    return {"subsolver": "scipy_faq", "seed": seed, "assignment": assignment, "cost": cost,
            "scipy_objective": float(result.fun), "seconds": perf_counter() - tic,
            "feasible": True}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument("--iterations", type=int, default=150)
    parser.add_argument("--k", type=int, default=3, help="vuelos liberados por iteración (K² qubits)")
    parser.add_argument("--reps", type=int, default=2, help="profundidad p del QAOA")
    parser.add_argument("--maxiter", type=int, default=60)
    parser.add_argument("--shots", type=int, default=512)
    args = parser.parse_args()

    instance = load_qap10()
    exact = solve_exact_blocks(instance)
    print(f"Exacto: costo {exact['cost']} en {exact['seconds']:.1f} s", flush=True)

    runs = []
    for seed in range(args.seeds):
        for subsolver in SUBSOLVERS:
            run = lns(instance, subsolver=subsolver, k=args.k, iterations=args.iterations,
                      seed=seed, reps=args.reps, maxiter=args.maxiter, shots=args.shots)
            run["gap_percent"] = gap(run["cost"])
            runs.append(run)
            print(f"seed {seed} {subsolver:6s}: {run['start_cost']} -> {run['cost']} "
                  f"(gap {run['gap_percent']:.1f}%, {run['seconds']:.1f} s)", flush=True)
        faq = scipy_faq(instance, seed)
        faq["gap_percent"] = gap(faq["cost"])
        runs.append(faq)
        print(f"seed {seed} scipy : {faq['cost']} (gap {faq['gap_percent']:.1f}%)", flush=True)

    summary = []
    for method in (*SUBSOLVERS, "scipy_faq"):
        group = [r for r in runs if r["subsolver"] == method]
        row = {
            "method": method,
            "runs": len(group),
            "best_cost": min(r["cost"] for r in group),
            "median_cost": statistics.median(r["cost"] for r in group),
            "median_gap_percent": statistics.median(r["gap_percent"] for r in group),
            "runs_reaching_340": sum(r["cost"] == REFERENCE for r in group),
            "all_feasible": all(r["feasible"] for r in group),
            "median_seconds": statistics.median(r["seconds"] for r in group),
        }
        if method == "qaoa":
            row["qubits_per_call"] = group[0]["qubits_per_call"]
            row["qaoa_calls_total"] = sum(r["qaoa_calls"] for r in group)
            row["median_subproblem_hit_rate"] = statistics.median(
                r["qaoa_subproblem_hit_rate"] for r in group)
            row["median_p_optimal_per_call"] = statistics.median(
                r["qaoa_mean_p_optimal"] for r in group)
        summary.append(row)

    payload = {"reference_optimum": REFERENCE, "exact": exact, "config": vars(args),
               "summary": summary, "runs": runs}
    Path("results/hybrid_n10.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with open("results/hybrid_n10_summary.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(dict.fromkeys(
            key for row in summary for key in row)))
        writer.writeheader()
        writer.writerows(summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
