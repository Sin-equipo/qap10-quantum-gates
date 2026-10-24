"""Behavior checks for the boundary between real solver data and the visual app."""

from itertools import permutations

from src.qap.instance import load_qap10
from src.qap.trace import lns_run
from tools.visual_adapter import normalize_catalog, normalize_lns_run, normalize_qaoa_run


def direct_result():
    # The readout order deliberately differs from the sorted unique-state order.
    return {"n": 2, "seed": 0, "mixer": "x", "reps": 2, "shots": 3, "alpha": 1,
            "penalty": 11, "train_seconds": 0.5, "sample_seconds": 0.1,
            "start_assignment": None, "start_cost": None, "optimum": 10,
            "raw_best_assignment": [1, 0], "raw_best_cost": 10,
            "p_optimal": 0.6, "p_feasible": 0.6, "raw_feasible_fraction": 2 / 3,
            "qubits": 4, "optimizer_evaluations": 7, "objective_history": [30, 20],
            "samples": {"unique": [
                {"matrix": [[0, 0], [1, 0]], "count": 1, "valid": False,
                 "assignment": None, "cost": None, "qubo_energy": 21},
                {"matrix": [[0, 1], [1, 0]], "count": 2, "valid": True,
                 "assignment": [1, 0], "cost": 10, "qubo_energy": 10}], "order": [1, 0, 1]}}


def test_actual_shot_order_is_preserved_and_invalid_cost_absent():
    result = normalize_qaoa_run(direct_result())
    assert [sample["feasible"] for sample in result["samples"]] == [True, False, True]
    assert result["samples"][1]["cost"] is None
    assert result["samples"][1]["assignment"] is None
    assert result["samples"][1]["qubo_energy"] == 21
    assert result["sampled_shots"] == result["total_shots"] == 3
    assert result["p_feasible"] == 0.6  # population probability is not prefix frequency


def test_sample_prefix_is_bounded_without_altering_full_metrics():
    raw = direct_result()
    raw["shots"] = 1000
    raw["samples"]["order"] = [1, 0] * 500
    result = normalize_qaoa_run(raw)
    assert len(result["samples"]) == 256
    assert result["total_shots"] == 1000
    assert result["raw_feasible_fraction"] == 2 / 3


def test_repaired_fallback_is_never_presented_as_raw_feasible_assignment():
    raw = direct_result()
    raw.update(raw_best_assignment=None, raw_best_cost=None, assignment=[0, 1], cost=10)
    result = normalize_qaoa_run(raw, wall_seconds=0.9)
    assert result["final_assignment"] is None
    assert result["cost"] is None
    assert not result["feasible"]
    assert result["seconds"] == 0.9
    assert result["timing_scope"] == "wall_clock"
    assert result["events"][-1]["assignment"] is None


def test_lns_real_trace_costs_kicks_and_same_neighborhoods():
    base = load_qap10().subinstance(4)
    runs = [lns_run(4, method, seed=0, iterations=14, stall_limit=2)
            for method in ("exact", "random")]
    assert runs[0]["start_assignment"] == runs[1]["start_assignment"]
    assert [event["flights"] for event in runs[0]["events"]] == [
        event["flights"] for event in runs[1]["events"]]
    for raw in runs:
        run = normalize_lns_run(raw)
        assert len(run["events"]) == 16
        assert any(event["kick"] for event in run["events"])
        previous_best = float("inf")
        previous_time = -1
        for event in run["events"]:
            assert base.cost(event["assignment"]) == event["cost"]
            assert base.cost(event["best_assignment"]) == event["best_cost"]
            assert event["best_cost"] <= previous_best
            assert event["elapsed_s"] >= previous_time
            previous_best, previous_time = event["best_cost"], event["elapsed_s"]
        assert run["events"][-1]["assignment"] == run["final_assignment"]


def test_catalog_keeps_all_n_exact_references_and_distinguishes_studies():
    base = load_qap10()
    exact = []
    for n in (1, 2, 3, 4):
        sub = base.subinstance(n)
        optimum = min(sub.cost(p) for p in permutations(range(n)))
        optimal = [list(p) for p in permutations(range(n)) if sub.cost(p) == optimum]
        exact.append({"n": n, "optimum": optimum, "optimal_assignments": optimal,
                      "seconds": 0.001})
    raw = {"schema_version": "1.0", "instance": {"flows": base.flows.tolist(),
           "distances": base.distances.tolist()}, "exact": exact, "lns_runs": [],
           "qaoa_runs": [], "studies": {"scaling": {"config": {"seeds": 3, "iterations": 60}},
           "hybrid_n10": {"config": {"seeds": 5, "iterations": 150}}}}
    catalog = normalize_catalog(raw)
    assert [row["optimum"] for row in catalog["instances"]] == [0, 10, 24, 32]
    assert catalog["studies"]["scaling"]["config"]["seeds"] == 3
    assert catalog["studies"]["hybrid_n10"]["config"]["seeds"] == 5
    assert len(catalog["instances"][-1]["distances"]) == 4
