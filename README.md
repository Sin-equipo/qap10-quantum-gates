# qap10-quantum-gates

Qiskit Fall Fest 2026 · Hackathon · Reto NTT DATA (QAP10, Track A: puertas de embarque).
Asignación cuadrática (10 vuelos → 10 puertas): baseline clásico exacto vs. enfoque cuántico/híbrido con Qiskit.

## Setup (Windows, PowerShell)

Requisitos: Python 3.13, Git.

```powershell
git clone https://github.com/Sin-equipo/qap10-quantum-gates.git
cd qap10-quantum-gates
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Si PowerShell bloquea la activación:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Verificar:

```powershell
python -c "import qiskit, qiskit_aer, qiskit_optimization; print(qiskit.__version__)"
```

Debe imprimir `2.6.1`.

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
data/        qap10.mps.gz y matrices F, D recuperadas
src/qap/     código: datos, costo, clásico, QUBO, Qiskit, híbrido
notebooks/   experimentos
app/         dashboard Streamlit
results/     salidas de experimentos (csv/json)
docs/        notas y descripción
slides/      PPT
```

## Convenciones

- Costo: cada par (i, k) con i < k se cuenta una sola vez. Validar con óptimos 24 (N=3), 32 (N=4), 340 (N=10).
- Reportar por separado la energía penalizada del QUBO y el costo de una asignación factible.
- Fijar semillas y registrar parámetros (λ, optimizador, shots) en cada experimento.
- Los datos de qap10 son un benchmark matemático; el contexto de aeropuerto es una adaptación con supuestos.

## Dependencias

Versiones fijadas en `requirements.txt` (Qiskit 2.6.1, qiskit-aer 0.18.0, qiskit-optimization 0.7.0).
