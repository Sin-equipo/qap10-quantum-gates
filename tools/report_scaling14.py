"""Generate the final scaling report/figure from completed measured jobs."""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
LABELS = {"exact": "LNS + exacto", "qaoa": "LNS + QAOA", "random": "LNS + azar", "scipy_faq": "SciPy FAQ"}
COLORS = {"exact": "#4d7fbb", "qaoa": "#1b9380", "random": "#d48b40", "scipy_faq": "#9a7597"}


def main():
    data = json.loads((ROOT / "results/scaling14.json").read_text(encoding="utf-8"))
    assert data["complete"], "Termina scaling14_study.py antes de generar conclusiones"
    refs, rows, summary = data["references"], data["rows"], data["summary"]
    fig, axes = plt.subplots(1, 3, figsize=(17, 5.4), facecolor="#fcfcfb")
    for method, label in LABELS.items():
        group = [r for r in summary if r["method"] == method]
        xs = [r["n"] for r in group]
        for ax, key, unit in ((axes[0], "median_gap_percent", 1),
                              (axes[1], "median_seconds", 1),
                              (axes[2], "median_peak_rss_bytes", 2**20)):
            ax.plot(xs, [r[key]/unit for r in group],
                    marker={"exact": "s", "qaoa": "o", "random": "^", "scipy_faq": "D"}[method],
                    linestyle={"exact": "-", "qaoa": "-", "random": ":", "scipy_faq": "-."}[method],
                    color=COLORS[method], label=label)
    axes[1].plot([r["n"] for r in rows], [r["exact_seconds"] for r in rows], "s--",
                 color="#576041", label="Referencia exacta (B&B)")
    axes[2].plot([r["n"] for r in rows], [r["exact_peak_rss_bytes"]/2**20 for r in rows], "s--",
                 color="#576041", label="Referencia exacta (B&B)")
    for ax, title, ylabel in zip(axes,
            ("Calidad: menor brecha es mejor", "Tiempo medido (escala logarítmica)", "Memoria RSS del proceso"),
            ("Brecha mediana respecto al óptimo (%)", "Segundos", "MiB; mediana de picos muestreados")):
        ax.set_facecolor("#fcfcfb")
        ax.set_title(title, fontsize=12, loc="left")
        ax.set_xlabel("Vuelos / puertas (N)")
        ax.set_ylabel(ylabel)
        ax.set_xticks(range(10, 15))
        ax.grid(alpha=.2)
        ax.spines[["top", "right"]].set_visible(False)
    axes[1].set_yscale("log")
    axes[0].set_ylim(bottom=0)
    handles, labels = axes[1].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=5, frameon=False, fontsize=10)
    fig.suptitle("QAP10 → ampliación sintética N=14 · cinco semillas, 60 iteraciones, K=3 (9 qubits)",
                 x=.03, ha="left", fontsize=14, fontweight="bold")
    fig.text(.03, .08, "N=10 original; N=11…14 sintéticos. RSS incluye Python y librerías; intervalo solicitado 5 ms. Aer ideal, sin hardware ni ruido.",
             fontsize=9, color="#52514e")
    fig.tight_layout(rect=(0, .12, 1, .93))
    fig.savefig(ROOT / "results/scaling14.png", dpi=180, facecolor=fig.get_facecolor())
    plt.close(fig)

    q14 = next(r for r in summary if r["n"] == 14 and r["method"] == "qaoa")
    local14 = next(r for r in summary if r["n"] == 14 and r["method"] == "exact")
    faq14 = next(r for r in summary if r["n"] == 14 and r["method"] == "scipy_faq")
    ref14 = refs["14"]
    calls = [e["qaoa"] for run in data["lns_runs"] if run["subsolver"] == "qaoa" for e in run["events"]]
    max_error = max(call["subspace_verification_max_probability_error"] for call in calls)
    lines = ["# Escalamiento final: QAP10 → N=14", "",
        f"**N=14: óptimo certificado {ref14['optimum']}; LNS + QAOA: mejor {q14['best_cost']}, mediana {q14['median_cost']}, "
        f"brecha mediana {q14['median_gap_percent']:.2f}%, {q14['optimal_hits']}/{q14['runs']} semillas alcanzaron el óptimo.**", "",
        "![Tiempo, memoria y calidad](../results/scaling14.png)", "",
        "## Instancias y procedencia", "",
        "N≤10 mantiene las primeras N filas y columnas de QAP10. La ampliación N=11…14 es sintética y anidada: conserva "
        "exactamente las matrices originales de diez elementos. Para cada nuevo vuelo k y cada i<k se muestrea un flujo "
        "de los 45 valores originales F[i,k] (incluidos los ceros), en orden k=10…13, i=0…k−1, con NumPy default_rng y "
        "semilla **20261025**. La matriz F sigue siendo simétrica, entera y de diagonal cero. Las puertas continúan la cuadrícula "
        "de cuatro columnas: D[a,b]=2·(|a//4−b//4|+|a%4−b%4|). Cada N usa el bloque principal de la misma ampliación.", "",
        "Es un escenario de escalamiento del equipo; **no es un benchmark MIPLIB QAP14 ni una ampliación medida en un aeropuerto real**. "
        "Los datos se fijan con independencia de las semillas de optimización y del resultado. Cada par i<k cuenta una vez.", "",
        "## Referencias óptimas certificadas", "",
        "| N | Óptimo | Cota final | Nº óptimos | Tiempo medido (s) | RSS pico (MiB) | Nodos B&B |",
        "|---|---:|---:|---:|---:|---:|---:|"]
    for n, ref in refs.items():
        lines.append(f"| {n} | {ref['optimum']} | {ref['lower_bound']} | {ref['optimal_count']} | {ref['measured_seconds']:.4f} | "
                     f"{ref['peak_rss_bytes']/2**20:.1f} | {ref['nodes']:,} |")
    enum_job = json.loads((ROOT / "results/scaling14_jobs/n10_enumeration_sNone.json").read_text(encoding="utf-8"))
    enum = enum_job["result"]
    lines += ["", "La referencia usa **ramificación y poda (branch and bound), cota Gilmore–Lawler y asignación lineal de SciPy**. "
        "Comienza con soluciones obtenidas por FAQ + 2-opt desde ocho semillas clásicas; nunca carga el óptimo conocido. "
        "La búsqueda exacta certifica el mínimo y cuenta todas las asignaciones que lo alcanzan. Las primeras 32 se guardan como ejemplos.", "",
        "En un nodo, C es el costo ya fijado y M[i,j] es la interacción de un vuelo libre con los vuelos fijos. Para cada fila, "
        "ordenamos los flujos restantes de menor a mayor y las distancias de mayor a menor, excluyendo las diagonales. Su producto "
        "es una cota inferior por reordenamiento que relaja la consistencia entre vuelos. La asignación lineal de la matriz "
        "2M+A_ordenada·B_ordenadaᵀ da una cota para **dos veces** el costo restante. Se poda solo si 2C+cota>2·mejor; "
        "la desigualdad estricta permite contar también óptimos empatados. Todos estos cálculos usan enteros. Al agotar el árbol, "
        "el mejor costo es óptimo global. Si vence el tiempo límite, el script no declara un óptimo y detiene la generación del informe.", "",
        f"El nuevo exacto reproduce los controles N=3→24, N=4→32 y N=10→340. Además, se ejecutó la enumeración de N=10 "
        f"en la misma campaña: costo {enum['cost']}, {enum['measured_seconds']:.4f} s, RSS pico {enum['peak_rss_bytes']/2**20:.1f} MiB. "
        "Las pruebas comparan el nuevo exacto y el número de óptimos contra enumeración independiente de seis instancias pequeñas "
        "aleatorias, con términos lineales; no sustituyen una certificación independiente de N=14 por otro solver.", "",
        "## Comparación de métodos", "",
        "| N | Método | Mediana | Mejor | Brecha mediana | Aciertos óptimos | Tiempo mediano (s) | RSS mediana (MiB) |",
        "|---|---|---:|---:|---:|---:|---:|---:|"]
    for r in summary:
        lines.append(f"| {r['n']} | {LABELS[r['method']]} | {r['median_cost']} | {r['best_cost']} | {r['median_gap_percent']:.2f}% | "
                     f"{r['optimal_hits']}/{r['runs']} | {r['median_seconds']:.4f} | {r['median_peak_rss_bytes']/2**20:.1f} |")
    lines += ["", "Todos los resultados de la tabla son asignaciones factibles. El gap utiliza el óptimo certificado de **cada instancia**, "
        "no 340 para todos los tamaños. Las corridas empiezan sin conocer el óptimo. El híbrido usa resultados crudos factibles "
        "del mezclador de intercambio; no requiere reparación clásica.", "",
        f"En N=14, la mediana de acierto del óptimo **local** por llamada fue {100*q14['median_subproblem_hit_rate']:.1f}%. "
        f"El óptimo **global** se alcanzó en {q14['optimal_hits']}/{q14['runs']} semillas. Resolver un vecindario de seis opciones "
        "no garantiza la mejor permutación completa. La calidad depende también de los vecindarios, las patadas, los arranques y las "
        "propuestas del subsolver; estas corridas no aíslan una única causa del estancamiento.", "",
        f"La comparación de N=14 distingue los controles: mediana QAOA {q14['median_cost']}, "
        f"LNS con exacto local {local14['median_cost']} y FAQ {faq14['median_cost']}. "
        f"Sus tiempos medianos fueron {q14['median_seconds']:.4f}, {local14['median_seconds']:.4f} y {faq14['median_seconds']:.4f} s. "
        "Un mejor recorrido dentro de una trayectoria LNS no demuestra que el subsolver sea más exacto: los estados aceptados, "
        "el estancamiento y las patadas divergen. Se necesita distinguir mejor costo, mayor probabilidad y menor tiempo, "
        "y comprobar resultados con más familias de instancias antes de generalizar.", "",
        "## Protocolo y límites de las mediciones", "",
        "- Cinco semillas 0…4 por método y tamaño; 60 iteraciones LNS, K=3, patada de 4 vuelos tras 12 iteraciones sin mejora.",
        "- QAOA: p=2, COBYLA con hasta 60 evaluaciones, 512 shots; Qiskit Aer statevector ideal. Cada llamada usa nueve qubits; "
        "el QUBO completo de N=14 tendría 196 qubits y no se simula.",
        "- Aceleración de simulación: el entrenamiento reproduce exactamente el mismo circuito en el subespacio de las seis "
        "permutaciones factibles, mediante fases y rotaciones de intercambio. Es cálculo clásico de amplitudes; no es hardware. "
        "Después se verifica la distribución entrenada con el circuito completo de nueve qubits en Aer y se obtienen los 512 shots "
        "con SamplerV2 de Qiskit. La verificación es obligatoria en **cada llamada** y aborta si el error máximo supera 1e−8. "
        f"En esta campaña se verificaron {len(calls)} llamadas, con error máximo de probabilidad {max_error:.3e}. "
        "Los tests también comparan ambas simulaciones en ángulos arbitrarios N=3/4. El redondeo numérico puede cambiar "
        "la trayectoria de COBYLA frente a corridas históricas, aunque ambas formas representan el mismo circuito; por eso N=10 se midió otra vez.",
        "- LNS exacto, aleatorio y QAOA comparten por semilla la asignación inicial y los vuelos liberados en cada iteración. "
        "Las propuestas y las aceptaciones pueden producir estados distintos. La referencia global no interviene en esa búsqueda.",
        "- Las corridas se miden en procesos separados y de forma secuencial. Cada proceso importa la misma pila de librerías antes "
        "de medir. OpenMP, OpenBLAS, MKL y Rayon se limitan a un hilo; se desactiva el paralelismo de Qiskit. "
        "Esto evita sobrecostos de concurrencia en estos circuitos pequeños; no modifica el circuito ni el presupuesto de búsqueda.",
        "- El tiempo incluye la llamada completa al solver, sus inicios heurísticos y la validación de las trazas; excluye imports, "
        "arranque del proceso y escritura del JSON. La reproducción visual usa las marcas internas de cada iteración.",
        "- Memoria: RSS del proceso con intervalo solicitado de 5 ms durante el solver, incluyendo Python y librerías. Se guardan RSS inicial, "
        "pico observado, incremento y pico de vida del proceso, además de tiempo CPU. El muestreo puede omitir picos breves. "
        "Los métodos muy rápidos pueden tener pocas muestras; un incremento cero no significa uso de memoria cero. No es memoria de una QPU.",
        "- Se comparan presupuestos de iteraciones, **no presupuestos iguales de tiempo**. FAQ usa su propio criterio de parada. "
        "Los tiempos históricos sin estos controles se conservan y no se mezclan con los nuevos para calcular aceleraciones.",
        "- Los tiempos corresponden a esta máquina y campaña. La carga y la frecuencia de CPU pueden cambiar durante el barrido; "
        "no se estima una ley asintótica ni el tiempo de ejecución de una QPU.",
        "- Cinco semillas y una familia sintética no permiten generalizar a otros aeropuertos o instancias, ni demostrar ventaja cuántica.", "",
        "## Qué cambia al presentar la demo", "",
        "El selector cubre N=1…14, con accesos N=4, N=10 y N=14. Para N=10…14 están disponibles las cinco semillas "
        "y sus trazas verdaderas. N>10 muestra la etiqueta ampliación sintética. «Óptimo exacto» carga la asignación global "
        "certificada; «Óptimo → resultado QAOA» permite ver las conexiones responsables de la brecha. Los tiempos de cálculo "
        "son mediciones; el desplazamiento de las personas usa segundos ilustrativos y distancia del modelo. "
        "Una llegada más temprana de un grupo no reemplaza la comparación del costo total.", "",
        "La comparación nueva de N=10 usa 60 iteraciones, para emparejarla con N=11…14. El estudio histórico de N=10 "
        "con 150 iteraciones sigue en su apartado propio. El QAOA directo N=3/4 conserva sus experimentos originales.", "",
        "## Reproducción y archivos", "", "```powershell", "pip install -r requirements.txt", "python scaling14_study.py",
        "python tools/report_scaling14.py", "python -m pytest tests", "streamlit run app/app.py", "```", "",
        "La ejecución reanuda únicamente jobs con parámetros y hash del código compatibles. "
        "`python scaling14_study.py --assemble-only` reconstruye las tablas de los jobs completos sin volver a calcular.", "",
        "- `results/scaling14.json`: matrices, referencias, configuración, resumen y trazas LNS.",
        "- `results/scaling14_summary.csv`: tabla de métricas por método/tamaño.",
        "- `results/scaling14_jobs/`: cada medición individual, semillas, asignaciones, trazas, memoria, entorno y hash del código.",
        "- `src/qap/exact_bound.py`: método exacto y derivación de su cota.", "",
        "Fuentes del método: [Lawler, 1963](https://doi.org/10.1287/mnsc.9.4.586), "
        "[asignación lineal SciPy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linear_sum_assignment.html), "
        "[FAQ y 2-opt SciPy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.quadratic_assignment.html).", "",
        f"Hash de las fuentes ejecutadas: `{data['solver_source_sha256']}`.", "",
        "Entorno medido:", "", "```json", json.dumps(data["environment"], indent=2, ensure_ascii=False), "```", ""]
    (ROOT / "docs/scaling14_results.md").write_text("\n".join(lines), encoding="utf-8")
    print("Escritos docs/scaling14_results.md y results/scaling14.png")


if __name__ == "__main__":
    main()
