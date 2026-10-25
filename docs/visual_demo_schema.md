# `results/visual_demo.json` · contrato de datos para la app (esquema 1.0)

Lo genera `python tools/export_visual_demo.py` (≈8 min; `--quick` ≈1 min para probar).
El archivo se verifica antes de escribirse; si una comprobación falla, no se escribe.
JSON compacto (~3 MB). Índices desde 0: vuelo `i` es la fila `i`, puerta `g` es la columna `g`.

Una **asignación** es una lista `a` de largo N donde `a[i]` = puerta del vuelo `i`.
Su costo es `sum(F[i][k] * D[a[i]][a[k]] for i < k)`, igual a `QAPInstance.cost` del repo.

## Raíz

| Campo | Contenido |
|---|---|
| `schema_version` | `"1.0"` |
| `generated_at`, `export`, `export_seconds` | fecha UTC; `"full"` o `"quick"`; duración |
| `versions` | python, qiskit, qiskit-aer, numpy, scipy |
| `instance` | `flows` y `distances` (10×10), `total_flow_n10` (=114 personas), `cost_convention`, `interpretation` (texto honesto), `layout` |
| `instance.layout` | `columns: 4`, `rows: 3`, `coords: [{gate, row, col}]`, `distance_rule`. Puerta g → fila g//4, columna g%4. Verificado: reproduce D exacto |
| `exact` | lista N=1…10: `optimum`, `optimal_assignments` (todas), `optimal_count`, `assignments` (N!), `p_optimal_random`, `mean_random_cost`, `seconds`, `trivial` (N=1, 2) |
| `studies` | resultados agregados con su configuración: `qaoa_recorded` (resumen por N, mezclador y p calculado desde las mismas `qaoa_runs`: P(óptimo) y válidas por semilla, medianas, azar, semillas que arrancaron en el óptimo), `qaoa_sweep` (barrido de 140 corridas), `hybrid_n10` (5 semillas, 150 iter.), `scaling` (3 semillas, 60 iter.). Las cifras de mediana salen de aquí, nunca de una corrida animada |
| `defaults` | vista inicial: `n: 10`, `left: "lns_n10_exact_s0"`, `right: "lns_n10_qaoa_s0"`; `qaoa_view`: N=4, `depth: 3`, `seed: 3` (el intercambio queda en la mediana de sus 5 semillas y X en la zona central; el export lo verifica) |
| `lns_reused` | `true` si las corridas LNS se reutilizaron de una exportación anterior (`--reuse-lns`) |
| `notes` | aclaraciones listas para mostrar en el panel de evidencia |
| `checks` | lista de verificaciones superadas |
| `lns_runs`, `qaoa_runs` | corridas registradas (abajo) |

Subinstancia N = primeras N filas y columnas de F y D (la geometría de las primeras N puertas).

## Ampliación final: `results/scaling14.json`

La app conserva este contrato histórico y carga adicionalmente `results/scaling14.json` cuando su campo `complete` es `true`.
Lo genera `python scaling14_study.py`. Las referencias y corridas nuevas de N=10…14 sustituyen las trazas históricas de esos tamaños en la vista principal; N=1…9 y QAOA directo N=3/4 mantienen sus datos anteriores. El estudio histórico N=10 con 150 iteraciones conserva su tabla propia.

- `instance`: matrices 14×14; QAP10 original ocupa el bloque principal 10×10. N=11…14 son ampliaciones sintéticas anidadas, con semilla de datos 20261025 y la misma cuadrícula de cuatro columnas.
- `references`: por tamaño, estado de optimalidad, costo, cota inferior final, asignación, número de óptimos, nodos y tiempos del exacto Gilmore–Lawler. Nunca son entradas ni puntos de partida del híbrido.
- `rows`, `summary`: óptimos, gaps por instancia, medianas, mejores costos, aciertos, factibilidad, tiempo, RSS y configuración.
- `lns_runs`: N=10…14 × tres subsolvers × cinco semillas, con el mismo formato de eventos anterior. Cada evento QAOA añade `training_simulator` y `subspace_verification_max_probability_error`.
- `measurement`, `environment`, `solver_source_sha256`: protocolo de memoria/tiempo, controles de hilos, versiones y hash de fuentes.
- `results/scaling14_jobs/`: los 106 jobs individuales (cinco referencias exactas, enumeración N=10 y cien corridas de cuatro métodos), con especificación y mediciones sin agregar.

El entrenamiento nuevo simula exactamente las seis permutaciones factibles de cada subproblema de K=3. Después, **cada llamada** verifica la distribución con el circuito completo de nueve qubits en Aer (error máximo permitido 1e−8) y obtiene sus 512 shots con SamplerV2. La animación reproduce eventos medidos, no inventa optimización mientras caminan pasajeros. Esta aceleración clásica de la simulación y sus límites se explican en [`scaling14_results.md`](scaling14_results.md).

