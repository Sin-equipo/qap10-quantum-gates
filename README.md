# QAP10 · Track A: puertas de embarque

Prototipo inicial para el reto NTT DATA del Qiskit Fall Fest 2026. Modela diez vuelos y diez puertas con la instancia matemática QAP10 y compara un baseline clásico exacto con una prueba QAOA simulada en Qiskit.

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

## Primera comparación

```powershell
.venv\Scripts\python.exe run_experiment.py --n 4
.venv\Scripts\python.exe run_experiment.py --n 4 --qaoa --maxiter 25 --shots 2048
```

El segundo comando ejecuta un QAOA de profundidad 1 con un statevector ideal de 16 qubits y repara cada muestra mediante asignación húngara. El JSON se escribe en `results/first_attempt_n4.json`. La reparación es clásica y se reporta explícitamente.

La instancia también puede extraerse de nuevo desde el MPS oficial:

```powershell
python tools\extract_qap10.py
```

## Qué resuelve esta primera versión

- Recupera las matrices de flujo y distancia del MPS de MIPLIB y verifica su factorización.
- Ejecuta enumeración exacta sobre las 24 permutaciones de `N=4`.
- Construye la penalización QUBO de asignación uno a uno y un circuito QAOA con Qiskit.
- Registra por separado el costo de asignación, la energía QUBO, las muestras factibles sin reparar y el resultado tras la reparación clásica.

La instancia `N=4` reproduce el óptimo de control 32. El experimento registrado encuentra costo 32 después de reparar muestras, pero tuvo cero muestras QAOA factibles sin reparar. Por eso aún no hay evidencia de que QAOA mejore el baseline clásico.

El circuito de statevector está limitado a `N<=4` (16 qubits). `N=10` se puede recorrer clásicamente en memoria constante, pero este prototipo no pretende simular un statevector de 100 qubits.

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
data/        MPS oficial comprimido y matrices F, D recuperadas
src/qap/     modelo, baseline clásico y QAOA
tools/       extracción reproducible de matrices desde MPS
results/     JSON de la primera comparación
docs/        análisis del proyecto y límites
```

## Convenciones

- Costo: cada par de vuelos (i, k) con i < k se cuenta una sola vez. Los óptimos de control son 24 (N=3), 32 (N=4), 340 (N=10).
- Reportar por separado la energía penalizada del QUBO y el costo de una asignación factible.
- Fijar semillas y registrar parámetros (λ, optimizador, shots) en cada experimento.
- Los datos de qap10 son un benchmark matemático; el contexto de aeropuerto es una adaptación con supuestos.

## Dependencias

Versiones fijadas en `requirements.txt` (Qiskit 2.6.1 y qiskit-aer 0.18.0). El prototipo usa Qiskit para construir y simular el circuito; la optimización de parámetros y la reparación de muestras se ejecutan clásicamente.
