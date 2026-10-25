# QAP10 · Track A: puertas de embarque

**Proyecto:** Misión conexiones · **Equipo:** Sin equipo · **Categoría:** 5.1 Industria (reto NTT DATA)

**Integrantes:** Luis Manuel Espinoza Navarrete · Italo Alfredo Chinto Rentería Hinojosa · Andrea Melissa Sanchez Revolledo · Alexander Julian Bravo Tarazona.

Reto NTT DATA del Qiskit Fall Fest 2026. Modela diez vuelos de conexión y diez puertas con la instancia matemática QAP10. Compara un baseline clásico exacto con QAOA en Qiskit para N=3/4 y con un híbrido LNS + QAOA hasta N=14. N=11…14 son una ampliación sintética reproducible que preserva QAP10.

**El aeropuerto es una interpretación del benchmark.** Los flujos y distancias de QAP10 no son datos medidos de vuelos ni de puertas reales; no deben presentarse como pasajeros, metros ni ahorros operativos reales.

**Descripción breve para la entrega:** Misión conexiones es un laboratorio interactivo para estudiar la asignación de vuelos a puertas mediante el benchmark QAP10. Compara métodos clásicos con QAOA simulado en Qiskit Aer y un enfoque híbrido por vecindarios. La demo permite explorar conexiones, intercambiar vuelos y comparar costo, factibilidad, probabilidades y tiempos registrados. Los experimentos reproducibles cubren N=1…14; N>10 es una ampliación sintética con referencia óptima certificada; muestran cómo conservar restricciones en el circuito mejora ciertos resultados pequeños y documentan los límites del híbrido, sin demostrar ventaja cuántica.

## Resultados en 30 segundos

| Qué se midió | Resultado |
|---|---|
| Controles del reto, con matrices recuperadas del MPS | N=3 → 24, N=4 → 32, N=10 → 340, exactos por enumeración |
| QAOA estándar (penalización), N=4, p=3, 5 semillas | P(óptimo) 0.3 %, 3.7 % de muestras válidas; no supera al azar (8.3 %) |
| QAOA con mezclador de intercambio, N=4, p=3 | P(óptimo) 36.8 %, 100 % válidas; 4.4× el azar (simulación ideal, sin ruido) |
| Híbrido LNS + QAOA, N=10 (9 qubits por llamada) | Mediana 374 (gap 10 %), mejor 360; no llega a 340 y no supera al LNS clásico |
| Referencia exacta, N=10 | 340 en ≈2.5 s |
| Final N=14, ampliación sintética (5 semillas, 60 iteraciones) | Óptimo 728 certificado en 6.32 s; QAOA: mediana 830, mejor 794, gap mediano 14.01 %, 0/5 aciertos |

No afirmamos ventaja cuántica ni medimos hardware real o ruido. El hallazgo medido es que el diseño del mezclador pesa más que el castigo de las restricciones.

## Final: ampliación hasta N=14

La demo permite explorar **todos los tamaños N=1…14**. N≤10 conserva QAP10; N=11…14 amplía la misma instancia con flujos sintéticos de semilla fija y nuevas puertas en la misma cuadrícula. La etiqueta de la interfaz identifica esa ampliación.

La campaña nueva compara N=10…14 con cinco semillas por método y 60 iteraciones: LNS + QAOA, LNS + exacto local, LNS + azar y SciPy FAQ. Incluye una **referencia óptima global por ramificación y poda con cota Gilmore–Lawler**, conteo de óptimos, calidad, factibilidad, tiempo y memoria RSS. El exacto reproduce 24/32/340; el óptimo certificado de esta ampliación N=14 es **728**. QAOA obtuvo mediana **830**, mejor **794** y **0/5** aciertos del óptimo (gap mediano **14,01 %**). La referencia nunca se usa como inicio.

QAOA mantiene nueve qubits por llamada. Para agilizar esta campaña, el entrenamiento simula el mismo circuito dentro de sus seis permutaciones factibles; cada llamada verifica la distribución con el circuito completo en Qiskit Aer y obtiene 512 shots con SamplerV2. Es una aceleración clásica de simulación, sin hardware cuántico. La campaña histórica sigue identificada con sus parámetros propios.

