"""Scaling figure N=1..10 (reads results/scaling.json, writes results/scaling.png)."""

import csv
import json
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
SURFACE, INK, INK_2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"


def style(ax, title: str) -> None:
    ax.set_facecolor(SURFACE)
    ax.grid(color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors=MUTED, length=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(AXIS)
    ax.set_title(title, loc="left", color=INK, fontsize=12, pad=10)
    ax.set_xlabel("N (vuelos = puertas)", color=INK_2)


def main() -> None:
    rows = json.loads((ROOT / "results" / "scaling.json").read_text(encoding="utf-8"))["rows"]
    plt.rcParams.update({"font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 11})
    fig, axes = plt.subplots(1, 3, figsize=(18, 5.8), facecolor=SURFACE)

    # 1. Search space: classical enumeration vs. statevector of the full QUBO.
    ax = axes[0]
    style(ax, "Tamaño del problema (escala log)")
    ns = [r["n"] for r in rows]
    ax.semilogy(ns, [r["assignments"] for r in rows], color=BLUE, linewidth=2, marker="o",
                markersize=7, label="asignaciones válidas (N!)")
    ax.semilogy(ns, [r["statevector_bytes"] for r in rows], color=ORANGE, linewidth=2, marker="o",
                markersize=7, label="bytes del statevector del QUBO (16·2^(N²))")
    ax.axhline(16 * 2 ** 16, color=INK_2, linestyle=(0, (4, 3)), linewidth=1.2)
    ax.text(1, 16 * 2 ** 16 * 3, "16 qubits: límite de QAOA directo", color=INK_2, fontsize=9.5)
    ax.legend(frameon=False, labelcolor=INK_2, loc="upper left")
    ax.set_xticks(ns)

    # 2. Direct QAOA where it fits, from the 5-seed sweep: one dot per seed.
    # N=1, 2 are left out: every assignment is optimal, so there is nothing to find.
    ax = axes[1]
    style(ax, "QAOA directo: P(óptimo) por semilla (barrido de 5 semillas)")
    sweep = list(csv.DictReader((ROOT / "results" / "qaoa_sweep.csv").open(encoding="utf-8")))
    series = (("x", "2", ORANGE, -0.18, "QAOA estándar (X), p=2"),
              ("perm", "3", BLUE, 0.18, "QAOA intercambio, p=3"))
    for n in (3, 4):
        random = next(r["p_optimal_random"] for r in rows if r["n"] == n)
        ax.hlines(100 * random, n - 0.4, n + 0.4, color=AQUA, linewidth=2.5,
                  label="azar (óptimas / N!)" if n == 3 else None)
        for mixer, reps, color, offset, label in series:
            runs = [r for r in sweep
                    if r["experiment"] == "mixer_depth_cvar" and r["n"] == str(n)
                    and r["mixer"] == mixer and r["reps"] == reps and r["alpha"] == "1.0"]
            fair = [100 * float(r["p_optimal"]) for r in runs if r["start_is_optimal"] != "True"]
            given = [100 * float(r["p_optimal"]) for r in runs if r["start_is_optimal"] == "True"]
            ax.scatter([n + offset] * len(fair), fair, s=60, color=color, edgecolor=SURFACE,
                       linewidth=2, zorder=3, label=label if n == 3 else None)
            if given:
                ax.scatter([n + offset] * len(given), given, s=60, facecolor="none",
                           edgecolor=color, linewidth=1.5, zorder=3,
                           label="arranque ya óptimo (excluido)" if n == 3 else None)
            median = statistics.median(fair)
            ax.hlines(median, n + offset - 0.12, n + offset + 0.12, color=INK, linewidth=1.5,
                      zorder=4)
            ax.text(n + offset + 0.14, median, f"{median:.0f}%", color=INK, fontsize=9.5,
                    va="center")
    ax.set_xticks([3, 4], ["N=3\n9 qubits", "N=4\n16 qubits"])
    ax.set_xlim(2.4, 4.7)
    ax.set_ylim(-4, 108)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.legend(frameon=False, labelcolor=INK_2, loc="upper center", fontsize=9.5, ncol=2,
              bbox_to_anchor=(0.5, -0.2))
    ax.text(4.68, 104, "raya negra = mediana de corridas justas", color=MUTED, fontsize=9,
            ha="right")

    # 3. Hybrid LNS where the QUBO no longer fits: median gap vs. exact optimum.
    ax = axes[2]
    style(ax, "Híbrido LNS (K=3): gap mediano vs. óptimo exacto")
    big = [r for r in rows if "lns_qaoa_median" in r]
    xs = [r["n"] for r in big]
    ax.plot(xs, [r["lns_exact_gap_median"] for r in big], color=ORANGE, linewidth=2, marker="o",
            markersize=7, label="LNS + subsolver exacto")
    ax.plot(xs, [r["lns_qaoa_gap_median"] for r in big], color=BLUE, linewidth=2, marker="o",
            markersize=7, label="LNS + QAOA (9 qubits por llamada)")
    ax.set_xticks(xs)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.set_ylim(bottom=-1)
    ax.legend(frameon=False, labelcolor=INK_2, loc="upper left")

    fig.suptitle("QAP10 · subinstancias N=1…10 (primeras N filas y columnas)", x=0.01, ha="left",
                 color=INK, fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(ROOT / "results" / "scaling.png", dpi=200, facecolor=SURFACE)
    print("Gráfica guardada en results/scaling.png")


if __name__ == "__main__":
    main()
