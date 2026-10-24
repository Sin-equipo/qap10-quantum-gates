"""QAOA parameter sweep on the N=3 and N=4 QAP10 subinstances.

Writes one CSV row per run to results/qaoa_sweep.csv (appending as it goes, so a
partial sweep is still usable) and prints a summary table at the end.
"""

import argparse
import csv
import json
from pathlib import Path

from src.qap.instance import load_qap10
from src.qap.qaoa import solve_qaoa

FIELDS = [
    "experiment", "n", "qubits", "mixer", "reps", "alpha", "penalty", "penalty_certified_bound",
    "ground_state_feasible", "seed", "start_cost", "start_is_optimal", "optimum",
    "p_feasible", "p_optimal", "p_optimal_random_permutation", "gain_vs_random_permutation",
    "raw_feasible_fraction", "raw_optimal_shots", "raw_best_cost", "repaired_best_cost",
    "optimizer_evaluations", "train_seconds", "sample_seconds",
]


def grid(quick: bool):
    seeds = range(3) if quick else range(5)
    # Mixer / depth / CVaR comparison at the certified penalty.
    for n in (3, 4):
        for mixer, depths in (("x", (1, 2)), ("perm", (1, 2, 3))):
            for reps in depths:
                for alpha in (1.0, 0.25):
                    for seed in seeds:
                        yield "mixer_depth_cvar", n, dict(mixer=mixer, reps=reps, alpha=alpha,
                                                          seed=seed)
    # Penalty sweep: only the X mixer depends on lambda (perm stays feasible).
    for n in (3, 4):
        for factor in (0.5, 1.0, 2.0, 4.0):
            for seed in seeds:
                yield "penalty", n, dict(mixer="x", reps=1, alpha=0.25, seed=seed,
                                         penalty_factor=factor)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true", help="3 semillas en lugar de 5")
    parser.add_argument("--maxiter", type=int, default=100)
    parser.add_argument("--shots", type=int, default=2048)
    parser.add_argument("--output", default="results/qaoa_sweep.csv")
    args = parser.parse_args()

    base = load_qap10()
    output = Path(args.output)
    output.parent.mkdir(exist_ok=True)
    rows = []
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        for experiment, n, kwargs in grid(args.quick):
            result = solve_qaoa(base.subinstance(n), maxiter=args.maxiter, shots=args.shots,
                                **kwargs)
            result["experiment"] = experiment
            result["start_is_optimal"] = result["start_cost"] == result["optimum"]
            writer.writerow(result)
            handle.flush()
            rows.append(result)
            print(f"{experiment:17s} N={n} {kwargs} -> p_feas={result['p_feasible']:.3f} "
                  f"p_opt={result['p_optimal']:.3f} "
                  f"gain={result['gain_vs_random_permutation']:.2f}", flush=True)

    summary = summarize(rows)
    Path("results/qaoa_sweep_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


def summarize(rows: list[dict]) -> list[dict]:
    """Median and best over seeds, excluding runs whose start was already optimal."""
    import statistics

    groups: dict[tuple, list[dict]] = {}
    for row in rows:
        key = (row["experiment"], row["n"], row["mixer"], row["reps"], row["alpha"],
               round(row["penalty"], 3))
        groups.setdefault(key, []).append(row)
    summary = []
    for (experiment, n, mixer, reps, alpha, penalty), group in groups.items():
        fair = [r for r in group if not r["start_is_optimal"]] or group
        summary.append({
            "experiment": experiment, "n": n, "mixer": mixer, "reps": reps, "alpha": alpha,
            "penalty": penalty, "runs": len(group), "runs_used": len(fair),
            "median_p_feasible": statistics.median(r["p_feasible"] for r in fair),
            "median_p_optimal": statistics.median(r["p_optimal"] for r in fair),
            "best_p_optimal": max(r["p_optimal"] for r in fair),
            "p_optimal_random_permutation": fair[0]["p_optimal_random_permutation"],
            "median_gain_vs_random": statistics.median(
                r["gain_vs_random_permutation"] for r in fair),
            "runs_with_raw_optimum": sum(r["raw_optimal_shots"] > 0 for r in fair),
            "median_train_seconds": statistics.median(r["train_seconds"] for r in fair),
        })
    return summary


if __name__ == "__main__":
    main()