**Resultados y explicación:** [`docs/scaling14_results.md`](docs/scaling14_results.md). **Datos completos:** [`results/scaling14.json`](results/scaling14.json). **Métricas:** [`results/scaling14_summary.csv`](results/scaling14_summary.csv). **Mediciones individuales:** [`results/scaling14_jobs/`](results/scaling14_jobs/).

```powershell
python scaling14_study.py
python tools/report_scaling14.py
streamlit run app/app.py
```

El script reanuda solo mediciones con parámetros y hash de código compatibles. Para regenerar el resumen sin nuevas corridas: `python scaling14_study.py --assemble-only`.

## Notebook de análisis

**Análisis final N=10…14:** [`notebooks/scaling14_analysis.ipynb`](notebooks/scaling14_analysis.ipynb), con tablas, gráficas y verificación de las mediciones guardadas. Permite revisar la comparación sin volver a ejecutar QAOA.

[`notebooks/qap10_track_a_analysis.ipynb`](notebooks/qap10_track_a_analysis.ipynb) conserva la exploración inicial en Colab y puede ejecutarse desde la raíz del repositorio con `data/qap10.mps.gz`. Instala `requirements.txt` y, si aún no tienes Jupyter, `pip install jupyterlab ipykernel`. Sus resultados son exploratorios y están marcados como anteriores a los estudios consolidados; el código N=10 usa vecindarios de cuatro vuelos y reparación clásica de asignaciones. El análisis vigente está en `docs/qaoa_results.md`, `docs/hybrid_results.md` y `docs/scaling_results.md`.

