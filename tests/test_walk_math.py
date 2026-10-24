"""Run the actual browser arithmetic in Node against an independent QAP oracle."""

from __future__ import annotations

import json
import shutil
import subprocess

import pytest

from app.walk_math import WALK_MODEL
from src.qap.instance import load_qap10

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="Node.js is required to execute the actual browser walking model")


def evaluate_js(expression: str, payload: dict):
    script = WALK_MODEL + "\nconst input = JSON.parse(require('fs').readFileSync(0, 'utf8'));\n"
    script += "console.log(JSON.stringify(" + expression + "));\n"
    process = subprocess.run(
        [NODE, "-e", script], input=json.dumps(payload), text=True,
        capture_output=True, check=True, timeout=10,
    )
    return json.loads(process.stdout)


def instance_payload(n: int, assignment=None):
    inst = load_qap10().subinstance(n)
    return inst, {"flows": inst.flows.tolist(), "distances": inst.distances.tolist(),
                  "assignment": list(range(n)) if assignment is None else assignment}


@pytest.mark.parametrize("n", range(1, 11))
def test_complete_walk_accounts_for_the_exact_qap_cost(n):
    assignment = list(reversed(range(n)))
    instance, payload = instance_payload(n, assignment)
    result = evaluate_js("(() => {const p=Walk.people(input.flows,input.distances,input.assignment);"
                         "const end=Walk.duration(p);return {p, end, stats:Walk.stats(p,end)};})()", payload)
    assert result["stats"]["travelled"] == instance.cost(assignment)
    assert result["stats"]["totalDistance"] == instance.cost(assignment)
    assert result["stats"]["arrived"] == result["stats"]["total"]
    assert result["stats"]["total"] == int(sum(instance.flows[i, k] for i in range(n) for k in range(i + 1, n)))
    assert result["end"] == result["stats"]["lastArrival"]
    assert all(0 <= person["delay"] <= 0.5 for person in result["p"])


def test_same_assignments_have_identical_routes_and_motion():
    _, payload = instance_payload(10)
    result = evaluate_js("(() => {const a=Walk.people(input.flows,input.distances,input.assignment);"
                         "const b=Walk.people(input.flows,input.distances,input.assignment);"
                         "return {a,b, aFrame:Walk.stats(a,1.234), bFrame:Walk.stats(b,1.234)};})()", payload)
    assert result["a"] == result["b"]
    assert result["aFrame"] == result["bFrame"]


def test_corresponding_people_share_schedule_even_after_gate_changes():
    _, payload = instance_payload(10)
    payload["other"] = [2, 6, 3, 0, 8, 4, 5, 1, 7, 9]
    result = evaluate_js("(() => {const a=Walk.people(input.flows,input.distances,input.assignment);"
                         "const b=Walk.people(input.flows,input.distances,input.other);"
                         "return {a,b};})()", payload)
    assert [p["delay"] for p in result["a"]] == [p["delay"] for p in result["b"]]
    assert [p["jitter"] for p in result["a"]] == [p["jitter"] for p in result["b"]]
    assert [(p["id"], p["i"], p["k"]) for p in result["a"]] == [
        (p["id"], p["i"], p["k"]) for p in result["b"]]


def test_transfer_subsets_partition_the_full_objective_and_keep_person_ids():
    instance, payload = instance_payload(10)
    payload["other"] = [2, 6, 3, 0, 8, 4, 5, 1, 7, 9]
    result = evaluate_js("(() => {const ts=Walk.transfers(input.flows,input.distances,input.assignment,input.other);"
                         "return {ts, all:Walk.people(input.flows,input.distances,input.assignment),"
                         "parts:ts.map(t=>Walk.people(input.flows,input.distances,input.assignment,t.id))};})()", payload)
    assert sum(t["leftCost"] for t in result["ts"]) == instance.cost(payload["assignment"])
    assert sum(t["rightCost"] for t in result["ts"]) == instance.cost(payload["other"])
    assert sum(t["delta"] for t in result["ts"]) == instance.cost(payload["assignment"]) - instance.cost(payload["other"])
    assert [p for part in result["parts"] for p in part] == result["all"]
    assert all(len(part) == transfer["flow"] for part, transfer in zip(result["parts"], result["ts"]))


def test_equal_last_arrival_can_hide_different_total_distance():
    result = evaluate_js("(() => {const a=[{d:2,delay:0},{d:2,delay:0},{d:8,delay:0}];"
                         "const b=[{d:2,delay:0},{d:6,delay:0},{d:8,delay:0}];"
                         "return {a:Walk.stats(a,Walk.duration(a)),b:Walk.stats(b,Walk.duration(b))};})()", {})
    assert result["a"]["lastArrival"] == result["b"]["lastArrival"]
    assert result["a"]["totalDistance"] == 12
    assert result["b"]["totalDistance"] == 16
    assert result["a"]["arrived"] == result["b"]["arrived"] == 3


def test_empty_and_zero_length_walks_finish_without_an_eight_second_wait():
    result = evaluate_js("({empty:Walk.stats([],0), duration:Walk.duration([]),"
                         "before:Walk.progress({d:0,delay:.2},.1),"
                         "at:Walk.progress({d:0,delay:.2},.2)})", {})
    assert result["empty"] == {"total": 0, "arrived": 0, "travelled": 0,
                               "totalDistance": 0, "lastArrival": 0}
    assert result["duration"] == 0
    assert result["before"] == 0
    assert result["at"] == 1


def test_completion_is_the_actual_last_arrival_and_progress_never_overshoots():
    _, payload = instance_payload(10)
    result = evaluate_js("(() => {const ps=Walk.people(input.flows,input.distances,input.assignment);"
                         "const end=Walk.duration(ps);return {end,before:Walk.stats(ps,end-1e-4),"
                         "at:Walk.stats(ps,end),after:Walk.stats(ps,end+100),negative:Walk.stats(ps,-1)};})()", payload)
    assert result["end"] < 8
    assert result["before"]["arrived"] < result["at"]["total"]
    assert result["at"]["arrived"] == result["at"]["total"]
    assert result["at"] == result["after"]
    assert result["negative"]["travelled"] == 0
    assert result["negative"]["arrived"] == 0


@pytest.mark.parametrize("assignment", [None, [0, 0, 2, 3], [0, 1, 2], [0, 1, 2, 4], [0, 1, 2, True]])
def test_invalid_plans_do_not_create_fake_routes_or_costs(assignment):
    _, payload = instance_payload(4, assignment)
    payload["assignment"] = assignment
    result = evaluate_js("({people:Walk.people(input.flows,input.distances,input.assignment),"
                         "ts:Walk.transfers(input.flows,input.distances,input.assignment,[0,1,2,3])})", payload)
    assert result["people"] == []
    assert all(t["leftDistance"] is None and t["leftCost"] is None and t["delta"] is None
               for t in result["ts"])
    assert all(t["rightCost"] is not None for t in result["ts"])
