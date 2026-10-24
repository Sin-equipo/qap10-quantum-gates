# QAP10 · Track A: puertas de embarque

Reto NTT DATA del Qiskit Fall Fest 2026. Modela diez vuelos de conexión y diez puertas con la instancia matemática QAP10. Compara un baseline clásico exacto con QAOA en Qiskit para N=3/4 y con un híbrido LNS + QAOA para la instancia completa N=10.

**El aeropuerto es una interpretación del benchmark.** Los flujos y distancias de QAP10 no son datos medidos de vuelos ni de puertas reales; no deben presentarse como pasajeros, metros ni ahorros operativos reales.

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
| 0. Tests (24, 32, 340, QUBO, mezclador, LNS) | `python -m pytest tests` | ~10 s | 19 tests en verde |
| 1. (Opcional) Re-extraer F y D del MPS | `python tools\extract_qap10.py` | ~1 s | `data/qap10_matrices.json` |
| 2. N=4: clásico exacto + un QAOA | `python run_experiment.py --n 4 --qaoa` | ~15 s | `results/first_attempt_n4.json` |
| 3. Barrido QAOA N=3/4 (140 corridas) | `python qaoa_sweep.py` | ~20 min | `results/qaoa_sweep.csv`, `qaoa_sweep_summary.json` |
| 4. Gráfica QAOA N=4 | `python tools\plot_qaoa.py` | ~3 s | `results/qaoa_n4.png` |
| 5. N=10: híbrido LNS + QAOA vs. controles | `python hybrid_experiment.py` | ~8 min | `results/hybrid_n10.json`, `hybrid_n10_summary.csv` |
| 6. Gráficas N=10 | `python tools\plot_hybrid.py` | ~5 s | `results/hybrid_convergence.png`, `hybrid_final.png`, `terminal_map.png` |
| 7. Corroboración N=1…10 (exacto, QAOA, híbrido) | `python scaling_study.py` | ~12 min | `results/scaling.csv`, `scaling.json` |
| 8. Gráfica de escalamiento | `python tools\plot_scaling.py` | ~3 s | `results/scaling.png` |

Los pasos 3, 5 y 7 ya tienen sus resultados en `results/`. Para revisar no hace falta volver a correrlos: los pasos 4, 6 y 8 regeneran las gráficas desde esos archivos. Versión rápida del paso 5: `python hybrid_experiment.py --seeds 2 --iterations 40`.

Análisis y tablas: [`docs/qaoa_results.md`](docs/qaoa_results.md) (N=3/4), [`docs/hybrid_results.md`](docs/hybrid_results.md) (N=10) y [`docs/scaling_results.md`](docs/scaling_results.md) (N=1…10).

## Qué hace cada parte

- **Datos** (`tools/extract_qap10.py`): recupera F y D de las variables linealizadas del MPS de MIPLIB y verifica que cada coeficiente se separa como F·D. D resulta ser una cuadrícula de 3×4 con distancia Manhattan ×2.
- **Clásico** (`src/qap/classical.py`): enumeración exacta. Para N=10 recorre las 10! permutaciones por bloques de numpy en ~3 s y obtiene 340.
- **QAOA** (`src/qap/qaoa.py`): QUBO → Ising normalizado, circuito con Qiskit, entrenamiento en Aer y muestreo con `SamplerV2`. Dos mezcladores: X estándar con penalización, o intercambio, que conserva las permutaciones y es siempre factible. Limitado a 16 qubits.
- **Híbrido N=10** (`src/qap/hybrid.py`): LNS. En cada iteración libera K=3 vuelos y QAOA (9 qubits) reparte sus 3 puertas teniendo en cuenta a los 7 vuelos fijos (término lineal). Se compara con el mismo LNS usando un subsolver exacto o uno aleatorio, y con SciPy FAQ.

Simulación ideal sin ruido. Qiskit construye y simula los circuitos; la optimización de ángulos (COBYLA), la elección de vecindarios y la aceptación de movimientos son clásicas. El mezclador de intercambio no necesita reparación. Si se usa el mezclador X, la reparación húngara se reporta aparte.

## Flujo de trabajo en equipo

```powershell
git pull
git checkout -b <tu-nombre>/<tarea>
# ... cambios ...
git add .
git commit -m "mensaje corto"
git push -u origin <tu-nombre>/<tarea>
```

Abre un Pull Request hacia `main`. Haz `git pull` antes de empezar cada bloque.

## Estructura

```
data/               MPS oficial comprimido y matrices F, D recuperadas
src/qap/            instance.py, classical.py, qaoa.py, hybrid.py
tests/              pytest
tools/              extracción del MPS y gráficas
run_experiment.py   N=3/4: clásico + un QAOA
qaoa_sweep.py       barrido QAOA N=3/4
hybrid_experiment.py N=10: LNS + QAOA vs. controles
results/            CSV/JSON/PNG de los experimentos
docs/               análisis y límites
```

## Convenciones

- Costo: cada par de vuelos (i, k) con i < k se cuenta una sola vez. Los óptimos de control son 24 (N=3), 32 (N=4), 340 (N=10).
- Reportar por separado la energía penalizada del QUBO y el costo de una asignación factible.
- Fijar semillas y registrar parámetros (λ, optimizador, shots) en cada experimento.
- Los datos de qap10 son un benchmark matemático; el contexto de aeropuerto es una adaptación con supuestos.

## Dependencias

Versiones fijadas en `requirements.txt` (Qiskit 2.6.1 y qiskit-aer 0.18.0). El prototipo usa Qiskit para construir y simular el circuito; la optimización de parámetros y la reparación de muestras se ejecutan clásicamente.