`app/demo_data.py` normaliza ambos archivos y expone un catálogo de N=1…14 con `reference_method`, `synthetic` y `study_seeds` por instancia. La UI identifica la ampliación sintética y la referencia por ramificación y poda; permite seleccionar las cinco semillas nuevas.

## `lns_runs[]` · N=4…10 × {`exact`, `qaoa`, `random`}, semilla 0

`id` (`lns_n{N}_{subsolver}_s0`), `n`, `subsolver`, `seed`, `config` (k=3, iterations=60, reps=2, maxiter=60, shots=512, stall_limit=12, kick=4), `start_assignment`, `start_cost`, `final_assignment`, `final_cost` (= mejor encontrado), `kicks`, `seconds` (cálculo real), `qaoa_calls`, `qaoa_subproblem_hit_rate`, `events`.

**Mismo N y semilla ⇒ mismo `start_assignment` y misma secuencia de `flights`** en los tres subsolvers (verificado). Duelo justo.

`events[]`, uno por iteración (la iteración 0 es `start_*`):

| Campo | Significado |
|---|---|
| `iteration`, `seconds` | número (1…) y segundos de cálculo acumulados |
| `flights`, `gates` | los K vuelos liberados y las K puertas que ocupaban |
| `proposal` | permutación propuesta por el subsolver: el vuelo `flights[a]` va a `gates[proposal[a]]` |
| `candidate`, `candidate_cost` | asignación completa propuesta |
| `outcome`, `accepted` | `improve` / `equal` / `reject`. El subsolver exacto nunca rechaza |
| `assignment_after_move`, `cost_after_move` | estado tras aceptar o rechazar |
| `kick` | `null` o `{flights: [...]}`: vuelos barajados por la patada |
| `assignment`, `cost` | estado al **final** de la iteración (después de la patada) |
| `best_assignment`, `best_cost` | mejor encontrado hasta ahora (nunca sube) |
| `qaoa` | solo LNS+QAOA: `{seed, qubits: 9, p_optimal, subproblem_optimum_found, train_seconds, sample_seconds}` |

Para animar: tomar `assignment_after_move` como "movimiento" y, si `kick` no es `null`, un segundo paso visual hasta `assignment`.

## `qaoa_runs[]` · N=3, 4 × {X p=2, X p=3, intercambio p=2, intercambio p=3} × semillas 0–4

Para comparar mezcladores usar la misma `reps` en ambos y declarar las semillas utilizadas. "Mejor costo entre los shots válidos" no es una métrica de comparación: con 2048 shots casi cualquier muestreo incluye un óptimo (el mezclador X lo alcanza en las cinco semillas con P(óptimo) de 0.2–1.3 %). Comparar `p_optimal` y `p_feasible`, y acompañarlos del tiempo. Las tablas muestran mediana y rango para describir la variación entre semillas.

`id` (`qaoa_n{N}_{mixer}_p{p}_s{seed}`), `n`, `mixer` (`x` | `perm`), `reps`, `seed`, `config` (maxiter=100, shots=2048, alpha=1), `qubits`, `penalty`, `start_assignment`/`start_cost` (solo intercambio: estado inicial del circuito), `optimum`, `p_feasible`, `p_optimal`, `p_optimal_random_permutation`, `gain_vs_random_permutation`, `raw_feasible_fraction`, `raw_best_assignment`, `raw_best_cost`, `train_seconds`, `sample_seconds`, `objective_history` (energía penalizada por evaluación del optimizador: **no son asignaciones**), `resources` (solo semilla 0: qubits, profundidad, compuertas de 2 qubits transpiladas).

Ojo: si `start_cost == optimum` (pasa en N=3), el circuito empezó en el óptimo; esa corrida no prueba nada sobre QAOA.

`samples`:
- `unique[]`: `{bitstring, count, matrix (N×N, matrix[i][g]=1 si el vuelo i quedó en la puerta g), valid, assignment, cost, qubo_energy, conflicts}`. Las inválidas tienen `assignment: null` y `cost: null`. `qubo_energy` es la energía penalizada, otra magnitud. `conflicts` = `{flights_without_gate, flights_with_several_gates, gates_without_flight, gates_with_several_flights}`.
- `order[]`: los 2048 shots en orden de lectura, como índices en `unique`.

## Corridas en vivo ("prueba real")

```python
from src.qap import trace
run = trace.qaoa_run(4, "perm", 3, seed=7)            # ~15 s; mismo formato que qaoa_runs[i]
run = trace.qaoa_run(3, "x", 2, seed=7)               # ~1 s
run = trace.lns_run(6, "qaoa", seed=7, iterations=20) # ~10 s; mismo formato que lns_runs[i]
```

Si falta una traza, mostrar solo el resultado agregado de `studies` y desactivar la reproducción. No hay que interpolar asignaciones.
