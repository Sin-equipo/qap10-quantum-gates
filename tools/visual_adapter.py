"""Lightweight adapter from recorded solver data to the visual app contract.

No simulation or file writes happen here. Live and recorded QAOA results share
the same normalizer; only genuine raw feasible samples receive a QAP cost.
"""

from __future__ import annotations

SAMPLE_LIMIT = 256


def _event(step, elapsed, event, assignment=None, best_assignment=None, cost=None,
           best_cost=None, flights=None, accepted=False, kick=False, **extra):
    return {"step": int(step), "elapsed_s": float(elapsed), "event": event,
            "assignment": assignment, "best_assignment": best_assignment,
            "cost": cost, "best_cost": best_cost, "flights": flights or [],
            "accepted": bool(accepted), "kick": bool(kick), **extra}


def normalize_lns_run(run: dict) -> dict:
    """Keep each recorded post-kick state and add the actual start/result."""
    events = [_event(0, 0, "start", run["start_assignment"], run["start_assignment"],
                     run["start_cost"], run["start_cost"])]
    for item in run.get("events", []):
        events.append(_event(
            item["iteration"], item["seconds"], "kick" if item["kick"] else "step",
            item["assignment"], item["best_assignment"], item["cost"], item["best_cost"],
            item["flights"], item["accepted"], bool(item["kick"]),
            outcome=item["outcome"], candidate=item["candidate"],
            candidate_cost=item["candidate_cost"],
            kicked_flights=(item["kick"] or {}).get("flights", []), qaoa=item.get("qaoa"),
        ))
    final = run.get("final_assignment", run.get("assignment"))
    cost = run.get("final_cost", run.get("cost"))
    config = run.get("config", {})
    events.append(_event(config.get("iterations", run.get("iterations", len(events) - 1)),
                         run["seconds"], "complete", final, final, cost, cost))
    method = run.get("subsolver", run.get("method"))
    return {"id": run.get("id", f"lns-n{run['n']}-{method}-s{run['seed']}"),
            "n": run["n"], "kind": "lns", "method": method,
            "seed": run["seed"], "config": config,
            "source": "visual_demo_recorded_run", "start_assignment": run["start_assignment"],
            "final_assignment": final, "cost": cost, "seconds": float(run["seconds"]),
            "timing_scope": "full_lns_loop", "events": events,
            "qubits": config.get("k", 3) ** 2 if method == "qaoa" else 0,
            "feasible": final is not None,
            "qaoa_subproblem_hit_rate": run.get("qaoa_subproblem_hit_rate")}


def normalize_qaoa_run(result: dict, wall_seconds: float | None = None) -> dict:
    """Adapt either solve_qaoa(return_samples=True) or trace.qaoa_run output.

    ``samples`` is the first 256 actual shots, never sorted by feasibility or
    cost. Full-run probabilities/frequencies remain separate from that prefix.
    Optimizer energies are not turned into made-up airport assignments.
    """
    config = dict(result.get("config", {}))
    n, seed = result["n"], result["seed"]
    mixer = result.get("mixer", result.get("method"))
    reps = result.get("reps", config.get("reps", 2))
    shots = result.get("shots", config.get("shots", 2048))
    config.update({"reps": reps, "shots": shots,
                   "alpha": result.get("alpha", config.get("alpha", 1.0)),
                   "maxiter": result.get("maxiter", config.get("maxiter", 100)),
                   "penalty": result.get("penalty", config.get("penalty"))})
    samples = []
    source = result.get("samples", {})
    if isinstance(source, dict):
        prefix = [source["unique"][index] for index in source.get("order", [])[:SAMPLE_LIMIT]]
    else:
        prefix = source[:SAMPLE_LIMIT]
    for sample in prefix:
        valid = bool(sample.get("valid", sample.get("feasible", False)))
        samples.append({"matrix": sample["matrix"], "count": 1, "feasible": valid,
                        "assignment": sample.get("assignment") if valid else None,
                        "cost": sample.get("cost") if valid else None,
                        "conflicts": sample.get("conflicts", {}),
                        "qubo_energy": sample.get("qubo_energy")})
    seconds = float(wall_seconds if wall_seconds is not None else result.get(
        "seconds", result["train_seconds"] + result["sample_seconds"]))
    start, final = result.get("start_assignment"), result.get("raw_best_assignment")
    cost = result.get("raw_best_cost")
    events = [_event(0, 0, "start", start, None, result.get("start_cost")),
              _event(result.get("optimizer_evaluations", 0), seconds, "complete",
                     final, final, cost, cost)]
    return {"id": result.get("id", f"qaoa-n{n}-{mixer}-p{reps}-s{seed}"),
            "n": n, "kind": "qaoa", "method": mixer, "seed": seed, "config": config,
            "source": "live_run" if wall_seconds is not None else "visual_demo_recorded_run",
            "start_assignment": start, "final_assignment": final, "cost": cost,
            "seconds": seconds, "train_seconds": result["train_seconds"],
            "sample_seconds": result["sample_seconds"],
            "timing_scope": "wall_clock" if wall_seconds is not None else "optimizer_and_sampling",
            "events": events, "p_optimal": result["p_optimal"],
            "p_feasible": result["p_feasible"],
            "raw_feasible_fraction": result["raw_feasible_fraction"],
            "p_optimal_random": result.get("p_optimal_random_permutation"),
            "start_is_optimal": result.get("start_cost") == result.get("optimum"),
            "qubits": result["qubits"], "resources": result.get("resources") or {},
            "samples": samples, "sampled_shots": len(samples), "sample_count": len(samples),
            "total_shots": shots, "sample_order": "actual_readout_order_prefix",
            "objective_history": result.get("objective_history", []),
            "objective_kind": "penalized_expected_energy", "feasible": final is not None}


def normalize_catalog(raw: dict) -> dict:
    """Expose one instances/runs shape for the Claude exporter and the app."""
    if "instances" in raw and "runs" in raw:
        return raw
    if not raw:
        return {"schema_version": 1, "instances": [], "runs": [], "studies": {}}
    benchmark = raw.get("instance", {})
    exact = {row["n"]: row for row in raw.get("exact", [])}
    studies = raw.get("studies", {})
    scaling = {row["n"]: row for row in studies.get("scaling", {}).get("rows", [])}
    instances = []
    for n, profile in sorted(exact.items()):
        optimum_assignments = profile.get("optimal_assignments", [])
        instances.append({"n": n,
                          "flows": [row[:n] for row in benchmark["flows"][:n]],
                          "distances": [row[:n] for row in benchmark["distances"][:n]],
                          "coordinates": [[g % 4, g // 4] for g in range(n)],
                          "optimum": profile["optimum"],
                          "exact_assignment": optimum_assignments[0] if optimum_assignments else None,
                          "exact_seconds": profile["seconds"],
                          "stats": scaling.get(n, profile)})
    runs = [normalize_lns_run(run) for run in raw.get("lns_runs", [])]
    runs += [normalize_qaoa_run(run) for run in raw.get("qaoa_runs", [])]
    return {"schema_version": 1, "created_at": raw.get("generated_at"),
            "instances": instances, "runs": runs, "studies": studies,
            "checks": raw.get("checks", []), "export": raw.get("export"),
            "versions": raw.get("versions", {}), "notes": raw.get("notes", {})}