Notebook original en [Google Colab](https://colab.research.google.com/drive/1M99ZgiXAJjfulGNs5h-nACDdR3QCSg31?usp=sharing).

**Dónde mirar, según el criterio:**

| Criterio | Archivos |
|---|---|
| Modelo, lectura de datos y factibilidad | `src/qap/instance.py`, `data/`, `docs/first_attempt.md`, `docs/scaling_results.md` |
| Uso de Qiskit | `src/qap/qaoa.py`, `docs/qaoa_results.md` |
| Comparación con el baseline clásico | `src/qap/classical.py`, `src/qap/hybrid.py`, `docs/hybrid_results.md` |
| Rigor: tiempos, límites y escalamiento | `docs/scaling_results.md`, sección «Lectura honesta» de `docs/hybrid_results.md` |
| Demo y trazas reproducibles | `app/app.py`, `results/visual_demo.json`, `tools/export_visual_demo.py` |

## Setup (Windows, PowerShell)

Requisitos: Python 3.13 y Git.

```powershell
git clone https://github.com/Sin-equipo/qap10-quantum-gates.git
cd qap10-quantum-gates
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Si PowerShell bloquea la activación: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

Verificar: `python -c "import qiskit; print(qiskit.__version__)"` debe imprimir `2.6.1`.

## Reproducir los resultados

Con el entorno activado, desde la raíz del repo. Todo usa semillas fijas.

| Paso | Comando | Tiempo | Salida |
|---|---|---|---|
| 0. Pruebas de costos, circuitos, trazas y app | `python -m pytest tests` | ~1 min con navegador | Controles 24/32/340 y verificaciones de factibilidad; navegador y Node requieren los recursos de desarrollo indicados abajo |
| 1. (Opcional) Re-extraer F y D del MPS | `python tools\extract_qap10.py` | ~1 s | `data/qap10_matrices.json` |
| 2. N=4: clásico exacto + un QAOA | `python run_experiment.py --n 4 --qaoa` | ~15 s | `results/first_attempt_n4.json` |
| 3. Barrido QAOA N=3/4 (140 corridas) | `python qaoa_sweep.py` | ~20 min | `results/qaoa_sweep.csv`, `qaoa_sweep_summary.json` |
| 4. Gráfica QAOA N=4 | `python tools\plot_qaoa.py` | ~3 s | `results/qaoa_n4.png` |
| 5. N=10: híbrido LNS + QAOA vs. controles | `python hybrid_experiment.py` | ~8 min | `results/hybrid_n10.json`, `hybrid_n10_summary.csv` |
| 6. Gráficas N=10 | `python tools\plot_hybrid.py` | ~5 s | `results/hybrid_convergence.png`, `hybrid_final.png`, `terminal_map.png` |
| 7. Corroboración N=1…10 (exacto, QAOA, híbrido) | `python scaling_study.py` | ~12 min | `results/scaling.csv`, `scaling.json` |
| 8. Gráfica de escalamiento | `python tools\plot_scaling.py` | ~3 s | `results/scaling.png` |
| 9. Trazas para la demo (corridas registradas paso a paso, verificadas) | `python tools\export_visual_demo.py` | ~8 min | `results/visual_demo.json` |
| 10. Final N=10…14: exacto, QAOA híbrido y controles con memoria | `python scaling14_study.py` | Depende del equipo; reanudable | `results/scaling14.json`, `scaling14_jobs/` |
| 11. Informe y gráfica final N=10…14 | `python tools/report_scaling14.py` | ~3 s | `docs/scaling14_results.md`, `results/scaling14.png` |

Los pasos 3, 5, 7, 9 y 10 ya tienen sus resultados en `results/`. Para revisar no hace falta volver a correrlos: los pasos 4, 6 y 8 regeneran las gráficas desde esos archivos. Versión rápida del paso 5: `python hybrid_experiment.py --seeds 2 --iterations 40`.

Las corridas nuevas registran `best_tracking="including_kicks"`: se considera también la asignación visitada después de una patada. Los artefactos históricos se conservan sin reescribir; se verificó que esta corrección no cambia los costos finales de las trazas guardadas de la demo ni del estudio principal N=10. Para reproducir estrictamente la implementación de los resultados históricos, la revisión de referencia es `2788df1`; las correcciones posteriores deben identificarse al generar nuevas corridas.

Análisis y tablas: [`docs/qaoa_results.md`](docs/qaoa_results.md) (N=3/4), [`docs/hybrid_results.md`](docs/hybrid_results.md) (N=10) y [`docs/scaling_results.md`](docs/scaling_results.md) (N=1…10). Formato de las trazas de la demo: [`docs/visual_demo_schema.md`](docs/visual_demo_schema.md).

## Qué hace cada parte

- **Datos** (`tools/extract_qap10.py`): recupera F y D de las variables linealizadas del MPS de MIPLIB y verifica que cada coeficiente se separa como F·D. D resulta ser una cuadrícula de 3×4 con distancia Manhattan ×2.
- **Clásico** (`src/qap/classical.py`): enumeración exacta. Para N=10 recorre las 10! permutaciones por bloques de numpy en ~2.5 s y obtiene 340.
- **QAOA** (`src/qap/qaoa.py`): QUBO → Ising normalizado, circuito con Qiskit, entrenamiento en Aer y muestreo con `SamplerV2`. Dos mezcladores: X estándar con penalización, o intercambio, que conserva las permutaciones y es siempre factible. Limitado a 16 qubits.
- **Híbrido N=10** (`src/qap/hybrid.py`): LNS. En cada iteración libera K=3 vuelos y QAOA (9 qubits) reparte sus 3 puertas teniendo en cuenta a los 7 vuelos fijos (término lineal). Se compara con el mismo LNS usando un subsolver exacto o uno aleatorio, y con SciPy FAQ.

Simulación ideal sin ruido. Qiskit construye y simula los circuitos; la optimización de ángulos (COBYLA), la elección de vecindarios y la aceptación de movimientos son clásicas. El mezclador de intercambio no necesita reparación. Si se usa el mezclador X, la reparación húngara se reporta aparte.

## Estructura

```
data/               MPS oficial comprimido y matrices F, D recuperadas
src/qap/            instance.py, classical.py, exact_bound.py, qaoa.py, hybrid.py, trace.py
app/                demo visual (Streamlit): streamlit run app/app.py
tests/              pytest
tools/              extracción del MPS, gráficas, export de trazas (export_visual_demo.py) y adaptador de la app
run_experiment.py   N=3/4: clásico + un QAOA
qaoa_sweep.py       barrido QAOA N=3/4
hybrid_experiment.py N=10: LNS + QAOA vs. controles
scaling_study.py    corroboración histórica N=1…10
scaling14_study.py  ampliación N=10…14, referencias exactas, comparación y memoria
results/            CSV/JSON/PNG de los experimentos
docs/               análisis y límites
```

## Convenciones

- Costo: cada par de vuelos (i, k) con i < k se cuenta una sola vez. Los óptimos de control son 24 (N=3), 32 (N=4), 340 (N=10).
- Reportar por separado la energía penalizada del QUBO y el costo de una asignación factible.
- Fijar semillas y registrar parámetros (λ, optimizador, shots) en cada experimento.
- Los datos de qap10 son un benchmark matemático; el contexto de aeropuerto es una adaptación con supuestos.

## Demo visual para PC

Con el entorno activado, abre la pantalla de dos terminales:

```powershell
streamlit run app/app.py
```

La app reproduce corridas reales guardadas para N=1…10. La búsqueda conserva sus relojes medidos; después se puede comparar la asignación inicial con el resultado, ambos algoritmos o el óptimo global. El recorrido destaca una conexión y muestra flujo × distancia, con opciones para tres conexiones secuenciales o todos los flujos. La suma recorrida por todas las figuras coincide con el costo QAP. Cada recorrido se detiene en la última llegada; pausa y finalización detienen también el redibujado continuo. La velocidad se ajusta por separado para el cálculo y la animación.

Se conservan el intercambio de vuelos mediante arrastre o dos clics, los shots reales de QAOA y el panel de evidencia. Las figuras representan unidades de flujo; sus emociones y segundos de movimiento son ilustrativos. Mostrar menos conexiones no cambia las matrices ni el costo del plan completo. Las tres conexiones clave se ordenan por cambio absoluto del aporte, incluyendo empeoramientos. Dos asignaciones iguales producen recorridos idénticos: la app no inventa una diferencia entre algoritmos.

`results/visual_demo.json` contiene las trazas completas. Para regenerarlas: `python tools/export_visual_demo.py` (varios minutos). Si falta una traza, su reproducción se desactiva; el resultado agregado sigue disponible. La prueba real opcional para N=3/4 ejecuta Qiskit Aer y conserva el resultado en la sesión, sin modificar el dataset guardado.

Pruebas del recorrido: `python -m pytest tests/test_walk_math.py`. Las pruebas de navegador en `tests/test_visual_browser.py` requieren Playwright y Chromium (`pip install playwright` y `python -m playwright install chromium`); arrancan y detienen su propio servidor local. Node se usa solo en las pruebas independientes de las fórmulas JavaScript, no para ejecutar la app.

## Dependencias

Versiones fijadas en `requirements.txt` (Qiskit 2.6.1 y qiskit-aer 0.18.0). El prototipo usa Qiskit para construir y simular el circuito; la optimización de parámetros y la reparación de muestras se ejecutan clásicamente.

## Fuentes y recursos

- [MIPLIB: instancia QAP10](https://miplib.zib.de/instance_details_qap10.html): archivo original y referencia de la instancia.
- [IBM Quantum: QAOA](https://quantum.cloud.ibm.com/docs/en/tutorials/quantum-approximate-optimization-algorithm): marco del método variacional híbrido.
- [Qiskit Aer: simuladores](https://qiskit.github.io/qiskit-aer/tutorials/1_aersimulator.html): simulación de circuitos y muestreo.
- [Hadfield et al.: Quantum Alternating Operator Ansatz](https://arxiv.org/abs/1709.03489): contexto de mezcladores que conservan restricciones.

Se utilizaron Python, NumPy, SciPy, Qiskit, Qiskit Aer, Matplotlib y Streamlit; las versiones están declaradas en `requirements.txt`. El equipo utilizó asistencia de Codex y Claude durante el desarrollo y la revisión, y es responsable de comprobar y explicar el código y los resultados presentados.
