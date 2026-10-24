"""Build results/visual_demo.json: the data contract between the experiments and the app.

Contents: schema version, matrices and gate geometry, exact references for
N=1..10, metadata of the aggregated studies, recorded LNS runs (N=4..10) and
recorded direct QAOA runs (N=3, 4) with every shot. The file is verified
before it is written; any failed check aborts the export.

    python tools/export_visual_demo.py           # full export (~8 min)
    python tools/export_visual_demo.py --quick   # small smoke export (~1 min)
"""

import argparse
import json
import platform
import statistics
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.qap import trace  # noqa: E402
from src.qap.instance import load_qap10  # noqa: E402

CONTROLS = {3: 24, 4: 32, 10: 340}
QAOA_CONFIGS = (("x", 2), ("x", 3), ("perm", 2), ("perm", 3))
DEFAULT_QAOA_VIEW = {"n": 4, "depth": 3, "seed": 3}


def studies() -> dict:
    """Aggregated results already in results/, each tagged with its own configuration."""
    read = lambda name: json.loads((ROOT / "results" / name).read_text(encoding="utf-8"))  # noqa: E731
    hybrid = read("hybrid_n10.json")
    scaling = read("scaling.json")
    return {
        "qaoa_sweep": {
            "file": "results/qaoa_sweep_summary.json", "label": "Barrido QAOA N=3/4",
            "config": {"seeds": 5, "maxiter": 100, "shots": 2048, "simulator": "Aer statevector, sin ruido"},
            "note": "p=2 depende de la semilla; p=3 es la configuración robusta del mensaje principal.",
            "summary": read("qaoa_sweep_summary.json"),
        },
        "hybrid_n10": {
            "file": "results/hybrid_n10.json", "label": "Híbrido N=10 (estudio principal)",
            "config": hybrid["config"], "reference_optimum": hybrid["reference_optimum"],
            "summary": hybrid["summary"],
        },
        "scaling": {
            "file": "results/scaling.json", "label": "Escalamiento N=1…10",
            "config": scaling["config"],
            "rows": [{k: v for k, v in row.items() if k != "exact_assignment"} for row in scaling["rows"]],
        },
    }


def qaoa_summary(runs: list[dict], exact: list[dict]) -> list[dict]:
    """Per configuration: P(optimum) and valid-shot probability for every seed, with the random baseline.

    Medians come from the same recorded runs the app animates, so the evidence
    table and the animation can never disagree.
    """
    baseline = {row["n"]: row["p_optimal_random"] for row in exact}
    rows = []
    for n, mixer, reps in sorted({(r["n"], r["mixer"], r["reps"]) for r in runs}):
        group = sorted((r for r in runs if (r["n"], r["mixer"], r["reps"]) == (n, mixer, reps)),
                       key=lambda r: r["seed"])
        informative = [r for r in group if r["start_cost"] != r["optimum"]]
        rows.append({
            "n": n, "mixer": mixer, "reps": reps, "seeds": len(group),
            "p_optimal_by_seed": [r["p_optimal"] for r in group],
            "p_feasible_by_seed": [r["p_feasible"] for r in group],
            "median_p_optimal": statistics.median(r["p_optimal"] for r in group),
            "median_p_feasible": statistics.median(r["p_feasible"] for r in group),
            "random_p_optimal": baseline[n],
            # Swap circuits start from a random permutation; if that is already optimal the run proves nothing.
            "start_optimal_seeds": [r["seed"] for r in group if r["start_cost"] == r["optimum"]],
            "median_p_optimal_informative": (statistics.median(r["p_optimal"] for r in informative)
                                             if informative else None),
            "resources": next((r["resources"] for r in group if r["resources"]), None),
        })
    return rows


