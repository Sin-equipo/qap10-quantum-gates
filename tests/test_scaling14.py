"""Independent exhaustive checks for exact certificates and nested extension."""

from itertools import permutations

import numpy as np
import pytest

from src.qap.exact_bound import lower_bound_matrix, solve_branch_bound
from src.qap.instance import QAPInstance, extended_qap14, load_instance, load_qap10


def test_extension_preserves_all_original_controls_and_geometry():
    original, extended = load_qap10(), extended_qap14()
    assert np.array_equal(extended.flows[:10, :10], original.flows)
    assert np.array_equal(extended.distances[:10, :10], original.distances)
    assert np.array_equal(extended.flows, extended_qap14().flows)
    assert set(extended.flows.flatten()) <= set(original.flows.flatten())
    for n in range(1, 15):
        instance = load_instance(n)
        assert instance.n == n
        for a in range(n):
            for b in range(n):
                assert instance.distances[a, b] == 2 * (abs(a//4 - b//4) + abs(a%4 - b%4))


@pytest.mark.parametrize("seed", range(6))
def test_bound_and_optimal_count_match_exhaustive_search_with_linear_costs(seed):
    from scipy.optimize import linear_sum_assignment

    rng, n = np.random.default_rng(seed), 6
    a, b = rng.integers(0, 8, (n, n)), rng.integers(0, 8, (n, n))
    f, d = np.triu(a, 1), np.triu(b, 1)
    f, d = f + f.T, d + d.T
    linear = rng.integers(-3, 10, (n, n))
    instance = QAPInstance(f, d, linear=linear)
    values = [instance.cost(p) for p in permutations(range(n))]
    optimum = min(values)
    bound = lower_bound_matrix(f, d, linear)
    rows, cols = linear_sum_assignment(bound)
    assert int(bound[rows, cols].sum()) <= 2 * optimum
    result = solve_branch_bound(instance)
    assert result["certified"] and result["status"] == "optimal"
    assert result["cost"] == result["lower_bound"] == optimum
    assert result["optimal_count"] == values.count(optimum)
    assert instance.cost(result["assignment"]) == optimum


@pytest.mark.parametrize("n,optimum", [(3, 24), (4, 32), (10, 340)])
def test_new_exact_method_reproduces_the_challenge_controls(n, optimum):
    result = solve_branch_bound(load_instance(n))
    assert result["cost"] == result["optimum"] == result["lower_bound"] == optimum
    assert result["count_all_optima"]


def test_new_catalog_covers_every_size_with_certified_references():
    from app.demo_data import catalog_signature, load_catalog

    catalog = load_catalog(catalog_signature())
    assert [i["n"] for i in catalog["instances"]] == list(range(1, 15))
    for item in catalog["instances"]:
        instance = load_instance(item["n"])
        assert instance.cost(item["exact_assignment"]) == item["optimum"]
        assert item["synthetic"] == (item["n"] > 10)
    extension = catalog["extension"]
    assert extension["complete"]
    for n in range(10, 15):
        ref = extension["references"][str(n)]
        assert ref["certified"] and ref["lower_bound"] == ref["optimum"]
        for seed in range(5):
            runs = [r for r in catalog["runs"] if r["n"] == n and r["kind"] == "lns" and r["seed"] == seed]
            assert {r["method"] for r in runs} == {"exact", "random", "qaoa"}
            assert len({tuple(r["start_assignment"]) for r in runs}) == 1
            assert len({tuple(tuple(e["flights"]) for e in r["events"][1:-1]) for r in runs}) == 1
            for run in runs:
                assert load_instance(n).cost(run["final_assignment"]) == run["cost"] >= ref["optimum"]


@pytest.mark.parametrize("n,reps,with_fixed", [(3, 1, False), (3, 2, False), (3, 3, False), (4, 2, False), (3, 2, True)])
def test_restricted_simulation_matches_full_qiskit_circuit_at_arbitrary_angles(n, reps, with_fixed):
    from qiskit import transpile
    from qiskit_aer import AerSimulator
    from src.qap import qaoa

    instance = load_instance(n)
    if with_fixed:
        from src.qap.hybrid import subproblem
        instance, _, _ = subproblem(load_instance(14), list(range(14)), [0, 5, 11])
    offset, linear, quadratic = qaoa._qubo(instance, qaoa.certified_penalty(instance))
    c, h, zz = qaoa._pauli_coefficients(offset, linear, quadratic)
    scale = max(np.abs(h).max(), max(abs(v) for v in zz.values()))
    perms = list(permutations(range(n)))
    indices = [qaoa._assignment_index(p, n) for p in perms]
    energies = qaoa._energies(n*n, c, h, zz)[indices]
    rng = np.random.default_rng(812)
    simulator = AerSimulator(method="statevector", max_parallel_threads=1)
    for _ in range(3):
        start = perms[int(rng.integers(len(perms)))]
        params = rng.uniform(-2, 2, 2 * reps)
        qc = qaoa._ansatz(n, reps, h/scale, {k: v/scale for k, v in zz.items()}, "perm", start)
        qc = qc.assign_parameters(params)
        qc.save_statevector()
        full = np.abs(np.asarray(simulator.run(transpile(qc, simulator)).result().get_statevector()))**2
        reduced = np.abs(qaoa._permutation_state(n, reps, start, energies, scale, params))**2
        assert np.allclose(full[indices], reduced, atol=1e-10)
        assert full[indices].sum() == pytest.approx(1.0, abs=1e-10)


def test_accelerated_solver_keeps_actual_aer_verification_and_sampling():
    from src.qap.qaoa import solve_qaoa

    result = solve_qaoa(load_instance(3), mixer="perm", reps=2, maxiter=12, shots=64,
                        training_simulator="permutation_subspace")
    assert result["subspace_verification_max_probability_error"] < 1e-8
    assert result["raw_feasible_shots"] == 64
    assert result["raw_feasible_fraction"] == 1
    assert load_instance(3).cost(result["raw_best_assignment"]) == result["raw_best_cost"]


def test_n14_manual_swap_uses_the_extended_model_on_the_server():
    from app.demo_data import validate_edit

    instance = load_instance(14)
    assignment = list(range(14))
    assignment[0], assignment[13] = assignment[13], assignment[0]
    cost = instance.cost(assignment)
    catalog = {"instances": [{"n": 14, "flows": instance.flows.tolist(),
                              "distances": instance.distances.tolist()}]}
    assert validate_edit({"n": 14, "assignment": assignment, "cost": cost}, catalog)["cost"] == cost
    with pytest.raises(ValueError, match="no coincide"):
        validate_edit({"n": 14, "assignment": assignment, "cost": cost-1}, catalog)
