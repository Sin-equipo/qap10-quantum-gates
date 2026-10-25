"""Measured nested QAP10 extension, N=10..14, with isolated serial workers.

python scaling14_study.py                    # five paired seeds, 60 steps
python scaling14_study.py --assemble-only    # rebuild summary from saved jobs

Every job saves its inputs, source hash, timing and process RSS measurements.
Resume reuses only jobs with the same specification AND solver source hash.
The exact reference is never passed to LNS or FAQ as a starting solution.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import statistics
import subprocess
import sys
import threading
from datetime import datetime, timezone
from importlib.metadata import version
from math import factorial
from pathlib import Path
from time import perf_counter

import numpy as np

ROOT = Path(__file__).resolve().parent
JOB_DIR = ROOT / "results" / "scaling14_jobs"
SOURCE_FILES = ("src/qap/instance.py", "src/qap/exact_bound.py", "src/qap/hybrid.py",
                "src/qap/qaoa.py", "src/qap/trace.py", "scaling14_study.py")
THREAD_ENV = {"OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
              "RAYON_NUM_THREADS": "1", "QISKIT_PARALLEL": "FALSE"}


def dump(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def source_hash():
    return hashlib.sha256(b"".join((ROOT / p).read_bytes().replace(b"\r\n", b"\n")
                                   for p in SOURCE_FILES)).hexdigest()


def worker(spec, output):
    # Import the same numerical/quantum stack BEFORE every measured method.
    import numpy as np
    import psutil
    from scipy.optimize import quadratic_assignment
    from src.qap.classical import solve_exact_blocks
    from src.qap.exact_bound import solve_branch_bound
    from src.qap.instance import EXTENSION_SEED, load_instance
    from src.qap.trace import lns_run

    instance = load_instance(spec["n"])
    process = psutil.Process()
    initial_rss = process.memory_info().rss
    rss_samples = [initial_rss]
    stopped = threading.Event()

    def sample():
        while not stopped.wait(0.005):
            rss_samples.append(process.memory_info().rss)

    monitor = threading.Thread(target=sample, daemon=True)
    monitor.start()
    tic, cpu_start = perf_counter(), process.cpu_times()
    try:
        method = spec["method"]
        if method == "reference":
            result = solve_branch_bound(instance, time_limit=spec["time_limit"],
                progress=lambda p: print(json.dumps({"n": instance.n, **p}), flush=True))
        elif method == "enumeration":
            result = solve_exact_blocks(instance)
        elif method == "scipy_faq":
            solved = quadratic_assignment(instance.flows, instance.distances, method="faq",
                options={"rng": spec["seed"], "P0": "randomized"})
            assignment = [int(x) for x in solved.col_ind]
            result = {"assignment": assignment, "cost": instance.cost(assignment),
                      "feasible": True, "scipy_objective": float(solved.fun)}
        else:
            result = lns_run(instance.n, method, seed=spec["seed"], **spec["lns_config"])
        measured_seconds = perf_counter() - tic
    finally:
        stopped.set()
        monitor.join()
    rss_samples.append(process.memory_info().rss)
    cpu_end = process.cpu_times()
    assignment = result.get("assignment", result.get("final_assignment"))
    cost = result.get("cost", result.get("final_cost"))
    assert instance.cost(assignment) == cost
    result.update({"measured_seconds": measured_seconds,
        "cpu_seconds": cpu_end.user + cpu_end.system - cpu_start.user - cpu_start.system,
        "rss_before_bytes": initial_rss, "peak_rss_bytes": max(rss_samples),
        "peak_rss_increase_bytes": max(rss_samples) - initial_rss,
        "rss_sample_interval_seconds": 0.005, "rss_samples": len(rss_samples),
        "peak_process_rss_bytes": getattr(process.memory_info(), "peak_wset", max(rss_samples))})
    matrix_bytes = instance.flows.astype("<i8").tobytes() + instance.distances.astype("<i8").tobytes()
    payload = {"spec": spec, "solver_source_sha256": source_hash(),
        "instance_sha256": hashlib.sha256(matrix_bytes).hexdigest(),
        "extension_seed": EXTENSION_SEED, "result": result,
        "completed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "environment": {"python": platform.python_version(), "os": platform.platform(),
            "thread_environment": {key: os.environ.get(key) for key in THREAD_ENV},
            "processor": platform.processor(), "logical_cpus": os.cpu_count(),
            "ram_bytes": psutil.virtual_memory().total,
            "versions": {p: version(p) for p in ("qiskit", "qiskit-aer", "numpy", "scipy", "psutil")}}}
    dump(output, payload)
    print(json.dumps({"n": instance.n, "method": method, "seed": spec["seed"],
        "cost": cost, "seconds": round(measured_seconds, 4),
        "peak_rss_mib": round(max(rss_samples) / 2**20, 1),
        "certified": result.get("certified")}), flush=True)


def job_specs(args):
    config = {"k": 3, "iterations": args.iterations, "reps": 2, "maxiter": 60,
              "shots": 512, "stall_limit": 12, "kick": 4,
              "training_simulator": "permutation_subspace"}
    # References finish first; timed jobs run sequentially, never competing.
    for n in range(10, 15):
        yield {"n": n, "method": "reference", "seed": None,
               "time_limit": args.time_limit, "lns_config": config}
    yield {"n": 10, "method": "enumeration", "seed": None,
           "time_limit": args.time_limit, "lns_config": config}
    for n in range(10, 15):
        for seed in range(args.seeds):
            for method in ("exact", "random", "scipy_faq", "qaoa"):
                yield {"n": n, "method": method, "seed": seed,
                       "time_limit": args.time_limit, "lns_config": config}


def job_path(spec):
    return JOB_DIR / f"n{spec['n']}_{spec['method']}_s{spec['seed']}.json"


def assemble(specs):
    from src.qap.instance import EXTENSION_SEED, extended_qap14
    jobs = []
    for spec in specs:
        if job_path(spec).exists():
            job = json.loads(job_path(spec).read_text(encoding="utf-8"))
            if job["solver_source_sha256"] == source_hash() and job["spec"] == spec:
                jobs.append(job)
    references = {j["spec"]["n"]: j["result"] for j in jobs if j["spec"]["method"] == "reference"}
    rows, summaries, recorded = [], [], []
    for n, ref in sorted(references.items()):
        if not ref["certified"]:
            raise RuntimeError(f"N={n}: la referencia no tiene certificado de optimalidad")
        instance = extended_qap14().subinstance(n)
        pair_count = n * (n - 1) // 2
        row = {"n": n, "instance_kind": "qap10_original" if n == 10 else "synthetic_extension",
            "optimum": ref["optimum"], "exact_assignment": ref["assignment"],
            "optimal_assignments": ref["optimal_count"], "assignments": factorial(n),
            "p_optimal_random": ref["optimal_count"] / factorial(n),
            "mean_random_cost": float(instance.flows[np.triu_indices(n, 1)].sum()
                                     * instance.distances[np.triu_indices(n, 1)].sum() / pair_count),
            "exact_seconds": ref["measured_seconds"], "reference_method": ref["method"],
            "reference_certified": True, "reference_lower_bound": ref["lower_bound"],
            "exact_peak_rss_bytes": ref["peak_rss_bytes"],
            "qubo_qubits": n*n, "statevector_bytes": 16 * 2 ** (n*n)}
        for method in ("exact", "random", "scipy_faq", "qaoa"):
            group = [j["result"] for j in jobs if j["spec"]["n"] == n and j["spec"]["method"] == method]
            if not group:
                continue
            costs = [r.get("final_cost", r.get("cost")) for r in group]
            for run in group:
                if method != "scipy_faq":
                    recorded.append(run)
            summary = {"n": n, "method": method, "runs": len(group),
                "best_cost": min(costs), "median_cost": statistics.median(costs),
                "median_gap_percent": 100 * (statistics.median(costs) - ref["optimum"]) / ref["optimum"],
                "optimal_hits": sum(c == ref["optimum"] for c in costs),
                "all_feasible": all(instance.cost(r.get("final_assignment", r.get("assignment")))
                                      == c for r, c in zip(group, costs)),
                "median_seconds": statistics.median(r["measured_seconds"] for r in group),
                "median_peak_rss_bytes": statistics.median(r["peak_rss_bytes"] for r in group),
                "max_peak_rss_bytes": max(r["peak_rss_bytes"] for r in group),
                "median_rss_increase_bytes": statistics.median(r["peak_rss_increase_bytes"] for r in group),
                "qubits_per_call": 9 if method == "qaoa" else 0}
            if method == "qaoa":
                summary["median_subproblem_hit_rate"] = statistics.median(r["qaoa_subproblem_hit_rate"] for r in group)
            summaries.append(summary)
            prefix = "lns_" + method if method != "scipy_faq" else "scipy_faq"
            for key, value in (("best", summary["best_cost"]), ("median", summary["median_cost"]),
                ("gap_median", summary["median_gap_percent"]), ("hits", summary["optimal_hits"]),
                ("seconds", summary["median_seconds"]), ("peak_rss_bytes", summary["median_peak_rss_bytes"])):
                row[f"{prefix}_{key}"] = value
        rows.append(row)
    payload = {"schema_version": 1, "complete": len(jobs) == len(specs),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "config": {"seeds": len({s["seed"] for s in specs if s["seed"] is not None}),
                   **specs[0]["lns_config"], "sizes": list(range(10, 15))},
        "instance": {"name": "qap10-extension14", "extension_seed": EXTENSION_SEED,
            "flows": extended_qap14().flows.tolist(), "distances": extended_qap14().distances.tolist(),
            "construction": "QAP10 intacto; nuevos flujos muestreados de sus 45 pares (incluye ceros); cuadrícula de 4 columnas, Manhattan ×2",
            "source": "data/qap10_matrices.json; extensión sintética del equipo, no un benchmark MIPLIB oficial ni datos aeroportuarios medidos"},
        "measurement": {"execution": "isolated processes, serial jobs; same imports before each timed solver",
            "time_scope": "solver call including warm start/trace validation, excluding imports and JSON writing",
            "memory_scope": "sampled process RSS during solver call, 5 ms interval; includes Python and all imported libraries",
            "memory_limit": "Sampling can miss transient peaks; baseline and increase provided, not memory of a real QPU",
            "thread_environment": THREAD_ENV,
            "comparison": f"Same seeded start and flight-neighbourhood sequence for paired LNS methods; same {specs[0]['lns_config']['iterations']}-step budget, not same wall-time budget"},
        "solver_source_sha256": source_hash(), "environment": jobs[0]["environment"] if jobs else {},
        "references": references, "rows": rows, "summary": summaries,
        "lns_runs": recorded, "jobs_completed": len(jobs), "jobs_expected": len(specs)}
    dump(ROOT / "results" / "scaling14.json", payload)
    if summaries:
        fields = list(dict.fromkeys(k for r in summaries for k in r))
        with (ROOT / "results" / "scaling14_summary.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(summaries)
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument("--iterations", type=int, default=60)
    parser.add_argument("--time-limit", type=float, default=1800)
    parser.add_argument("--assemble-only", action="store_true")
    parser.add_argument("--worker")
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.worker:
        worker(json.loads(args.worker), Path(args.output))
        return
    specs = list(job_specs(args))
    for spec in specs:
        path = job_path(spec)
        reusable = False
        if path.exists():
            old = json.loads(path.read_text(encoding="utf-8"))
            reusable = old["spec"] == spec and old["solver_source_sha256"] == source_hash()
        if not reusable:
            if args.assemble_only:
                raise RuntimeError(f"Falta una medición compatible: {path}")
            subprocess.run([sys.executable, "-u", str(Path(__file__).resolve()),
                "--worker", json.dumps(spec), "--output", str(path)], cwd=ROOT,
                env={**os.environ, **THREAD_ENV}, check=True)
        # Checkpoint after each job; UI reads only completed full results.
        assemble(specs)
    result = assemble(specs)
    print(f"Complete: {result['jobs_completed']}/{result['jobs_expected']} jobs", flush=True)


if __name__ == "__main__":
    main()
