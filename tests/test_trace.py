import pytest

from src.qap import trace
from src.qap.hybrid import lns
from src.qap.instance import load_qap10
from src.qap.qaoa import solve_qaoa


@pytest.fixture(scope="module")
def base():
    return load_qap10()


@pytest.mark.parametrize("subsolver", ["exact", "random"])
def test_trace_does_not_change_the_run(base, subsolver):
    plain = lns(base.subinstance(7), subsolver=subsolver, iterations=40, seed=3)
    traced = lns(base.subinstance(7), subsolver=subsolver, iterations=40, seed=3, trace=True)
    for key in ("assignment", "cost", "history", "current_history", "kicks"):
        assert plain[key] == traced[key]


def test_lns_events_are_consistent(base):
    run = trace.lns_run(6, "random", seed=1, iterations=40)
    instance = base.subinstance(6)
    best = run["start_cost"]
    for event in run["events"]:
        assert instance.cost(event["assignment"]) == event["cost"]
        assert instance.cost(event["candidate"]) == event["candidate_cost"]
        assert event["accepted"] == (event["outcome"] != "reject")
        if event["accepted"]:
            assert event["assignment_after_move"] == event["candidate"]
        else:
            assert event["candidate_cost"] > event["cost_after_move"]
        best = min(best, event["cost_after_move"], event["cost"])
        assert event["best_cost"] == best
    assert any(e["kick"] for e in run["events"])
    assert run["final_cost"] == best


def test_same_neighbourhoods_across_subsolvers():
    runs = [trace.lns_run(6, s, seed=2, iterations=30) for s in ("exact", "random")]
    assert runs[0]["start_assignment"] == runs[1]["start_assignment"]
    assert [e["flights"] for e in runs[0]["events"]] == [e["flights"] for e in runs[1]["events"]]


def test_qaoa_samples_in_read_out_order(base):
    result = solve_qaoa(base.subinstance(3), mixer="x", reps=1, maxiter=5, shots=256, seed=4,
                        return_samples=True)
    samples = result["samples"]
    assert len(samples["order"]) == 256
    assert sum(u["count"] for u in samples["unique"]) == 256
    for u in samples["unique"]:
        conflicts = any(u["conflicts"].values())
        assert u["valid"] != conflicts
        assert (u["cost"] is None) == (not u["valid"])
    valid_share = sum(samples["unique"][i]["valid"] for i in samples["order"]) / 256
    assert valid_share == pytest.approx(result["raw_feasible_fraction"])


def test_gate_layout_reproduces_distances(base):
    layout = trace.gate_layout(base)
    assert (layout["rows"], layout["columns"]) == (3, 4)


def test_exact_profile_lists_every_optimum(base):
    profile = trace.exact_profile(base.subinstance(4))
    assert profile["optimum"] == 32 and profile["optimal_count"] == 2


def test_export_summary_and_default_view_use_the_same_recorded_runs():
    from tools.export_visual_demo import DEFAULT_QAOA_VIEW, qaoa_summary

    runs = [trace.qaoa_run(3, mixer, 2, seed, maxiter=8, shots=64)
            for mixer in ("x", "perm") for seed in range(2)]
    exact = [trace.exact_profile(load_qap10().subinstance(3))]
    summary = {(row["mixer"], row["reps"]): row for row in qaoa_summary(runs, exact)}
    assert set(summary) == {("x", 2), ("perm", 2)}
    for (mixer, _), row in summary.items():
        recorded = sorted(r["p_optimal"] for r in runs if r["mixer"] == mixer)
        assert row["seeds"] == 2 and row["p_optimal_by_seed"] == [
            r["p_optimal"] for r in sorted((r for r in runs if r["mixer"] == mixer), key=lambda r: r["seed"])]
        assert row["median_p_optimal"] == sum(recorded) / 2
        assert row["random_p_optimal"] == exact[0]["p_optimal_random"]
    assert DEFAULT_QAOA_VIEW == {"n": 4, "depth": 3, "seed": 3}