def verify(payload: dict) -> list[str]:
    checks = []
    exact = {row["n"]: row for row in payload["exact"]}
    for n, optimum in CONTROLS.items():
        assert exact[n]["optimum"] == optimum, f"control N={n}"
    checks.append("controles 24/32/340 reproducidos")
    checks.append("la geometría 3x4 reproduce D (verificado en gate_layout)")

    by_group: dict[tuple, list] = {}
    for run in payload["lns_runs"]:
        n = run["n"]
        by_group.setdefault((n, run["seed"]), []).append(run)
        best = run["start_cost"]
        for event in run["events"]:
            for key in ("candidate", "assignment_after_move", "assignment", "best_assignment"):
                assert sorted(event[key]) == list(range(n)), f"{run['id']} {key} no es permutación"
            assert event["best_cost"] <= best, f"{run['id']} el mejor costo subió"
            best = min(best, event["cost_after_move"])
            assert event["best_cost"] == best, f"{run['id']} best_cost inconsistente"
            if event["kick"]:
                assert len(event["kick"]["flights"]) == run["config"]["kick"], f"{run['id']} patada"
        assert run["final_cost"] == best, f"{run['id']} costo final"
    checks.append("LNS: todas las asignaciones son permutaciones; mejor costo nunca sube; costo final = mejor")
    for (n, seed), runs in by_group.items():
        starts = {tuple(r["start_assignment"]) for r in runs}
        flights = {tuple(tuple(e["flights"]) for e in r["events"]) for r in runs}
        assert len(starts) == 1 and len(flights) == 1, f"N={n} semilla {seed}: inicio o vecindarios distintos"
    checks.append("LNS: mismo inicio y misma secuencia de vuelos liberados entre subsolvers")

    for run in payload["qaoa_runs"]:
        samples = run["samples"]
        assert len(samples["order"]) == run["config"]["shots"], f"{run['id']} shots"
        assert sum(u["count"] for u in samples["unique"]) == run["config"]["shots"], f"{run['id']} conteos"
        for u in samples["unique"]:
            assert u["valid"] == (u["assignment"] is not None) == (u["cost"] is not None), run["id"]
        valid_share = sum(samples["unique"][i]["valid"] for i in samples["order"]) / len(samples["order"])
        assert abs(valid_share - run["raw_feasible_fraction"]) < 1e-12, f"{run['id']} factibilidad"
        if run["mixer"] == "perm":
            assert valid_share == 1.0, f"{run['id']} intercambio con muestra inválida"
    checks.append("QAOA: shots en orden completos; inválidas sin costo; intercambio 100 % válido")

    summary = {(r["n"], r["mixer"], r["reps"]): r for r in payload["studies"]["qaoa_recorded"]}
    view = payload["defaults"]["qaoa_view"]
    for mixer in ("x", "perm"):
        row = summary[(view["n"], mixer, view["depth"])]
        shown = next(r for r in payload["qaoa_runs"] if r["id"] == f"qaoa_n{view['n']}_{mixer}_p{view['depth']}_s{view['seed']}")
        assert shown["p_optimal"] in sorted(row["p_optimal_by_seed"])[1:4], f"vista inicial {mixer} fuera de la zona central"
    swap = summary[(view["n"], "perm", view["depth"])]
    shown_swap = next(r for r in payload["qaoa_runs"] if r["id"] == view["runs"][1])["p_optimal"]
    assert abs(shown_swap - swap["median_p_optimal"]) < 1e-3, "la semilla inicial del intercambio no es la mediana (±0,1 pp)"
    checks.append("vista inicial de QAOA = semilla central de las 5; el intercambio coincide con la mediana")
    return checks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quick", action="store_true", help="exportación reducida para probar la app")
    parser.add_argument("--output", default="results/visual_demo.json")
    parser.add_argument("--reuse-lns", action="store_true",
                        help="reutiliza las corridas LNS ya grabadas en --output (recalcularlas tarda ~7 min)")
    args = parser.parse_args()

    instance = load_qap10()
    tic = perf_counter()
    lns_sizes = (4, 6, 10) if args.quick else range(4, 11)
    lns_overrides = {"iterations": 15} if args.quick else {}
    qaoa_seeds = range(1) if args.quick else range(5)

    exact = []
    for n in range(1, instance.n + 1):
        profile = trace.exact_profile(instance.subinstance(n))
        exact.append(profile)
        print(f"exacto N={n}: {profile['optimum']} ({profile['optimal_count']} óptimas)", flush=True)

    lns_runs = []
    if args.reuse_lns:
        lns_runs = json.loads((ROOT / args.output).read_text(encoding="utf-8"))["lns_runs"]
        print(f"LNS: {len(lns_runs)} corridas reutilizadas de {args.output}", flush=True)
    else:
        for n in lns_sizes:
            for subsolver in ("exact", "qaoa", "random"):
                run = trace.lns_run(n, subsolver, seed=0, **lns_overrides)
                lns_runs.append(run)
                print(f"{run['id']}: {run['start_cost']} -> {run['final_cost']} ({run['seconds']:.1f} s)", flush=True)

    qaoa_runs = []
    for n in (3, 4):
        for mixer, reps in QAOA_CONFIGS:
            for seed in qaoa_seeds:
                run = trace.qaoa_run(n, mixer, reps, seed, resources=(seed == 0))
                qaoa_runs.append(run)
                print(f"{run['id']}: válidas {run['raw_feasible_fraction']:.3f}, "
                      f"P(óptimo) {run['p_optimal']:.3f} ({run['train_seconds']:.1f} s)", flush=True)

    payload = {
        "schema_version": trace.SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "export": "quick" if args.quick else "full",
        "lns_reused": args.reuse_lns,
        "versions": {"python": platform.python_version(),
                     **{pkg: version(pkg) for pkg in ("qiskit", "qiskit-aer", "numpy", "scipy")}},
        "instance": {
            "name": "qap10", "source": "https://miplib.zib.de/instance_details_qap10.html",
            "interpretation": "Benchmark matemático interpretado como vuelos (filas) y puertas (columnas); "
                              "no son pasajeros ni metros reales.",
            "flows": instance.flows.tolist(), "distances": instance.distances.tolist(),
            "total_flow_n10": int(instance.flows.sum() // 2),
            "subinstances": "N usa las primeras N filas y columnas de F y D",
            "cost_convention": "cada par de vuelos (i<k) se cuenta una vez: sum F[i][k] * D[g_i][g_k]",
            "layout": trace.gate_layout(instance),
        },
        "exact": exact,
        "studies": {**studies(), "qaoa_recorded": qaoa_summary(qaoa_runs, exact)},
        "defaults": {"n": 10, "left": "lns_n10_exact_s0", "right": "lns_n10_qaoa_s0",
                     "qaoa_view": {**DEFAULT_QAOA_VIEW,
                                   "runs": [f"qaoa_n4_x_p3_s{DEFAULT_QAOA_VIEW['seed']}",
                                            f"qaoa_n4_perm_p3_s{DEFAULT_QAOA_VIEW['seed']}"],
                                   "note": "p=3 es la configuración robusta. Semilla 3: el intercambio queda en la "
                                           "mediana de sus 5 semillas y X en la zona central de las suyas. "
                                           "Las medianas por configuración están en studies.qaoa_recorded."}},
        "notes": {
            "lns_events": "Un evento por iteración. outcome: improve | equal | reject. 'assignment' es el estado "
                          "al final de la iteración (después de la patada, si hubo). El subsolver exacto nunca "
                          "rechaza: la asignación actual siempre es una de sus opciones.",
            "qaoa_samples": "samples.order lista cada shot en orden de lectura como índice en samples.unique. "
                            "Las muestras inválidas no tienen costo de asignación; qubo_energy es la energía "
                            "penalizada, una magnitud distinta.",
            "objective_history": "Pasos del optimizador clásico (energía penalizada esperada); no son asignaciones.",
            "single_runs": "Cada corrida es una semilla; no es una mediana. Las medianas están en 'studies'.",
        },
        "lns_runs": lns_runs,
        "qaoa_runs": qaoa_runs,
    }
    payload["checks"] = verify(payload)
    payload["export_seconds"] = perf_counter() - tic

    output = ROOT / args.output
    tmp = output.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tmp.replace(output)
    print("\n".join(["Verificaciones:"] + [f"  ✔ {c}" for c in payload["checks"]]))
    print(f"Escrito {output} ({output.stat().st_size / 1e6:.1f} MB) en {payload['export_seconds']:.0f} s")


if __name__ == "__main__":
    main()
