"""One-screen QAP10 airport laboratory. Run: streamlit run app/app.py."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from demo_data import catalog_signature, load_catalog, validate_edit  # noqa: E402
from simulation import airport_lab  # noqa: E402


def main():
    st.set_page_config(
        page_title="Mission Connections · QAP10",
        page_icon=":material/connecting_airports:",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.session_state.setdefault("live_runs", [])
    st.session_state.setdefault("live_nonce", None)
    st.session_state.setdefault("edit_validation", None)
    catalog = load_catalog(catalog_signature())
    catalog["runs"] = catalog["runs"] + st.session_state.live_runs
    catalog["validation"] = st.session_state.edit_validation
    catalog["live_completed"] = st.session_state.live_nonce

    def on_edit():
        event = st.session_state.airport_lab.edit
        if event:
            try:
                st.session_state.edit_validation = validate_edit(event, catalog)
            except ValueError as exc:
                st.session_state.edit_validation = {"ok": False, "message": str(exc), "nonce": event.get("nonce")}

    result = airport_lab(
        catalog,
        key="airport_lab",
        on_edit_change=on_edit,
        on_live_change=lambda: None,
    )

    request = result.live
    if request and request.get("nonce") != st.session_state.live_nonce:
        n, seed = int(request.get("n", 4)), int(request.get("seed", 0))
        depth = int(request.get("depth", 3))
        if n not in (3, 4) or seed not in range(5) or depth not in (2, 3):
            st.error("La prueba real admite N=3/4, semillas de 0 a 4 y p=2 o 3.")
            return
        try:
            from src.qap.instance import load_qap10
            from src.qap.qaoa import solve_qaoa
            from tools.visual_adapter import normalize_qaoa_run

            with st.status("Qiskit Aer está calculando una nueva corrida…", expanded=True) as status:
                for mixer in ("x", "perm"):
                    st.write("Penalizaciones" if mixer == "x" else "Mezclador de intercambio")
                    started = time.perf_counter()
                    solved = solve_qaoa(
                        load_qap10().subinstance(n), seed=seed, mixer=mixer,
                        reps=depth, maxiter=100, shots=2048, alpha=1.0,
                        resources=True, return_samples=True,
                    )
                    run = normalize_qaoa_run(solved, wall_seconds=time.perf_counter() - started)
                    run.update(id=f"live-{request['nonce']}-{mixer}", live=True)
                    st.session_state.live_runs.append(run)
                status.update(label="Corrida real terminada. Resultados disponibles en la simulación.", state="complete")
            st.session_state.live_nonce = request["nonce"]
            st.rerun()
        except Exception as exc:
            st.session_state.live_nonce = request["nonce"]
            st.error(f"No se pudo completar la corrida real: {exc}. Los experimentos registrados siguen disponibles.")


if __name__ == "__main__":
    main()
