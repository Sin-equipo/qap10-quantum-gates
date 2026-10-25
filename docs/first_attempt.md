# Planteamiento y primera solución

## Problema en Track A

Interpretamos cada elemento del QAP10 como un vuelo de conexión y cada ubicación como una puerta de embarque. Si vuelos `i` y `k` comparten flujo, asignarlos a puertas alejadas aumenta la suma flujo-distancia. Se busca una permutación que minimice ese costo.

La interpretación industrial es ilustrativa: MIPLIB QAP10 es un benchmark matemático, no un conjunto de mediciones de aeropuerto. No se atribuyen al prototipo unidades reales de pasajeros o metros ni reducciones operativas.

## Solución implementada

1. Se descargó `qap10.mps.gz` de MIPLIB.
2. `tools/extract_qap10.py` recupera los productos flujo-distancia de las variables auxiliares del MPS y separa las matrices `F` y `D`. Verifica que cada coeficiente reconstruido coincida con `F[i,k] * D[j,l]`.
3. `src/qap/classical.py` enumera todas las permutaciones para obtener el baseline exacto.
4. `src/qap/qaoa.py` construye el QUBO con penalizaciones de asignación uno a uno, convierte el Hamiltoniano a términos `Z` y `ZZ`, y optimiza un circuito QAOA de profundidad 1 con un statevector de Qiskit.
5. Las muestras se evalúan primero sin alterar. Una asignación húngara las repara a una permutación factible; su resultado se etiqueta como híbrido y no como salida QAOA factible.

## Resultado guardado

Para `N=4`, el baseline exacto evalúa 24 permutaciones y alcanza costo 32. En la corrida fijada con semilla 7, QAOA usa 16 qubits, 25 iteraciones y 2,048 muestras: no produjo ninguna muestra factible sin reparar. La reparación clásica obtuvo la misma asignación óptima y costo 32.

La comparación sirve para validar el flujo completo, no para afirmar ventaja cuántica: el baseline ya resuelve `N=4` exactamente y la muestra QAOA requirió reparación clásica. El tiempo medido incluye la optimización variacional local y la simulación ideal en esta máquina; no es una comparación de hardware equivalente.

## Qué vino después

Este documento registra el primer intento. Los pasos que dejaba abiertos ya están resueltos:

- Penalización y factibilidad sin reparación en cinco semillas, más el mezclador de intercambio: [`qaoa_results.md`](qaoa_results.md).
- Búsqueda local clásica e híbrido LNS + QAOA para `N=10`, con costo y tiempo frente a 340: [`hybrid_results.md`](hybrid_results.md).
- Escalamiento N=1…10 y límites de cada método: [`scaling_results.md`](scaling_results.md).
- Visualización de asignaciones y aportes flujo × distancia: la demo `app/app.py`.

La prueba `N>=14` de la final está documentada en [`scaling14_results.md`](scaling14_results.md), con vecindarios de tres vuelos, nueve qubits por llamada y referencia óptima certificada; no se simula un statevector de `N²` qubits.
