"""Protect the contract between a browser-side swap and the QAP cost model."""

import pytest

from app.demo_data import validate_edit
from src.qap.instance import load_qap10


@pytest.fixture
def catalog():
    inst = load_qap10().subinstance(4)
    return {"instances": [{"n": 4, "flows": inst.flows.tolist(),
                            "distances": inst.distances.tolist()}]}


def test_manual_swap_is_validated_against_qap(catalog):
    assignment = [1, 0, 2, 3]
    expected = load_qap10().subinstance(4).cost(assignment)
    result = validate_edit({"n": 4, "assignment": assignment,
                            "cost": expected, "nonce": 42}, catalog)
    assert result == {"ok": True, "cost": expected, "nonce": 42, "n": 4}


def test_duplicate_gates_are_rejected(catalog):
    with pytest.raises(ValueError, match="distinta"):
        validate_edit({"n": 4, "assignment": [0, 0, 2, 3], "cost": 0}, catalog)


def test_browser_cannot_supply_a_false_cost(catalog):
    with pytest.raises(ValueError, match="no coincide"):
        validate_edit({"n": 4, "assignment": [0, 1, 2, 3], "cost": 0}, catalog)
