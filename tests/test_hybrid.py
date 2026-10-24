from itertools import permutations

import numpy as np
import pytest

from src.qap import qaoa
from src.qap.classical import solve_exact_blocks
from src.qap.hybrid import lns, subproblem
from src.qap.instance import load_qap10


@pytest.fixture(scope="module")
def base():
    return load_qap10()


def test_exact_blocks_finds_reference_optimum(base):
    assert solve_exact_blocks(base)["cost"] == 340


@pytest.mark.parametrize("seed", range(5))
def test_subproblem_cost_decomposition(base, seed):
    rng = np.random.default_rng(seed)
    assignment = [int(g) for g in rng.permutation(base.n)]
    flights = sorted(int(i) for i in rng.choice(base.n, size=3, replace=False))
    sub, gates, constant = subproblem(base, assignment, flights)
    for perm in permutations(range(3)):
        full = list(assignment)
        for a, flight in enumerate(flights):
            full[flight] = gates[perm[a]]
        assert base.cost(full) == constant + sub.cost(perm)


def test_qubo_with_linear_term_matches_cost(base):
    sub, _, _ = subproblem(base, list(range(base.n)), [0, 4, 7])
    constant, h, zz = qaoa._pauli_coefficients(*qaoa._qubo(sub, qaoa.certified_penalty(sub)))
    energies = qaoa._energies(9, constant, h, zz)
    for perm in permutations(range(3)):
        assert energies[qaoa._assignment_index(perm, 3)] == pytest.approx(sub.cost(perm))
    assert qaoa._feasibility_mask(3)[int(np.argmin(energies))]


@pytest.mark.parametrize("subsolver", ["exact", "random", "qaoa"])
def test_lns_returns_valid_non_worse_assignment(base, subsolver):
    run = lns(base, subsolver=subsolver, iterations=3, seed=1, maxiter=10, shots=128)
    assert run["feasible"]
    assert run["cost"] <= run["start_cost"]
    assert all(b <= a for a, b in zip(run["history"], run["history"][1:]))


@pytest.mark.parametrize("traced", [False, True])
def test_final_kick_improvement_is_retained(base, traced):
    """The last exploration kick reaches 48 after the local move stays at 50."""
    instance = base.subinstance(4)
    run = lns(instance, subsolver="random", iterations=1, seed=2,
              stall_limit=1, kick=4, trace=traced)
    assert run["start_cost"] == 50
    assert run["cost"] == instance.cost(run["assignment"]) == 48
    assert run["history"] == [50, 48]
    assert run["current_history"] == [50, 48]
    assert run["best_tracking"] == "including_kicks"
    if traced:
        event = run["events"][0]
        assert event["kick"] is not None
        assert event["cost_after_move"] == 50
        assert event["cost"] == event["best_cost"] == 48
        assert event["best_assignment"] == run["assignment"]
