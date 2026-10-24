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
