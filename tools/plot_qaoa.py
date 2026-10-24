"""Plot the N=4 QAOA sweep summary for the slides (results/qaoa_n4.png)."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
SURFACE, INK, INK_2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
COLORS = {"x": "#eb6834", "perm": "#2a78d6"}
LABELS = {"x": "QAOA estándar (mezclador X + penalización)",
          "perm": "QAOA con mezclador de intercambio (siempre factible)"}


def main() -> None:
    summary = json.loads((ROOT / "results" / "qaoa_sweep_summary.json").read_text(encoding="utf-8"))
    rows = [r for r in summary
            if r["experiment"] == "mixer_depth_cvar" and r["n"] == 4 and r["alpha"] == 1.0]
    rows.sort(key=lambda r: (r["mixer"] != "x", r["reps"]))
    names = [f"{'X' if r['mixer'] == 'x' else 'Intercambio'} · p={r['reps']}" for r in rows]
    baseline = rows[0]["p_optimal_random_permutation"]

    plt.rcParams.update({"font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 11})
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), facecolor=SURFACE)
    panels = (("median_p_feasible", "Muestras factibles sin reparar"),
              ("median_p_optimal", "Probabilidad de muestrear el óptimo (costo 32)"))
    for ax, (key, title) in zip(axes, panels):
        values = [100 * r[key] for r in rows]
        ax.set_facecolor(SURFACE)
        bars = ax.barh(names, values, height=0.55, color=[COLORS[r["mixer"]] for r in rows],
                       edgecolor=SURFACE, linewidth=2)
        # Keep value labels clear of the dashed random-baseline line.
        floor = 100 * baseline if key == "median_p_optimal" else 0.0
        for bar, value in zip(bars, values):
            ax.text(max(value, floor) + 1.5, bar.get_y() + bar.get_height() / 2, f"{value:.1f}%",
                    va="center", color=INK, fontsize=10)
        if key == "median_p_optimal":
            ax.axvline(100 * baseline, color=INK_2, linestyle=(0, (4, 3)), linewidth=1.5)
            ax.text(40, 1.0, f"línea punteada = azar\n(1 de 24 permutaciones = {100 * baseline:.1f}%)",
                    color=INK_2, fontsize=9.5, va="center")
        ax.set_xlim(0, 110)
        ax.invert_yaxis()
        ax.set_title(title, loc="left", color=INK, fontsize=12, pad=10)
        ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
        ax.grid(axis="x", color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        ax.tick_params(colors=MUTED, length=0)
        for label in ax.get_yticklabels():
            label.set_color(INK_2)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color("#c3c2b7")
    axes[1].set_yticklabels([])
    handles = [plt.Rectangle((0, 0), 1, 1, color=COLORS[m]) for m in ("x", "perm")]
    fig.legend(handles, [LABELS["x"], LABELS["perm"]], loc="lower center", ncol=2,
               frameon=False, labelcolor=INK_2, bbox_to_anchor=(0.5, -0.01))
    fig.suptitle("QAP10 · N=4 (16 qubits, Aer statevector) · mediana de 5 semillas",
                 x=0.01, ha="left", color=INK, fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0.07, 1, 0.95))
    output = ROOT / "results" / "qaoa_n4.png"
    fig.savefig(output, dpi=200, facecolor=SURFACE)
    print(f"Gráfica guardada en {output}")


if __name__ == "__main__":
    main()
