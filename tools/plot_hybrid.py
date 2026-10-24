"""Figures for the N=10 hybrid experiment (reads results/hybrid_n10.json).

* results/hybrid_convergence.png - cost vs. LNS iteration per subsolver
* results/hybrid_final.png       - final cost per seed and method
* results/terminal_map.png       - gate layout: random start vs. hybrid result
"""

import json
import statistics
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.qap.instance import load_qap10  # noqa: E402

SURFACE, INK, INK_2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
COLORS = {"qaoa": "#2a78d6", "exact": "#eb6834", "random": "#1baf7a", "scipy_faq": "#eda100"}
LABELS = {"qaoa": "LNS + QAOA (Qiskit, 9 qubits)", "exact": "LNS + subsolver exacto (clásico)",
          "random": "LNS + subsolver aleatorio (control)", "scipy_faq": "SciPy FAQ (heurística clásica)"}
BLUES = LinearSegmentedColormap.from_list("blues", ["#cde2fb", "#86b6ef", "#2a78d6", "#104281"])


def style(ax) -> None:
    ax.set_facecolor(SURFACE)
    ax.grid(color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors=MUTED, length=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(AXIS)


def convergence(data: dict) -> None:
    fig, ax = plt.subplots(figsize=(10, 5), facecolor=SURFACE)
    style(ax)
    for method in ("random", "exact", "qaoa"):
        histories = np.array([r["history"] for r in data["runs"] if r["subsolver"] == method])
        x = np.arange(histories.shape[1])
        median = np.median(histories, axis=0)
        ax.fill_between(x, histories.min(axis=0), histories.max(axis=0),
                        color=COLORS[method], alpha=0.12, linewidth=0)
        ax.plot(x, median, color=COLORS[method], linewidth=2,
                label=f"{LABELS[method]} · mediana final {median[-1]:.0f}")
    ax.axhline(340, color=INK_2, linestyle=(0, (4, 3)), linewidth=1.5)
    ax.text(1, 343, "óptimo de referencia C* = 340", color=INK_2, fontsize=9.5, va="bottom")
    ax.set_xlabel("Iteración LNS (3 vuelos liberados por iteración)", color=INK_2)
    ax.set_ylabel("Mejor costo encontrado (siempre factible)", color=INK_2)
    ax.set_xlim(0, histories.shape[1])
    ax.legend(frameon=False, labelcolor=INK_2, loc="upper right")
    ax.set_title(f"QAP10 · N=10 · convergencia: mediana y rango de {len(histories)} semillas",
                 loc="left", color=INK, fontsize=13, fontweight="bold", pad=12)
    fig.tight_layout()
    fig.savefig(ROOT / "results" / "hybrid_convergence.png", dpi=200, facecolor=SURFACE)


def final_costs(data: dict) -> None:
    methods = ["qaoa", "exact", "random", "scipy_faq"]
    fig, ax = plt.subplots(figsize=(10, 4.8), facecolor=SURFACE)
    style(ax)
    ax.grid(axis="y", visible=False)
    for row, method in enumerate(methods):
        costs = [r["cost"] for r in data["runs"] if r["subsolver"] == method]
        jitter = np.linspace(-0.12, 0.12, len(costs))
        ax.scatter(costs, row + jitter, s=70, color=COLORS[method], edgecolor=SURFACE,
                   linewidth=2, zorder=3)
        median = statistics.median(costs)
        ax.text(max(costs) + 4, row, f"mediana {median:.0f} · gap {100 * (median - 340) / 340:.1f}%",
                color=INK, va="center", fontsize=10)
    exact = data["exact"]
    row = len(methods)
    ax.scatter([exact["cost"]], [row], s=70, marker="D", color=INK_2, zorder=3)
    ax.text(exact["cost"] + 4, row, f"{exact['cost']} en {exact['seconds']:.1f} s · recorre las 10! permutaciones",
            color=INK, va="center", fontsize=10)
    ax.axvline(340, color=INK_2, linestyle=(0, (4, 3)), linewidth=1.5)
    labels = [LABELS[m] for m in methods] + ["Enumeración exacta (referencia)"]
    ax.set_yticks(range(len(labels)), labels, color=INK_2)
    ax.invert_yaxis()
    right = max(r["cost"] for r in data["runs"] if "cost" in r)
    ax.set_xlim(330, right + 75)
    ax.set_xlabel("Costo final por semilla (línea punteada: 340)", color=INK_2)
    ax.set_title("QAP10 · N=10 · resultado final de cada semilla", loc="left", color=INK,
                 fontsize=13, fontweight="bold", pad=12)
    fig.tight_layout()
    fig.savefig(ROOT / "results" / "hybrid_final.png", dpi=200, facecolor=SURFACE)


def gate_xy(gate: int) -> tuple[float, float]:
    """Gate g sits at row g // 4, column g % 4 (verified against D below)."""
    return float(gate % 4), -float(gate // 4)


def terminal_map(data: dict) -> None:
    instance = load_qap10()
    coords = [gate_xy(g) for g in range(instance.n)]
    manhattan = np.array([[2 * (abs(a[0] - b[0]) + abs(a[1] - b[1])) for b in coords] for a in coords])
    if not (manhattan == instance.distances).all():
        raise ValueError("D no coincide con la cuadrícula 3x4 supuesta")

    hybrid = min((r for r in data["runs"] if r["subsolver"] == "qaoa"),
                 key=lambda r: (r["cost"], r["seed"]))
    panels = ((hybrid["start_assignment"], f"Inicio aleatorio (semilla {hybrid['seed']})"),
              (hybrid["assignment"], "Resultado LNS + QAOA"),
              (data["exact"]["assignment"], "Óptimo (enumeración exacta)"))
    pairs = [(i, k) for i in range(instance.n) for k in range(i + 1, instance.n)
             if instance.flows[i, k]]
    top = max(instance.flows[i, k] * 10 for i, k in pairs)

    fig, axes = plt.subplots(1, 3, figsize=(18, 5.4), facecolor=SURFACE)
    for ax, (assignment, title) in zip(axes, panels):
        ax.set_facecolor(SURFACE)
        for i, k in pairs:
            (x1, y1), (x2, y2) = coords[assignment[i]], coords[assignment[k]]
            contribution = instance.flows[i, k] * instance.distances[assignment[i], assignment[k]]
            ax.plot([x1, x2], [y1, y2], color=BLUES(contribution / top),
                    linewidth=0.6 + 0.45 * instance.flows[i, k], alpha=0.9, zorder=1,
                    solid_capstyle="round")
        for flight, gate in enumerate(assignment):
            x, y = coords[gate]
            ax.add_patch(plt.Rectangle((x - 0.22, y - 0.22), 0.44, 0.44, facecolor="#ffffff",
                                       edgecolor=AXIS, linewidth=1.2, zorder=2))
            ax.text(x, y + 0.05, f"V{flight + 1}", ha="center", va="center", fontsize=11,
                    color=INK, fontweight="bold", zorder=3)
            ax.text(x, y - 0.13, f"puerta {gate + 1}", ha="center", va="center", fontsize=7.5,
                    color=MUTED, zorder=3)
        ax.set_title(f"{title}\ncosto {instance.cost(assignment)}", loc="left", color=INK,
                     fontsize=12)
        ax.set_xlim(-0.5, 3.5)
        ax.set_ylim(-2.5, 0.5)
        ax.set_aspect("equal")
        ax.axis("off")
    sm = plt.cm.ScalarMappable(cmap=BLUES, norm=plt.Normalize(0, top))
    bar = fig.colorbar(sm, ax=axes, orientation="horizontal", fraction=0.05, pad=0.04, aspect=50)
    bar.set_label("Aporte al costo de cada conexión: flujo × distancia (grosor = flujo)",
                  color=INK_2)
    bar.ax.tick_params(colors=MUTED, length=0)
    bar.outline.set_visible(False)
    fig.suptitle("Terminal interpretada: 10 puertas en cuadrícula 3×4 (distancia Manhattan del benchmark)",
                 x=0.01, ha="left", color=INK, fontsize=13, fontweight="bold")
    fig.savefig(ROOT / "results" / "terminal_map.png", dpi=200, facecolor=SURFACE,
                bbox_inches="tight")


def main() -> None:
    plt.rcParams.update({"font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 11})
    data = json.loads((ROOT / "results" / "hybrid_n10.json").read_text(encoding="utf-8"))
    convergence(data)
    final_costs(data)
    terminal_map(data)
    print("Gráficas en results/: hybrid_convergence.png, hybrid_final.png, terminal_map.png")


if __name__ == "__main__":
    main()
