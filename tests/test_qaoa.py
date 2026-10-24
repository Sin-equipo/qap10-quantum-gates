from itertools import permutations

import numpy as np
import pytest

from src.qap import qaoa
from src.qap.classical import solve_exact
from src.qap.instance import load_qap10


@pytest.fixture(scope="module")
def base():
    return load_qap10()


@pytest.mark.parametrize("n, optimum", [(3, 24), (4, 32)])
def test_control_optima(base, n, optimum):
    assert solve_exact(base.subinstance(n))["cost"] == optimum


def test_full_instance_known_assignment(base):
    assert base.cost([2, 6, 3, 0, 8, 4, 5, 1, 7, 9]) == 340


@pytest.mark.parametrize("n", [3, 4])
def test_qubo_energy_equals_cost_on_permutations(base, n):
    instance = base.subinstance(n)
    constant, h, zz = qaoa._pauli_coefficients(
        *qaoa._qubo(instance, qaoa.certified_penalty(instance)))
    energies = qaoa._energies(n * n, constant, h, zz)
    for perm in permutations(range(n)):
        assert energies[qaoa._assignment_index(perm, n)] == pytest.approx(instance.cost(perm))


@pytest.mark.parametrize("n", [3, 4])
def test_certified_penalty_makes_ground_state_feasible(base, n):
    instance = base.subinstance(n)
    constant, h, zz = qaoa._pauli_coefficients(
        *qaoa._qubo(instance, qaoa.certified_penalty(instance)))
    energies = qaoa._energies(n * n, constant, h, zz)
    assert qaoa._feasibility_mask(n)[int(np.argmin(energies))]


def test_swap_term_paulis_commute():
    term = qaoa._swap_term(3, 0, 1, 0, 2)
    assert all(a.commutes(b) for a in term.paulis for b in term.paulis)


def test_perm_mixer_stays_feasible(base):
    result = qaoa.solve_qaoa(base.subinstance(3), mixer="perm", reps=1, maxiter=5, seed=2)
    assert result["p_feasible"] == pytest.approx(1.0, abs=1e-9)
    assert result["raw_feasible_fraction"] == 1.0
