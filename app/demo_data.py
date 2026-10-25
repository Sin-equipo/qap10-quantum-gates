"""Read-only evidence loading and authoritative validation for the visual app."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    "data/qap10_matrices.json", "results/scaling.json",
    "results/qaoa_sweep_summary.json", "results/hybrid_n10.json",
    "results/visual_demo.json",
    "results/visual_demo_quick.json",
    "results/scaling14.json",
)


def catalog_signature() -> tuple:
    return tuple((name, (ROOT / name).stat().st_mtime_ns if (ROOT / name).exists() else 0) for name in SOURCES)


@st.cache_data(max_entries=4)
def load_catalog(signature: tuple) -> dict:
    def read(name, default):
        path = ROOT / name
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default

    matrices = read(SOURCES[0], {})
    scaling = read(SOURCES[1], {"rows": [], "config": {}})
    sweep = read(SOURCES[2], [])
    hybrid = read(SOURCES[3], {})
    visual = read(SOURCES[4], {}) or read(SOURCES[5], {})
    extension = read("results/scaling14.json", {})
    if not extension.get("complete"):
        extension = {}
    if visual and "runs" not in visual:
        from tools.visual_adapter import normalize_catalog

        visual = normalize_catalog(visual)
    instances = []
    for row in scaling["rows"]:
        n = row["n"]
        instances.append({
            "n": n,
            "flows": [r[:n] for r in matrices["flows"][:n]],
            "distances": [r[:n] for r in matrices["distances"][:n]],
            "coordinates": [[i % 4, i // 4] for i in range(n)],
            "optimum": row["optimum"], "exact_assignment": row["exact_assignment"],
            "exact_seconds": row["exact_seconds"], "stats": row,
            "reference_method": "enumeration", "synthetic": False,
            "study_seeds": scaling["config"].get("seeds", 3),
        })
    runs = visual.get("runs", [])
    if extension:
        from tools.visual_adapter import normalize_lns_run

        extended = extension["instance"]
        instances = [item for item in instances if item["n"] < 10]
        for row in extension["rows"]:
            n = row["n"]
            instances.append({"n": n, "flows": [r[:n] for r in extended["flows"][:n]],
                "distances": [r[:n] for r in extended["distances"][:n]],
                "coordinates": [[i % 4, i // 4] for i in range(n)],
                "optimum": row["optimum"], "exact_assignment": row["exact_assignment"],
                "exact_seconds": row["exact_seconds"], "stats": row,
                "reference_method": row["reference_method"], "synthetic": n > 10,
                "study_seeds": extension["config"]["seeds"]})
        runs = [r for r in runs if not (r["kind"] == "lns" and r["n"] >= 10)]
        runs += [normalize_lns_run(run) for run in extension["lns_runs"]]
    return {
        "schema_version": 1, "instances": instances, "runs": runs,
        "studies": visual.get("studies", {}),
        "scaling": scaling, "sweep": sweep, "legacy": hybrid.get("summary", []),
        "generated_at": extension.get("generated_at", visual.get("created_at")),
        "extension": {k: v for k, v in extension.items() if k not in ("lns_runs", "instance")},
    }


def validate_edit(event: dict, catalog: dict) -> dict:
    n = event.get("n")
    instance = next((r for r in catalog["instances"] if r["n"] == n), None)
    assignment = event.get("assignment", [])
    if instance is None or not isinstance(assignment, list) or len(assignment) != n:
        raise ValueError("Instancia o asignación inválida.")
    if any(type(x) is not int for x in assignment) or sorted(assignment) != list(range(n)):
        raise ValueError("Cada vuelo debe recibir una puerta distinta.")
    cost = sum(instance["flows"][i][k] * instance["distances"][assignment[i]][assignment[k]]
               for i in range(n) for k in range(i + 1, n))
    if event.get("cost") != cost:
        raise ValueError("El costo visual no coincide con el modelo QAP.")
    return {"ok": True, "cost": cost, "nonce": event.get("nonce"), "n": n}
