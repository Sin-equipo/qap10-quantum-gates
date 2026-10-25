"""Browser-side airport renderer. CCv2 keeps animation off the Python rerun loop."""

from hashlib import sha256

import streamlit as st

from walk_math import WALK_MODEL

HTML = r"""
<main id="lab" class="lab">
  <header class="masthead">
    <div class="brand"><span class="brand-icon">↗</span><div><h1>Mission Connections<span class="brand-period">.</span></h1><p>Un aeropuerto. Millones de decisiones.</p></div></div>
    <div class="head-right"><span class="small-tag"><i></i> <span id="instance-kind">BENCHMARK QAP10</span></span><button id="evidence" class="quiet" aria-label="Abrir evidencia y metodología">Evidencia <span>↗</span></button></div>
  </header>
  <nav class="toolbar" aria-label="Controles del experimento">
    <div class="size-control"><span class="eyebrow">VUELOS / PUERTAS</span><div><strong id="n-label">10</strong><input id="size" aria-label="Número de vuelos y puertas" type="range" min="1" max="10" value="10"><button data-size="4" class="preset">N=4</button><button data-size="10" class="preset active">N=10</button><button data-size="14" class="preset" hidden>N=14</button></div></div>
    <span class="toolbar-rule"></span>
    <label class="experiment-label"><span class="eyebrow">EXPERIMENTO</span><select id="mode" aria-label="Comparación de algoritmos"><option value="lns">Clásico vs. híbrido QAOA</option><option value="mixers">QAOA: penalización vs. intercambio</option></select></label>
    <label class="seed-label"><span class="eyebrow">SEMILLA</span><select id="seed" aria-label="Semilla de la corrida"><option>0</option><option>1</option><option>2</option><option>3</option><option>4</option></select></label>
    <label class="seed-label depth-label"><span class="eyebrow">CAPAS (p)</span><select id="depth" aria-label="Profundidad p del circuito QAOA"><option>2</option><option selected>3</option></select></label>
    <button class="reference-pill" id="show-optimum" title="Mostrar la asignación exacta en la terminal izquierda"><span class="eyebrow">ÓPTIMO EXACTO ↗</span><strong id="reference">340</strong><small id="exact-time">2,6 s · 10! opciones</small></button>
  </nav>
  <section class="phase-line"><div class="phase-steps"><span id="step-search" class="phase-step selected"><b>1</b> Buscar asignación</span><span class="phase-dash"></span><span id="step-walk" class="phase-step"><b>2</b> Ver las conexiones</span></div><span id="phase-message" class="phase-message">Mismo inicio. Mismos vecindarios. Distinto subsolver.</span></section>
  <section id="walk-options" class="walk-options" aria-label="Explorar el efecto de las asignaciones" hidden>
    <label>Comparar <select id="walk-compare" aria-label="Asignaciones que recorren los pasajeros"><option value="impact">Antes → resultado QAOA</option><option value="algorithms">Los dos algoritmos</option><option value="optimum">Óptimo → resultado QAOA</option></select></label>
    <label>Mostrar <select id="walk-view" aria-label="Cantidad de conexiones visibles"><option value="group">Una conexión</option><option value="tour">Tres conexiones clave</option><option value="all">Todos los flujos</option></select></label>
    <label class="transfer-control">Conexión <select id="transfer" aria-label="Conexión de vuelos a inspeccionar"></select></label>
    <button id="prev-transfer" class="square" aria-label="Conexión anterior" title="Conexión anterior">‹</button><button id="next-transfer" class="square" aria-label="Siguiente conexión" title="Siguiente conexión">›</button>
    <span id="tour-label" class="tour-label"></span>
  </section>
  <section class="arena" aria-label="Comparación visual de dos aeropuertos">
    <article class="terminal terminal-left" data-side="0">
      <div class="terminal-head"><div><span class="eyebrow method-label" id="method-left">BÚSQUEDA CLÁSICA</span><h2 id="title-left">LNS + exacto</h2></div><span id="status-left" class="status">En espera</span></div>
      <div class="metrics"><div><small>Costo actual</small><strong id="cost-left">—</strong></div><div><small>Mejor encontrado</small><strong id="best-left">—</strong></div><div class="qmetric" id="popt-wrap-left" hidden><small>P(óptimo)</small><strong id="popt-left">—</strong></div><div class="qmetric" id="valid-wrap-left" hidden><small>Shots válidos</small><strong id="valid-left">—</strong></div><div class="time-metric"><small>Cálculo medido</small><strong id="time-left">—</strong></div><span id="gap-left" class="gap">—</span></div>
      <div class="map" id="map-left"><canvas id="canvas-left" aria-label="Pasajeros y pasillos de la terminal izquierda"></canvas><svg id="gates-left" viewBox="0 0 600 330" role="group" aria-label="Puertas de la terminal izquierda, selecciona dos para intercambiar vuelos"></svg><div class="speech" id="speech-left" hidden></div></div>
      <div id="walk-readout-left" class="walk-readout" hidden><div><span id="trip-left">Esta conexión</span><strong id="walked-left">0 / 0 unidades</strong></div><div class="arrival-track"><span id="arrival-fill-left"></span></div><small id="trip-equation-left">flujo × distancia</small></div>
      <div class="terminal-foot"><span id="detail-left">60 iteraciones · K=3</span><span id="arrivals-left">↔ Arrastra o selecciona dos puertas</span></div>
    </article>
    <article class="terminal terminal-right" data-side="1">
      <div class="terminal-head"><div><span class="eyebrow method-label" id="method-right">BÚSQUEDA HÍBRIDA</span><h2 id="title-right">LNS + QAOA</h2></div><span id="status-right" class="status">En espera</span></div>
      <div class="metrics"><div><small>Costo actual</small><strong id="cost-right">—</strong></div><div><small>Mejor encontrado</small><strong id="best-right">—</strong></div><div class="qmetric" id="popt-wrap-right" hidden><small>P(óptimo)</small><strong id="popt-right">—</strong></div><div class="qmetric" id="valid-wrap-right" hidden><small>Shots válidos</small><strong id="valid-right">—</strong></div><div class="time-metric"><small>Cálculo medido</small><strong id="time-right">—</strong></div><span id="gap-right" class="gap">—</span></div>
      <div class="map" id="map-right"><canvas id="canvas-right" aria-label="Pasajeros y pasillos de la terminal derecha"></canvas><svg id="gates-right" viewBox="0 0 600 330" role="group" aria-label="Puertas de la terminal derecha, selecciona dos para intercambiar vuelos"></svg><div class="speech" id="speech-right" hidden></div></div>
      <div id="walk-readout-right" class="walk-readout" hidden><div><span id="trip-right">Esta conexión</span><strong id="walked-right">0 / 0 unidades</strong></div><div class="arrival-track"><span id="arrival-fill-right"></span></div><small id="trip-equation-right">flujo × distancia</small></div>
      <div class="terminal-foot"><span id="detail-right">60 iteraciones · 9 qubits por llamada</span><span id="arrivals-right">↔ Arrastra o selecciona dos puertas</span></div>
    </article>
  </section>
  <section class="insight-strip"><span class="insight-icon">↳</span><p id="insight" role="status" aria-live="polite">¿Un buen subsolver garantiza una buena asignación global? Reproduce el duelo y observa.</p><button id="restore" class="text-button" hidden>Restaurar duelo ↺</button></section>
  <section class="bottom-row">
    <div class="player"><div class="player-buttons"><button id="play" class="primary"><span>▶</span> Reproducir duelo</button><button id="restart" class="square" title="Reiniciar" aria-label="Reiniciar reproducción">↺</button><button id="next" class="square" title="Avanzar un evento" aria-label="Avanzar un evento">↦</button><button id="walk" class="quiet small">Ver pasajeros ↗</button><button id="samples" class="quiet small" hidden>Ver muestras</button></div><div class="scrub"><span id="clock-label">0,0 s</span><input id="timeline" type="range" min="0" max="1000" value="0" aria-label="Línea de tiempo de la corrida"><span id="duration-label">—</span><select id="speed" aria-label="Velocidad de reproducción"><option value="1">1×</option><option value="5">5×</option><option value="10" selected>10×</option><option value="20">20×</option></select></div></div>
    <div class="chart-wrap"><div class="chart-heading"><span id="chart-title">Costo por iteración</span><span><i class="dot blue"></i> <span id="legend-left">Clásico</span> <i class="dot teal"></i> <span id="legend-right">QAOA</span></span></div><svg id="convergence" viewBox="0 0 520 64" role="img" aria-label="Evolución del costo en las corridas registradas"></svg></div>
  </section>
  <footer class="footer"><span>QAP10 · pesos de un benchmark, no pasajeros ni metros medidos en Lima.</span><span id="provenance">Aer ideal · reproducción de corridas registradas · sin hardware cuántico</span><button id="live" class="text-button" hidden>Ejecutar Qiskit ahora ↗</button></footer>
  <div id="toast" class="toast" role="status" hidden></div>
  <aside id="drawer" class="drawer" aria-label="Evidencia experimental" hidden><div class="drawer-top"><div><span class="eyebrow">DETALLES DEL EXPERIMENTO</span><h2>Los datos detrás del dibujo</h2></div><button id="close-evidence" class="square" aria-label="Cerrar evidencia">×</button></div><div id="evidence-body" class="evidence-body"></div></aside>
</main>
"""

CSS = r"""
:host {font-family: 'Segoe UI',system-ui,sans-serif; color:#183348; color-scheme:light;}
* {box-sizing:border-box} [hidden]{display:none!important} button,input,select{font:inherit}button{cursor:pointer}button:disabled{opacity:.45;cursor:not-allowed}button,select,input{outline-offset:3px}button:focus-visible,select:focus-visible,input:focus-visible,[role=button]:focus-visible{outline:3px solid #d48a19}
.lab{position:relative;height:calc(100dvh - 86px);min-height:585px;max-height:1120px;display:flex;flex-direction:column;gap:7px;background:#f5f4ef;overflow:hidden}
.masthead{height:49px;display:flex;align-items:center;justify-content:space-between;flex-shrink:0}.brand{display:flex;gap:12px;align-items:center}.brand-icon{background:#173d4b;border-radius:12px;width:42px;height:42px;display:grid;place-items:center;color:#ecf3dd;font-size:32px;font-weight:400;transform:rotate(-7deg)}h1,h2,p{margin:0}h1{font-size:25px;letter-spacing:-1px;line-height:1.1;font-weight:750}.brand-period{color:#0c9381}.brand p{font-size:11px;color:#66766f;margin-top:3px;letter-spacing:.25px}.head-right{display:flex;gap:20px;align-items:center}.small-tag{font-size:10px;letter-spacing:1.6px;color:#61766e;font-weight:700;display:flex;gap:7px;align-items:center}.small-tag i{width:6px;height:6px;border-radius:50%;background:#148d79}.quiet,.square,.preset,.text-button{background:transparent;border:0;color:#335363}.quiet{padding:8px 10px;border:1px solid #d6ded5;border-radius:7px;font-weight:600;font-size:12px}.quiet:hover,.square:hover,.preset:hover{background:#e3eae1}.quiet span{margin-left:14px}.quiet.small{border:0;font-size:11px;padding:5px}.square{border:1px solid #d6ded5;border-radius:6px;width:30px;height:30px;font-size:20px;line-height:1}.text-button{font-size:11px;font-weight:650;white-space:nowrap;padding:0 5px}
.toolbar{display:flex;align-items:center;gap:22px;padding:10px 16px;background:#ebece4;border:1px solid #dde2d7;border-radius:10px;flex-shrink:0;min-height:66px}.eyebrow{font-size:9px;font-weight:750;letter-spacing:1.5px;color:#75817b;display:block;white-space:nowrap}.size-control{min-width:300px}.size-control>div{display:flex;align-items:center;gap:11px;margin-top:4px}.size-control strong{font-size:22px;min-width:26px;font-variant-numeric:tabular-nums;line-height:25px}.size-control input{width:120px;accent-color:#0a8175;height:5px}.preset{border:1px solid #ced6ca;border-radius:5px;padding:3px 7px;font-size:10px}.preset.active{background:#173d4b;color:#fff;border-color:#173d4b}.toolbar-rule{height:34px;border-left:1px solid #d3dacf}.experiment-label{flex:1;min-width:220px}select{border:0;background:transparent;color:#244d5b;font-weight:650;cursor:pointer;font-size:12px;max-width:100%}.experiment-label select{margin:6px 0 0 -4px;width:100%}.seed-label{width:58px}.seed-label select{margin-top:6px;min-width:42px}.reference-pill{padding-left:20px;border-left:1px solid #d3dacf;min-width:145px;display:grid;grid-template-columns:auto 1fr;gap:2px 8px}.reference-pill .eyebrow{grid-column:1/-1}.reference-pill strong{font-size:22px;line-height:25px;font-variant-numeric:tabular-nums}.reference-pill small{font-size:10px;color:#6c7d72;max-width:120px;line-height:13px;align-self:center}
.phase-line{display:flex;align-items:center;justify-content:space-between;min-height:21px;flex-shrink:0;gap:8px}.phase-steps{display:flex;align-items:center;gap:9px}.phase-step{font-size:11px;color:#89948b;white-space:nowrap}.phase-step b{font-size:9px;display:inline-grid;place-items:center;width:17px;height:17px;border:1px solid #ccd5c9;border-radius:50%;margin-right:5px}.phase-step.selected{color:#154f57;font-weight:700}.phase-step.selected b{background:#e2ece3;border-color:#4e8c7f}.phase-dash{width:23px;border-top:1px solid #c9d3c6}.phase-message{font-size:10px;color:#758175;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.arena{display:grid;grid-template-columns:1fr 1fr;gap:15px;min-height:260px;flex:1}.terminal{border:1px solid #d9dfd4;border-radius:11px;background:#fcfdf9;overflow:hidden;display:flex;flex-direction:column;min-height:0;box-shadow:0 2px 4px #223d1610}.terminal-head{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:11px 15px 8px;border-bottom:1px solid #edf0e8;min-height:56px}.method-label{font-size:8px;letter-spacing:1.3px;color:#628298}.terminal-right .method-label{color:#398c77}.terminal h2{font-size:18px;letter-spacing:-.55px;margin-top:2px}.status{font-size:9px;padding:4px 7px;border:1px solid #d7dfd2;border-radius:4px;white-space:nowrap;color:#6a7b6b;background:#f0f4e9}.status.working{background:#e5f0ef;color:#18746d;border-color:#bfdbd6}.status.bad{background:#fff0e8;color:#bc5739;border-color:#efcaba}.status.good{background:#e8f4e2;color:#427e44;border-color:#c9dfbc}.status.manual{background:#fdf3d8;color:#986b17;border-color:#e9d8ad}.metrics{display:flex;align-items:center;gap:22px;padding:7px 15px 4px;min-height:51px}.metrics small{font-size:9px;color:#849081;display:block;margin-bottom:1px}.metrics strong{font-size:21px;letter-spacing:-.6px;font-variant-numeric:tabular-nums;line-height:24px}.time-metric{margin-left:auto}.time-metric strong{font-size:17px;font-weight:650}.gap{font-size:10px;color:#a26534;background:#f6f0e3;border-radius:4px;padding:4px;align-self:center;min-width:40px;text-align:center}.gap.optimal{color:#3d7c4e;background:#e9f3e4}
.map{position:relative;flex:1;min-height:136px;overflow:hidden;touch-action:none}.map canvas,.map svg{position:absolute;inset:0;width:100%;height:100%}.map canvas{z-index:2;pointer-events:none}.map svg{z-index:3}.gate{cursor:grab;user-select:none}.gate:active{cursor:grabbing}.gate .building{fill:#fbfcf6;stroke:#bdcaba;stroke-width:1}.gate:hover .building{stroke:#127b73;stroke-width:2}.gate.chosen .building{stroke:#b37b19;stroke-width:3;fill:#fff3cc}.gate.released .building{stroke:#d49a31;stroke-width:2;fill:#fff9e8}.gate.conflict .building{stroke:#d27458;fill:#fff2ea;stroke-width:1.7}.gate text{pointer-events:none;dominant-baseline:middle}.gate .gate-number{font-size:8px;fill:#819080;letter-spacing:1px}.gate .flight{font-size:15px;fill:#294b5c;font-weight:700}.gate .empty{font-size:9px;fill:#b0654b}.gate .gate-marker{fill:#b6c8af}.gate .conflict-dot{fill:#db7453}.speech{position:absolute;z-index:5;top:4px;right:12px;max-width:230px;padding:9px 12px;border-radius:7px;background:#fffcf1;box-shadow:0 2px 8px #26412620;border:1px solid #e4d4ae;font-size:10px;line-height:1.5;pointer-events:none}.speech strong{display:block;font-size:11px}.terminal-foot{display:flex;justify-content:space-between;gap:5px;font-size:9px;color:#85907c;padding:6px 12px;border-top:1px solid #eff1e9;min-height:25px}.terminal-foot span:last-child{color:#628b7a;text-align:right}
.insight-strip{display:flex;align-items:center;gap:9px;min-height:28px;flex-shrink:0}.insight-icon{font-size:20px;color:#288878;padding-left:2px}.insight-strip p{font-size:11px;color:#536a65;flex:1;line-height:1.45}.bottom-row{display:grid;grid-template-columns:1fr 1fr;gap:24px;min-height:77px;flex-shrink:0}.player{display:flex;flex-direction:column;justify-content:space-between;padding-top:2px}.player-buttons{display:flex;align-items:center;gap:7px}.primary{background:#173e49;color:#fff;border:1px solid #173e49;border-radius:6px;font-size:11px;padding:8px 12px;font-weight:650;white-space:nowrap}.primary:hover{background:#22606a}.primary span{display:inline-block;width:15px;font-size:10px}.scrub{display:flex;align-items:center;gap:8px;min-height:30px}.scrub input{flex:1;accent-color:#1b8b7b;height:4px;min-width:30px}.scrub span{font-size:9px;color:#6b8072;white-space:nowrap;font-variant-numeric:tabular-nums}.scrub select{font-size:10px;background:#e7ece1;border-radius:4px;padding:3px 1px}.chart-wrap{border-left:1px solid #d7dfd0;padding-left:20px;min-width:0;display:flex;flex-direction:column}.chart-heading{font-size:9px;display:flex;justify-content:space-between;color:#6a8071;gap:4px}.chart-heading>span:first-child{font-weight:650}.chart-heading>span:last-child{white-space:nowrap;font-size:8px}.dot{display:inline-block;width:6px;height:6px;border-radius:2px;margin:0 2px 0 7px}.blue{background:#4d7fbb}.teal{background:#1b9380}#convergence{width:100%;height:62px;overflow:visible}.footer{display:flex;justify-content:space-between;gap:8px;align-items:center;min-height:16px;flex-shrink:0;border-top:1px solid #e0e5d8;padding-top:5px;color:#8a9685;font-size:8px}.footer>span:last-of-type{text-align:right}.footer .text-button{color:#0b8173;font-size:9px}.toast{position:absolute;z-index:10;bottom:110px;left:50%;transform:translateX(-50%);background:#173e49;color:white;padding:10px 18px;border-radius:7px;box-shadow:0 3px 12px #1233;font-size:12px;max-width:80%;text-align:center;pointer-events:none}.drawer{position:absolute;z-index:20;inset:0 0 0 auto;width:min(700px,85%);border:1px solid #d0dacc;border-radius:12px;background:#fcfdf8;box-shadow:-8px 0 40px #173e4925;display:flex;flex-direction:column}.drawer-top{padding:20px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #e4e9dd}.drawer h2{font-size:23px;margin-top:5px}.evidence-body{padding:18px 20px;overflow:auto;flex:1;font-size:12px;line-height:1.6}.evidence-body h3{font-size:15px;margin:18px 0 6px;color:#1b5c62}.evidence-body h3:first-child{margin-top:0}.evidence-body p{margin:6px 0}.evidence-body table{border-collapse:collapse;width:100%;font-size:10px;margin:12px 0}.evidence-body th{text-align:left;background:#eaf0e3;padding:6px}.evidence-body td{border-bottom:1px solid #e3e8dd;padding:5px}.evidence-body code{font-size:10px;color:#31766d}.evidence-body .source-card{background:#f0f3e9;padding:10px 12px;border:1px solid #e0e6d6;border-radius:7px;margin:8px 0}.evidence-body .key-number{font-size:27px;font-weight:700;color:#14796d}.evidence-body a{color:#127d73}.evidence-body ul{padding-left:18px}
@media(max-height:850px){.masthead{height:39px}.brand-icon{width:35px;height:35px;font-size:27px}h1{font-size:23px}.brand p{font-size:10px}.toolbar{min-height:54px;padding:6px 14px}.size-control>div{margin-top:2px}.toolbar .eyebrow{font-size:8px}.reference-pill strong{font-size:20px}.phase-line{min-height:18px}.terminal-head{min-height:47px;padding:8px 13px 6px}.terminal h2{font-size:17px}.metrics{min-height:45px;padding:5px 13px 3px}.metrics strong{font-size:20px}.time-metric strong{font-size:16px}.terminal-foot{min-height:22px;padding:4px 10px}.insight-strip{min-height:24px}.bottom-row{min-height:64px}.player-buttons{gap:5px}.primary{padding:6px 10px}.square{height:28px;width:28px}.scrub{min-height:25px}#convergence{height:51px}.footer{min-height:14px;padding-top:3px}}
@media(min-height:950px){.masthead{height:60px}h1{font-size:30px}.toolbar{min-height:75px}.terminal-head{min-height:65px}.terminal h2{font-size:23px}.metrics{min-height:64px}.metrics strong{font-size:27px}.time-metric strong{font-size:21px}.bottom-row{min-height:100px}#convergence{height:80px}.eyebrow{font-size:10px}.footer{font-size:9px}.insight-strip p{font-size:13px}}
@media(max-width:1150px){.toolbar{gap:12px;padding:9px 12px}.size-control{min-width:250px}.size-control input{width:85px}.reference-pill{min-width:120px;padding-left:12px}.small-tag{display:none}.metrics{gap:12px}.metrics strong{font-size:19px}.time-metric strong{font-size:15px}.phase-message{max-width:45%}.terminal-foot span{font-size:8px}.experiment-label{min-width:200px}.footer{font-size:7px}.player-buttons{gap:4px}.quiet.small{font-size:10px}}
@media(max-width:780px){.lab{min-height:620px}.toolbar{flex-wrap:wrap;gap:8px}.toolbar-rule,.reference-pill{display:none}.size-control{min-width:230px}.seed-label{width:40px}.arena{gap:7px}.terminal-head{padding:8px}.terminal h2{font-size:14px}.status{font-size:7px}.metrics{gap:7px;padding:6px}.metrics small{font-size:7px}.metrics strong{font-size:16px}.gap{display:none}.head-right{gap:4px}.time-metric strong{font-size:12px}.bottom-row{gap:10px}.quiet.small{display:none}.phase-message{display:none}.footer>span:last-of-type{display:none}.terminal-foot span:last-child{display:none}}
.depth-label{width:auto;min-width:58px}.qmetric strong{color:#14796d}.reference-pill{background:transparent;border-top:0;border-right:0;border-bottom:0;text-align:left;border-radius:0}.reference-pill:hover{background:#e0e8da}
"""

CSS += r"""
.walk-options{display:flex;align-items:center;gap:10px;padding:6px 10px;border-radius:7px;background:#e8eee1;min-height:36px;flex-shrink:0}.walk-options label{font-size:9px;color:#697c68;display:flex;align-items:center;gap:5px;white-space:nowrap}.walk-options select{font-size:10px;max-width:230px}.walk-options .transfer-control{flex:1;min-width:0}.transfer-control select{width:100%;max-width:none}.walk-options .square{width:25px;height:25px}.tour-label{font-size:9px;color:#49775f;white-space:nowrap}.walk-readout{padding:6px 12px;background:#f0f5e9;border-top:1px solid #e1e9d7;min-height:47px;flex-shrink:0}.walk-readout>div:first-child{display:flex;justify-content:space-between;gap:8px;font-size:10px;color:#506c62}.walk-readout strong{font-size:13px;color:#1c6d63;font-variant-numeric:tabular-nums}.walk-readout small{font-size:9px;color:#7c8d71}.arrival-track{height:3px;border-radius:3px;background:#dfe7d5;margin:4px 0 2px;overflow:hidden}.arrival-track span{display:block;height:100%;width:0;background:#4c86a6}.terminal-right .arrival-track span{background:#309580}.speed-label{display:flex;align-items:center;gap:3px;font-size:8px;color:#6b8072;white-space:nowrap}.terminal-foot span:last-child{font-variant-numeric:tabular-nums}.lab[data-phase=done] .insight-strip,.lab[data-phase=sampledone] .insight-strip{background:#e5eddf;padding:5px 9px;border-radius:6px}@media(max-height:850px){.lab{gap:5px}.walk-options{min-height:31px;padding:3px 8px}.walk-readout{min-height:40px;padding:4px 10px}.walk-readout strong{font-size:12px}.insight-strip p{font-size:10px}.terminal-head{min-height:43px}.terminal-foot{min-height:20px}.metrics{min-height:42px}.walk-options select{font-size:9px}}@media(max-width:1150px){.walk-options{gap:5px}.walk-options label{font-size:8px}.walk-options select{font-size:9px}.walk-readout strong{font-size:11px}.walk-options .tour-label{display:none}}
"""

JS = WALK_MODEL + r"""
const instances = new WeakMap();
const BLUE = '#4d7fbb', TEAL = '#1b9380', INK = '#294b5c';
const LETTERS = 'ABCDEFGHIJKLMN';
const SIDES = ['left','right'];
const FLIGHT_COLORS = ['#347da2','#d48b40','#458f7a','#9a7597','#b76b51','#687fb0','#a79849','#598e95','#ab6983','#709557','#c47e82','#8471b2','#72883b','#4888a8'];
const skin = ['#dbad84','#e8c29d','#bd8c69','#f0d1af','#a97852'];
const fmt = value => Number(value).toLocaleString('es-PE', {maximumFractionDigits:1});
const sec = value => value===0 ? '0 s' : value < .001 ? '<1 ms' : value < 1 ? `${fmt(value*1000)} ms` : `${fmt(value)} s`;
const esc = value => String(value ?? '').replace(/[&<>"']/g, x => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));

export default function(component) {
  const {parentElement, data, setTriggerValue} = component;
  const root = parentElement.querySelector('#lab');
  if (!root || !data) return;
  let app = instances.get(parentElement);
  if (app) {
    app.data = data;
    app.send = setTriggerValue;
    if(data.validation && data.validation.nonce===app.lastEditNonce && data.validation.ok===false) {
      app.manual=[null,null];app.referenceSide=null;app.playing=false;
      app.toast(data.validation.message||'El servidor rechazó esta asignación.');
    }
    if (data.live_completed && data.live_completed !== app.liveDone) {
      app.liveDone = data.live_completed;
      app.livePending = false;
      app.refresh(true);
      app.toast('Nueva corrida real disponible. Sus resultados se conservan en esta sesión.');
    } else app.refresh(false);
    return app.cleanup;
  }
  const $ = id => root.querySelector('#'+id);
  const speedKind=document.createElement('span');speedKind.id='speed-kind';speedKind.className='speed-label';$('speed').before(speedKind);
  app = {data, send:setTriggerValue, n:10, mode:'lns', seed:0, depth:3, speed:10,
    phase:'ready', clock:0, walkTime:0, sampleTime:0, playing:false,
    manual:[null,null], referenceSide:null, picked:null, highlight:null, frames:[null,null],
    runs:[null,null], raf:0, last:0, lastUI:0, lastMap:['',''], toastUntil:0,
    walkCompare:'impact',walkView:'group',travelSpeed:1,pairId:null,pairs:[],tourIndex:0,tourIds:[],peopleCache:[null,null],
    liveDone:data.live_completed, livePending:false, destroyed:false};
  instances.set(parentElement,app);

  function instance() {return app.data.instances.find(x=>x.n===app.n);}
  // N=4: seed 3 is the central seed of the 5 recorded at p=3 (swap = median P(optimum)); see export verify().
  // N=3: seeds 1, 3, 4 start the swap circuit at the optimum (proves nothing), so open on seed 2.
  function defaultSeed() {return app.mode!=='mixers'?0:app.n===3?2:3;}
  function cost(a) {if(!a || a.length!==app.n || new Set(a).size!==app.n || a.some(x=>x<0||x>=app.n)) return null;let c=0;const I=instance();for(let i=0;i<app.n;i++)for(let k=i+1;k<app.n;k++)c+=I.flows[i][k]*I.distances[a[i]][a[k]];return c;}
  function valid(a) {return cost(a)!==null;}
  function duration() {return Math.max(.000001,...app.runs.filter(Boolean).map(r=>Number(r.seconds||0)));}
  function isWalking() {return app.phase==='walk'||app.phase==='done';}
  function isSampling() {return app.phase==='samples'||app.phase==='sampledone';}
  function sampleDuration() {return Math.max(.01,...app.runs.map(r=>(r?.samples?.length||0)/32));}
  function walkDuration() {return Math.max(0,Walk.duration(cohorts(0)),Walk.duration(cohorts(1)));}
  function selectedPair() {return app.pairs.find(p=>p.id===app.pairId)||null;}
  function configureWalk(keepPair=false) {
    updateFrames();const I=instance();
    app.pairs=Walk.transfers(I.flows,I.distances,app.frames[0]?.assignment,app.frames[1]?.assignment)
      .sort((a,b)=>Math.abs(b.delta??0)-Math.abs(a.delta??0)||Math.max(b.leftCost??0,b.rightCost??0)-Math.max(a.leftCost??0,a.rightCost??0)||a.id.localeCompare(b.id));
    if(!keepPair||!app.pairs.some(p=>p.id===app.pairId))app.pairId=app.pairs[0]?.id||null;
    app.tourIds=app.pairs.slice(0,3).map(p=>p.id);app.tourIndex=Math.max(0,app.tourIds.indexOf(app.pairId));
    app.peopleCache=[null,null];app.walkTime=0;app.highlight=null;app.picked=null;
  }
  function coordinates() {
    const rows = Math.ceil(app.n/4), cols=Math.min(app.n,4);
    const unit=Math.min(138, (600-155)/Math.max(1,cols-1), (330-85)/Math.max(1,rows-1));
    const x0=(600-(cols-1)*unit)/2, y0=(330-(rows-1)*unit)/2;
    return instance().coordinates.map(([x,y])=>[x0+x*unit,y0+y*unit]);
  }
  function sceneBox(){
    const pair=selectedPair();if(!isWalking()||app.walkView==='all'||!pair)return [0,0,600,330];
    const pts=coordinates(),ends=app.frames.flatMap(f=>valid(f?.assignment)?[pts[f.assignment[pair.i]],pts[f.assignment[pair.k]]]:[]);
    if(!ends.length)return [0,0,600,330];
    const xs=ends.map(p=>p[0]),ys=ends.map(p=>p[1]);
    return [Math.min(...xs)-56,Math.min(...ys)-46,Math.max(180,Math.max(...xs)-Math.min(...xs)+112),Math.max(120,Math.max(...ys)-Math.min(...ys)+112)];
  }
  function chooseRuns() {
    const kind=app.mode==='lns'?'lns':'qaoa';
    const methods=kind==='lns'?['exact','qaoa']:['x','perm'];
    app.runs=methods.map(method=>app.data.runs.filter(r=>r.n===app.n && r.kind===kind && r.method===method && Number(r.seed)===app.seed && (kind==='lns'||Number(r.config?.reps ?? r.reps ?? 2)===app.depth)).at(-1)||null);
  }
  function reset() {
    app.playing=false;app.phase='ready';app.clock=0;app.walkTime=0;app.sampleTime=0;
    app.manual=[null,null];app.referenceSide=null;app.picked=null;app.highlight=null;app.lastMap=['',''];
    app.walkCompare=app.mode==='lns'?'impact':'algorithms';app.pairId=null;app.pairs=[];app.peopleCache=[null,null];
    SIDES.forEach(s=>$("speech-"+s).hidden=true);
    chooseRuns();refresh(true);
  }
  function frame(run,side) {
    const I=instance();
    if(app.manual[side]) {const a=app.manual[side];return {assignment:a,cost:cost(a),best_cost:cost(a),manual:true,reference:app.referenceSide===side,event:'manual'};}
    if(isWalking()&&side===0&&app.walkCompare==='optimum')return {assignment:I.exact_assignment,cost:I.optimum,best_cost:I.optimum,reference:true,event:'reference'};
    if(isWalking()&&side===0&&app.walkCompare==='impact'&&app.mode==='lns'&&app.runs[1]){const a=app.runs[1].start_assignment;return {assignment:a,cost:cost(a),best_cost:null,baseline:true,event:'baseline'};}
    if(app.n<=2) return {assignment:I.exact_assignment,cost:I.optimum,best_cost:I.optimum,elapsed_s:0,event:'trivial'};
    if(!run) {const a=Array.from({length:app.n},(_,i)=>i);return {assignment:a,cost:cost(a),best_cost:null,missing:true,event:'missing'};}
    if(app.mode==='mixers') {
      if(isSampling()) {
        const samples=run.samples||[];const index=Math.min(samples.length-1,Math.floor(app.sampleTime/sampleDuration()*samples.length));
        const sample=samples[Math.max(0,index)];
        if(sample) return {assignment:sample.assignment,matrix:sample.matrix,cost:sample.feasible?sample.cost:null,best_cost:cost(run.final_assignment),invalid:!sample.feasible,event:'sample',sampleIndex:index,elapsed_s:run.seconds};
      }
      if(app.phase==='walk'||app.phase==='done') {return {assignment:run.final_assignment,cost:cost(run.final_assignment),best_cost:cost(run.final_assignment),invalid:!valid(run.final_assignment),event:'final',elapsed_s:run.seconds};}
      const a=run.start_assignment;
      return {assignment:a,cost:valid(a)?cost(a):null,best_cost:null,training:true,elapsed_s:Math.min(app.clock,run.seconds),event:'training'};
    }
    if(app.phase==='walk'||app.phase==='done') {const a=run.final_assignment;return {assignment:a,cost:cost(a),best_cost:cost(a),elapsed_s:run.seconds,event:'final'};}
    let e={assignment:run.start_assignment,best_assignment:run.start_assignment,cost:cost(run.start_assignment),best_cost:cost(run.start_assignment),step:0,elapsed_s:0,event:'start'};
    for(const next of run.events||[]) {if(next.elapsed_s<=app.clock+1e-9)e=next;else break;}
    return e;
  }
  function updateFrames() {app.frames=app.runs.map((r,s)=>frame(r,s));}
  function statusLabel(f,r) {
    if(isWalking()&&!f.missing){const stats=Walk.stats(cohorts(f===app.frames[0]?0:1),app.walkTime);if(!valid(f.assignment))return ['Sin plan válido','bad'];if(stats.total===0)return ['Sin conexiones','good'];if(stats.arrived===stats.total)return ['Grupo completado','good'];return [app.playing?'En camino':'Recorrido pausado','working'];}
    if(f.reference)return ['Referencia exacta','good'];
    if(f.manual)return ['Tu asignación','manual'];
    if(app.n<=2)return ['Óptimo trivial','good'];
    if(f.missing)return ['Traza no disponible','bad'];
    if(app.phase==='ready')return ['En espera',''];
    if(f.invalid)return ['Muestra inválida','bad'];
    if(f.event==='sample')return ['Muestra válida','good'];
    if(f.training)return [app.clock>=r.seconds?'Entrenamiento listo':'Entrenando QAOA',app.clock>=r.seconds?'good':'working'];
    if(app.phase==='walk'||app.phase==='done'){if(app.mode==='mixers')return ['Mejor shot válido',''];return [f.cost===instance().optimum?'Óptimo encontrado':'Mejor de esta corrida',f.cost===instance().optimum?'good':''];}
    if(f.kick)return ['Patada: explorar de nuevo','bad'];
    if(f.event==='complete'||app.clock>=r.seconds)return ['Búsqueda terminada','good'];
    if(f.accepted===false)return ['Movimiento rechazado',''];
    return [f.accepted?'Movimiento aceptado':'Explorando','working'];
  }
  function refresh(force=false) {
    if(!instance())return;
    chooseRuns();updateFrames();
    const I=instance();
    $('n-label').textContent=app.n;$('size').value=app.n;
    $('size').max=Math.max(...app.data.instances.map(x=>x.n));
    root.querySelectorAll('[data-size]').forEach(b=>b.hidden=!app.data.instances.some(x=>x.n===Number(b.dataset.size)));
    $('instance-kind').textContent=I.synthetic?'AMPLIACIÓN SINTÉTICA · N='+app.n:'BENCHMARK QAP10';
    root.querySelectorAll('[data-size]').forEach(b=>b.classList.toggle('active',Number(b.dataset.size)===app.n));
    $('mode').value=app.mode;$('mode').disabled=app.n<=3;
    const availableSeeds=[...new Set(app.data.runs.filter(r=>r.n===app.n&&r.kind===(app.mode==='lns'?'lns':'qaoa')).map(r=>Number(r.seed)))];
    for(const option of $('seed').options)option.disabled=!availableSeeds.includes(Number(option.value));
    $('seed').value=app.seed;$('seed').disabled=availableSeeds.length<2||app.n<=2;
    $('depth').value=app.mode==='lns'?(app.runs[1]?.config?.reps??2):app.depth;$('depth').disabled=app.mode==='lns'||app.n<=2;
    $('reference').textContent=I.optimum;
    $('show-optimum').title=I.reference_method==='branch_bound_gilmore_lawler'?'Óptimo certificado por ramificación y poda; muestra la asignación global':'Óptimo por enumeración completa; muestra la asignación global';
    $('exact-time').textContent=`${sec(I.exact_seconds)} · ${Number(I.stats.assignments).toLocaleString('es-PE')} opciones`;
    $('live').hidden=app.mode!=='mixers'||app.n<3;
    $('live').disabled=app.livePending;
    $('live').textContent=app.livePending?'Qiskit está calculando…':'Ejecutar Qiskit ahora ↗';
    $('samples').hidden=app.mode!=='mixers'||app.n<=2;
    root.dataset.phase=app.phase;root.dataset.playing=String(app.playing);root.dataset.pair=app.pairId||'';
    $('walk').textContent=isWalking()?'Repetir recorrido ↗':'Ver el impacto ↗';
    const missing=app.n>2&&app.runs.some(r=>!r);
    $('play').disabled=missing;
    $('next').disabled=missing||app.n<=2||(app.mode==='mixers'&&!isSampling());
    $('samples').disabled=missing;
    $('play').innerHTML=app.playing?'<span>Ⅱ</span> Pausar':app.phase==='done'?'<span>↺</span> Repetir recorrido':app.phase==='sampledone'?'<span>↺</span> Repetir muestras':app.phase==='ready'?'<span>▶</span> Reproducir duelo':'<span>▶</span> Continuar';
    $('restore').hidden=!app.manual.some(Boolean)&&!(isWalking()&&app.walkCompare!=='algorithms');
    $('step-search').classList.toggle('selected',!['walk','done'].includes(app.phase));
    $('step-walk').classList.toggle('selected',['walk','done'].includes(app.phase));
    $('phase-message').textContent=app.manual.some(Boolean)?'Exploración manual · costo calculado sobre todos los flujos':isSampling()?'Shots registrados · factibilidad y probabilidad son métricas diferentes':isWalking()?(app.walkCompare==='impact'?'Impacto: asignación inicial → resultado, con la misma demanda y velocidad':app.walkCompare==='optimum'?'Referencia exacta → mejor resultado de esta corrida':'Misma demanda y velocidad · las asignaciones pueden coincidir'):app.mode==='lns'?'Mismo inicio. Mismos vecindarios. Distinto subsolver.':'Mismo problema · distinta forma de imponer las restricciones';
    for(let side=0;side<2;side++) {
      const s=SIDES[side],r=app.runs[side],f=app.frames[side];
      const names=app.mode==='lns'?['LNS + exacto local','LNS + QAOA']:['QAOA con penalización','QAOA de intercambio'];
      $('title-'+s).textContent=f.reference?'Referencia exacta':f.manual?'Tu asignación':f.baseline?'Antes de optimizar':app.n<=2?'Todas son óptimas':names[side];
      $('method-'+s).textContent=f.reference?(I.reference_method==='branch_bound_gilmore_lawler'?'ÓPTIMO CERTIFICADO · RAMIFICACIÓN Y PODA':'ENUMERACIÓN COMPLETA · RESULTADO GUARDADO'):f.manual?'EXPLORACIÓN MANUAL':f.baseline?'ASIGNACIÓN INICIAL · MISMA DEMANDA':app.n<=2?'CASO INTRODUCTORIO':app.mode==='lns'?(side?'BÚSQUEDA HÍBRIDA':'BÚSQUEDA CLÁSICA'):(side?`MIXER DE INTERCAMBIO · P=${app.depth}`:`MIXER X · P=${app.depth}`);
      const [label,cls]=statusLabel(f,r);$('status-'+s).textContent=label;$('status-'+s).className='status '+cls;
      $('cost-'+s).textContent=f.cost==null?'—':f.cost;
      $('best-'+s).textContent=f.best_cost==null?'—':f.best_cost;
      const elapsed=app.phase==='ready'?0:Math.min(app.clock,Number(r?.seconds||0));
      $('time-'+s).textContent=f.reference?sec(I.exact_seconds):f.manual||f.baseline?'—':r?sec(isWalking()||isSampling()?r.seconds:elapsed):app.n<=2?sec(I.exact_seconds):'—';
      root.querySelector('.terminal-'+s+' .metrics>div:first-child small').textContent=isWalking()?'Costo del plan completo':'Costo actual';
      root.querySelector('.terminal-'+s+' .metrics>div:nth-child(2) small').textContent=app.mode==='mixers'&&!f.manual?`Mejor shot válido de ${r?.total_shots??2048}`:'Mejor encontrado';
      const gap=f.cost!=null&&I.optimum>0?100*(f.cost-I.optimum)/I.optimum:0;
      $('gap-'+s).textContent=f.cost==null?'Sin plan':gap===0?'Óptimo':`+${fmt(gap)}%`;
      $('gap-'+s).className='gap '+(f.cost===I.optimum?'optimal':'');
      const direct=app.mode==='mixers'&&app.n>2&&!f.manual&&!f.reference&&!f.baseline&&!!r;
      $('popt-wrap-'+s).hidden=!direct;$('valid-wrap-'+s).hidden=!direct;$('gap-'+s).hidden=direct;
      if(direct){const trivial=!!r.start_is_optimal;root.querySelector('#popt-wrap-'+s+' small').textContent=trivial?'P(óptimo) · arrancó óptimo':'P(óptimo)';$('popt-'+s).textContent=trivial?'n/a':`${fmt(100*r.p_optimal)}%`;$('valid-'+s).textContent=`${fmt(100*r.p_feasible)}%`;}
      if(f.baseline)$('detail-'+s).textContent='Inicio de la corrida · sin búsqueda · no es otro algoritmo';
      else if(f.reference)$('detail-'+s).textContent='Óptimo global certificado · sin traza de pasos intermedios';
      else if(f.manual)$('detail-'+s).textContent=app.data.validation?.ok&&app.data.validation.nonce===app.lastEditNonce?'Costo verificado por Python · cada par una vez':'Costo QAP local · comprobando con Python';
      else if(app.n<=2)$('detail-'+s).textContent=app.n===1?'Una asignación · sin conexiones':'Dos asignaciones · ambas cuestan 10';
      else if(f.missing)$('detail-'+s).textContent='Resultado agregado en Evidencia; no hay pasos para reproducir';
      else if(app.mode==='mixers')$('detail-'+s).textContent=`semilla ${app.seed} · p=${app.depth} · azar válido ${fmt(100*I.stats.p_optimal_random)}%${r.start_is_optimal?' · arrancó en el óptimo (no cuenta)':''}`;
      else $('detail-'+s).textContent=`${r?.config?.iterations??60} iter. · K=${r?.config?.k??3} · semilla ${app.seed}${side?' · 9 qubits':''}${f.step?' · paso '+f.step:''}`;
      drawGates(side,force);
    }
    const runMax=duration();
    const end=isWalking()?walkDuration():isSampling()?sampleDuration():runMax;
    $('clock-label').textContent=isWalking()?`${fmt(app.walkTime)} s ilustrativos`:isSampling()?`Shot ${(app.frames[0]?.sampleIndex??0)+1}`:sec(app.clock);
    $('duration-label').textContent=isWalking()?(app.phase==='done'?'Recorrido completo':`${fmt(end)} s · hasta la última llegada`):isSampling()?(app.phase==='sampledone'?'Muestreo completo':'shots registrados'):`${sec(runMax)} medidos`;
    if(parentElement.activeElement!==$('timeline'))$('timeline').value=end===0?1000:Math.min(1000,Math.round((isWalking()?app.walkTime:isSampling()?app.sampleTime:app.clock)/end*1000));
    const visual=isWalking()||isSampling(),speedOptions=visual?[.5,1,2,4]:[1,5,10,20];
    if($('speed').dataset.kind!==(visual?'visual':'calculation')){$('speed').innerHTML=speedOptions.map(v=>`<option value="${v}">${v}×</option>`).join('');$('speed').dataset.kind=visual?'visual':'calculation';}
    $('speed').value=visual?app.travelSpeed:app.speed;$('speed').title=visual?'Velocidad del recorrido ilustrativo':'Aceleración de tiempos de cálculo registrados';
    $('speed-kind').textContent=visual?'Animación':'Cálculo';
    $('chart-title').textContent=app.manual.some(Boolean)?'Curvas de las corridas originales':app.mode==='lns'?'Costo por iteración · sólido = mejor':'Energía QUBO por evaluación · no es costo';
    $('legend-left').textContent=app.mode==='lns'?'LNS clásico':'Mixer X';
    $('legend-right').textContent=app.mode==='lns'?'LNS QAOA':'Intercambio';
    $('provenance').textContent=app.runs.some(r=>r?.live)?'Aer ideal · corrida calculada en esta sesión · sin hardware cuántico':'Aer ideal · reproducción de corridas registradas · sin hardware cuántico';
    updateWalkControls();insight();drawChart();drawPeople(0);drawPeople(1);
  }
  app.refresh=refresh;
  function insight() {
    const I=instance();let text;
    if(isWalking()) {
      const a=cost(app.frames[0].assignment),b=cost(app.frames[1].assignment),p=selectedPair();
      const same=valid(app.frames[0].assignment)&&JSON.stringify(app.frames[0].assignment)===JSON.stringify(app.frames[1].assignment);
      if(app.n===1)text='Sin conexiones: no hay personas que mover ni tiempo que esperar. Sube N para descubrir el problema.';
      else if(a===null||b===null)text='Una asignación inválida no permite evaluar el recorrido: hace falta una puerta única para cada vuelo. No se le atribuye un costo factible.';
      else if(same)text=`Misma asignación: los recorridos deben coincidir. El costo es ${a}; la diferencia entre algoritmos está en el cálculo (${sec(app.runs[0]?.seconds||0)} vs ${sec(app.runs[1]?.seconds||0)}).`;
      else if(app.walkView==='all')text=`${app.phase==='done'?'Recorrido completo. ':''}La suma de distancias de todas las figuras coincide con el costo QAP: ${a} frente a ${b}. ${b<a?`Reducción de ${a-b} unidades (${fmt(100*(a-b)/a)}%) respecto de la izquierda.`:b>a?`La derecha requiere ${b-a} unidades más.`:'Mismo costo, con recorridos diferentes.'}`;
      else if(p)text=`${app.phase==='done'?'Grupo completado. ':''}${LETTERS[p.i]} → ${LETTERS[p.k]}: flujo ${p.flow} × distancia ${p.leftDistance} = ${p.leftCost}, frente a ${p.flow} × ${p.rightDistance} = ${p.rightCost}. ${p.delta>0?`Esta conexión ahorra ${p.delta} unidades.`:p.delta<0?`Esta conexión empeora ${-p.delta} unidades.`:'Esta conexión empata.'} Total de los planes: ${a} → ${b}.`;
      else text='No hay conexiones con flujo positivo en esta instancia.';
    }
    else if(app.manual.some(Boolean))text='Tu turno: intercambia vuelos y observa qué conexiones recorren más distancia. El duelo original se puede restaurar.';
    else if(app.n<=2)text=app.n===1?'Una puerta y un vuelo: no hay decisión que optimizar. Sube N para que aparezca el problema.':'Aquí las dos permutaciones cuestan lo mismo: todas son óptimas. Encontrar el óptimo todavía no demuestra habilidad.';
    else if(app.runs.some(r=>!r))text='Esta combinación aún no tiene una traza registrada. Puedes explorar asignaciones manuales o consultar los resultados en Evidencia.';
    else if(app.phase==='sampledone')text=`Vista de ${Math.max(...app.runs.map(r=>r?.samples?.length||0))} shots completada. Las probabilidades describen el circuito completo; encontrar un buen shot entre 2048 no garantiza alta probabilidad de óptimo. Usa «Ver el impacto» para explorar las rutas.`;
    else if(app.phase==='samples')text='Una muestra inválida puede dejar vuelos sin puerta o asignar varios a la misma. El mixer de intercambio conserva la regla uno a uno.';
    else if(app.mode==='mixers')text=`Azar válido: ${fmt(100*I.stats.p_optimal_random)}% de P(óptimo). Con 2048 shots, "mejor shot válido" casi siempre llega al óptimo porque se prueban muchos; lo que distingue a los mixers es P(óptimo) y el % de shots válidos. Es una semilla, no la mediana (ver Evidencia).`;
    else if(['walk','done'].includes(app.phase)) {
      const a=cost(app.runs[0].final_assignment),b=cost(app.runs[1].final_assignment);
      text=a===b?`En esta semilla ambos terminaron en ${a}. Compara también el tiempo medido; la calidad final por sí sola no cuenta toda la historia.`:`En esta semilla: clásico ${a}, híbrido ${b}; óptimo global ${I.optimum}. Los personajes representan el costo de conexiones de cada asignación.`;
    } else if(app.mode==='lns'&&app.clock>=duration()) {
      const a=app.runs[0].cost,b=app.runs[1].cost;
      text=`Búsqueda completa: clásico ${a}, híbrido ${b}, óptimo certificado ${I.optimum}. ${b===I.optimum?'El híbrido alcanzó el óptimo en esta semilla.':`El híbrido quedó a +${fmt(100*(b-I.optimum)/I.optimum)}% del óptimo.`} Tiempos: ${sec(app.runs[0].seconds)} vs ${sec(app.runs[1].seconds)}. «Ver el impacto» muestra los recorridos.`;
    } else if(app.n>10&&app.phase==='ready')text=`N=${app.n}, ampliación sintética: ${I.stats.assignments.toLocaleString('es-PE')} asignaciones; óptimo certificado ${I.optimum}. El híbrido mantiene 9 qubits por llamada, frente a ${app.n*app.n} del QUBO completo. Reproduce la búsqueda o compara sus recorridos con el óptimo.`;
    else text='¿Resolver bien un vecindario garantiza una buena solución global? Observa las mesetas, los cambios y las patadas de exploración.';
    if($('insight').textContent!==text)$('insight').textContent=text;
  }
  function updateWalkControls() {
    const visible=isWalking();$('walk-options').hidden=!visible;
    SIDES.forEach(s=>$('walk-readout-'+s).hidden=!visible);
    if(!visible)return;
    const comparison=$('walk-compare');
    if(!comparison.querySelector('[value=manual]'))comparison.insertAdjacentHTML('beforeend','<option value="manual" disabled>Tu asignación → resultado</option>');
    comparison.querySelector('[value=manual]').hidden=!app.manual.some(Boolean);
    comparison.querySelector('[value=impact]').disabled=app.mode!=='lns'||app.n<=2;
    comparison.value=app.manual.some(Boolean)?'manual':app.walkCompare;
    $('walk-view').value=app.walkView;
    const options=app.pairs.map(p=>`<option value="${p.id}">${LETTERS[p.i]} → ${LETTERS[p.k]} · flujo ${p.flow} · Δ ${p.delta==null?'—':p.delta>0?'−'+p.delta:p.delta<0?'+'+(-p.delta):'0'} costo</option>`).join('');
    if($('transfer').innerHTML!==options)$('transfer').innerHTML=options;
    $('transfer').value=app.pairId||'';$('transfer').disabled=app.walkView==='all'||app.pairs.length===0;
    $('prev-transfer').disabled=$('next-transfer').disabled=app.walkView==='all'||app.pairs.length<2;
    $('tour-label').textContent=app.walkView==='tour'?`Conexión ${app.tourIndex+1}/${app.tourIds.length}`:app.walkView==='all'?'Costo completo':`1 de ${app.pairs.length} · total evaluado completo`;
  }
  function drawGates(side,force=false) {
    const f=app.frames[side],pts=coordinates();
    const released=(app.phase==='search'&&f.flights)||[];
    const box=sceneBox();$('gates-'+SIDES[side]).setAttribute('viewBox',box.join(' '));
    const marker=JSON.stringify([f.assignment,f.matrix,f.invalid,released,app.picked,app.mode,app.pairId,isWalking()]);
    if(!force&&app.lastMap[side]===marker)return;
    app.lastMap[side]=marker;
    const pieces=[];
    for(let g=0;g<app.n;g++) {
      const flights=f.matrix?f.matrix.flatMap((row,i)=>row[g]?[i]:[]):valid(f.assignment)?f.assignment.flatMap((gate,i)=>gate===g?[i]:[]):[];
      const conflict=f.matrix&&flights.length!==1;
      const chosen=app.picked?.side===side&&app.picked.gate===g;
      const isReleased=flights.some(i=>released.includes(i));
      const [x,y]=pts[g], name=flights.map(i=>LETTERS[i]).join(' · ')||'SIN VUELO';
      pieces.push(`<g class="gate ${conflict?'conflict':''} ${chosen?'chosen':''} ${isReleased?'released':''}" transform="translate(${x},${y})" data-gate="${g}" role="button" tabindex="0" aria-label="Puerta ${g+1}, ${esc(name)}. Selecciona dos puertas para intercambiar"><rect class="building" x="-37" y="-32" width="74" height="49" rx="6"/><rect class="gate-marker" x="-13" y="17" width="26" height="4" rx="2"/><text class="gate-number" x="0" y="-20" text-anchor="middle">PUERTA ${String(g+1).padStart(2,'0')}</text><circle cx="-24" cy="0" r="3" fill="${flights.length?FLIGHT_COLORS[flights[0]]:'#b9c3b2'}"/><text class="${flights.length?'flight':'empty'}" x="3" y="0" text-anchor="middle">${name}</text>${conflict?'<circle class="conflict-dot" cx="32" cy="-28" r="5"/>':''}</g>`);
    }
    $('gates-'+SIDES[side]).innerHTML=pieces.join('');
  }
  function drawChart() {
    const series=app.runs.map((r,s)=>!r||app.referenceSide===s?[]:app.mode==='lns'?(r.events||[]).map(e=>Number(e.best_cost)):(r.objective_history||[]));
    const currents=app.runs.map((r,s)=>!r||app.referenceSide===s||app.mode!=='lns'?[]:(r.events||[]).map(e=>Number(e.cost)));
    const all=[...series.flat(),...currents.flat()].filter(Number.isFinite), svg=$('convergence');
    if(!all.length){svg.innerHTML='<text x="3" y="34" fill="#8b9984" font-size="11">Las curvas aparecerán con una traza registrada.</text>';return;}
    let min=Math.min(...all),max=Math.max(...all);if(app.mode==='lns')min=Math.min(min,instance().optimum);const span=max-min||1;
    const y=v=>50-(v-min)/span*40;
    const elements=[`<path d="M28 9H510 M28 50H510" stroke="#dfe6d8" stroke-dasharray="3 4"/><text x="1" y="12" font-size="8" fill="#8b9984">${Math.round(max)}</text><text x="1" y="52" font-size="8" fill="#8b9984">${Math.round(min)}</text>`];
    if(app.mode==='lns')elements.push(`<path d="M28 ${y(instance().optimum)}H510" stroke="#9fb87f" stroke-dasharray="3 4"/>`);
    currents.forEach((values,s)=>{if(!values.length)return;const pts=values.map((v,i)=>`${28+i/Math.max(1,values.length-1)*480},${y(v)}`).join(' ');elements.push(`<polyline points="${pts}" fill="none" stroke="${s?TEAL:BLUE}" stroke-width="1" stroke-dasharray="3 3" opacity=".4"/>`);});
    series.forEach((values,s)=>{if(!values.length)return;const x=i=>28+i/Math.max(1,values.length-1)*480;const pts=values.map((v,i)=>`${x(i)},${y(v)}`).join(' ');elements.push(`<polyline points="${pts}" fill="none" stroke="${s?TEAL:BLUE}" stroke-width="1.9"/>`);const f=app.frames[s];let step=app.mode==='lns'?Math.min(values.length-1,Number(f?.step||0)):(app.clock>=app.runs[s].seconds?values.length-1:0);if(['walk','done','samples'].includes(app.phase))step=values.length-1;elements.push(`<circle cx="${x(step)}" cy="${y(values[step])}" r="3" fill="${s?TEAL:BLUE}" stroke="#fff" stroke-width="1"/>`);});
    elements.push('<text x="28" y="63" font-size="8" fill="#8b9984">0</text><text x="505" y="63" text-anchor="end" font-size="8" fill="#8b9984">'+Math.max(...series.map(v=>v.length-1))+'</text>');svg.innerHTML=elements.join('');
  }
  function cohorts(side) {
    const f=app.frames[side];if(!f||!valid(f.assignment))return [];
    const I=instance(),pair=app.walkView==='all'?null:app.pairId;
    const key=JSON.stringify([app.n,f.assignment,pair,app.walkView]);
    if(app.peopleCache[side]?.key===key)return app.peopleCache[side].people;
    const pts=coordinates(),people=Walk.people(I.flows,I.distances,f.assignment,pair).map(p=>({...p,a:pts[p.g],b:pts[p.h]}));
    app.peopleCache[side]={key,people};return people;
  }
  function point(person,t) {
    const f=Walk.progress(person,t);
    const [ax,ay]=person.a,[bx,by]=person.b;
    const h=Math.abs(bx-ax),v=Math.abs(by-ay),distance=(h+v)*f;
    const x=distance<=h?ax+Math.sign(bx-ax)*distance:bx;
    const y=distance<=h?ay:ay+Math.sign(by-ay)*(distance-h);
    return {x:x+person.jitter,y:y+23+((person.id%3)-1)*3.2,f,waiting:t<person.delay};
  }
  function rounded(ctx,x,y,w,h,r,fill) {ctx.beginPath();ctx.roundRect(x,y,w,h,r);ctx.fillStyle=fill;ctx.fill();}
  function avatar(ctx,x,y,id,mood,t,arrived=false,size=1) {
    const bob=arrived?0:Math.sin(t*14+id)*.8;
    const color=['#397f9f','#c69341','#bc6c50'][mood];
    ctx.save();ctx.translate(x,y+bob);ctx.scale(size,size);
    ctx.fillStyle='#29492e1a';ctx.beginPath();ctx.ellipse(0,7,4.8,1.8,0,0,Math.PI*2);ctx.fill();
    const stride=arrived?0:Math.sin(t*12+id);ctx.strokeStyle='#3f5260';ctx.lineWidth=1.3;ctx.beginPath();ctx.moveTo(-1.5,3);ctx.lineTo(-2.5+stride,6.5);ctx.moveTo(1.5,3);ctx.lineTo(2.5-stride,6.5);ctx.stroke();
    rounded(ctx,-3,-2,6,6,1.7,color);rounded(ctx,4,1,3,4,1,'#65786b');
    ctx.fillStyle=skin[id%skin.length];ctx.beginPath();ctx.arc(0,-4.5,3.4,0,Math.PI*2);ctx.fill();
    ctx.fillStyle='#414a40';ctx.beginPath();ctx.arc(.2,-6.3,3.1,Math.PI,Math.PI*2);ctx.fill();
    ctx.fillStyle='#4c443c';ctx.fillRect(-1.5,-4.5,.7,.7);ctx.fillRect(1,-4.5,.7,.7);
    ctx.strokeStyle='#7c4e3d';ctx.lineWidth=.7;ctx.beginPath();if(mood===2){ctx.moveTo(-1.4,-2.2);ctx.quadraticCurveTo(0,-4,1.4,-2.2);}else{ctx.moveTo(-1.2,-2.8);ctx.quadraticCurveTo(0,mood===0?-1.7:-3,1.3,-2.8);}ctx.stroke();
    if(mood===2 && !arrived && id%3===0){ctx.fillStyle='#bd7755';ctx.font='bold 7px sans-serif';ctx.fillText('!',5,-10);}
    ctx.restore();
  }
  function drawFloor(ctx,pts) {
    ctx.fillStyle='#f7f9f0';ctx.fillRect(0,0,600,330);
    ctx.fillStyle='#e8edde';for(let x=10;x<600;x+=20)for(let y=10;y<330;y+=20){ctx.beginPath();ctx.arc(x,y,.6,0,Math.PI*2);ctx.fill();}
    // Keep corridors across the whole grid, including cells without a gate:
    // the horizontal-then-vertical walk must follow the same Manhattan metric.
    const links=[],rows=Math.ceil(app.n/4),cols=Math.min(app.n,4),unit=pts[1]?pts[1][0]-pts[0][0]:0;
    const floorPoint=(row,col)=>[pts[0][0]+col*unit,pts[0][1]+row*unit];
    for(let row=0;row<rows;row++)for(let col=0;col<cols;col++){if(col+1<cols)links.push([floorPoint(row,col),floorPoint(row,col+1)]);if(row+1<rows)links.push([floorPoint(row,col),floorPoint(row+1,col)]);}
    ctx.lineCap='round';for(const [a,b] of links){ctx.beginPath();ctx.moveTo(a[0],a[1]+23);ctx.lineTo(b[0],b[1]+23);ctx.lineWidth=24;ctx.strokeStyle='#e5ecdf';ctx.stroke();ctx.lineWidth=1;ctx.strokeStyle='#fcfdf9';ctx.setLineDash([3,5]);ctx.stroke();ctx.setLineDash([]);}
    ctx.font='8px "Segoe UI", sans-serif';ctx.fillStyle='#9aa58f';ctx.fillText('TERMINAL DE CONEXIONES',19,19);ctx.fillText('ESQUEMA DEL BENCHMARK · PASILLOS MANHATTAN',19,320);
    for(const [x,y] of [[35,62],[560,82],[45,255],[552,248]]){rounded(ctx,x-6,y,12,10,3,'#c1c7a9');for(let j=0;j<4;j++){ctx.fillStyle=j%2?'#83a874':'#9bb985';ctx.beginPath();ctx.ellipse(x+(j%2?3:-3),y-2-j*1.3,4,7,j*.9,0,Math.PI*2);ctx.fill();}}
    for(const [x,y] of [[40,160],[545,160]]){rounded(ctx,x,y,18,6,2,'#aebea5');rounded(ctx,x+2,y+7,2,3,1,'#8f9e88');rounded(ctx,x+14,y+7,2,3,1,'#8f9e88');}
  }
  function drawPeople(side) {
    const canvas=$('canvas-'+SIDES[side]),rect=canvas.getBoundingClientRect();if(rect.width<1||rect.height<1)return;
    const ratio=Math.min(2,window.devicePixelRatio||1);const w=Math.round(rect.width*ratio),h=Math.round(rect.height*ratio);
    if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;}
    const ctx=canvas.getContext('2d');ctx.setTransform(1,0,0,1,0,0);ctx.clearRect(0,0,w,h);
    const box=sceneBox(),scale=Math.min(rect.width/box[2],rect.height/box[3]),ox=(rect.width-box[2]*scale)/2-box[0]*scale,oy=(rect.height-box[3]*scale)/2-box[1]*scale;
    ctx.setTransform(scale*ratio,0,0,scale*ratio,ox*ratio,oy*ratio);
    const pts=coordinates();drawFloor(ctx,pts);
    const f=app.frames[side];if(!f)return;
    const walking=isWalking();
    const people=cohorts(side),stats=Walk.stats(people,app.walkTime),pair=selectedPair();
    const group=app.walkView!=='all';
    if(walking&&group&&people.length){
      const p=people[0],sameDistance=pair&&pair.leftDistance===pair.rightDistance;
      ctx.beginPath();ctx.moveTo(p.a[0],p.a[1]+23);ctx.lineTo(p.b[0],p.a[1]+23);ctx.lineTo(p.b[0],p.b[1]+23);
      ctx.strokeStyle=sameDistance?'#6e9ba6':p.d===(Math.min(pair?.leftDistance??Infinity,pair?.rightDistance??Infinity))?'#46a582':'#ce9e55';ctx.lineWidth=11;ctx.globalAlpha=.38;ctx.stroke();ctx.globalAlpha=1;
    }
    if(walking) {
      for(const p of people) {
        const pos=point(p,app.walkTime);
        if(app.highlight?.side===side&&app.highlight.id===p.id){ctx.beginPath();ctx.moveTo(p.a[0],p.a[1]+23);ctx.lineTo(p.b[0],p.a[1]+23);ctx.lineTo(p.b[0],p.b[1]+23);ctx.strokeStyle='#d49736';ctx.lineWidth=2;ctx.stroke();}
        ctx.globalAlpha=pos.waiting ? .55 : 1;avatar(ctx,pos.x,pos.y,p.id,p.mood,app.walkTime,pos.f>=1||pos.waiting,group?1.8:1);ctx.globalAlpha=1;
      }
    } else if(f.invalid || f.training&&app.mode==='mixers') {
      for(let i=0;i<Math.min(12,app.n*2);i++)avatar(ctx,238+(i%6)*17,280+Math.floor(i/6)*15,i,2,app.sampleTime,true);
      ctx.font='9px "Segoe UI",sans-serif';ctx.fillStyle='#a27355';ctx.fillText(f.invalid?'Esperando una asignación válida…':'Se entrena una distribución, todavía no es una asignación.',180,255);
    }
    const s=SIDES[side],arrival=$('arrivals-'+s);
    arrival.dataset.arrived=stats.arrived;arrival.dataset.total=stats.total;
    if(walking) {
      arrival.textContent=valid(f.assignment)?`${stats.arrived}/${stats.total} llegadas ${group?'en este grupo':'· flujo completo'}`:'Sin recorrido: asignación inválida';
      $('trip-'+s).textContent=group&&pair?`Conexión ${LETTERS[pair.i]} → ${LETTERS[pair.k]} · flujo ${pair.flow}`:'Distancia acumulada · todos los flujos';
      $('walked-'+s).textContent=valid(f.assignment)?`${fmt(stats.travelled)} / ${stats.totalDistance} unidades`:'Sin costo factible';
      $('walked-'+s).dataset.travelled=stats.travelled;$('walked-'+s).dataset.target=stats.totalDistance;
      $('arrival-fill-'+s).style.width=`${stats.total?100*stats.arrived/stats.total:0}%`;
      $('trip-equation-'+s).textContent=group&&pair?`Este grupo: ${pair.flow} × ${side?pair.rightDistance:pair.leftDistance} = ${side?pair.rightCost:pair.leftCost}. El costo superior evalúa todas las conexiones.`:'Al llegar todos, esta suma coincide exactamente con el costo del plan.';
    }
    else if(isSampling())arrival.textContent=`Shot ${(f.sampleIndex??0)+1} · ${f.invalid?'hay conflictos':'permutación válida'}`;
    else $('arrivals-'+SIDES[side]).textContent=app.playing?'Pausa para intercambiar vuelos':'↔ Arrastra o selecciona dos puertas';
    const other=Walk.stats(cohorts(1-side),app.walkTime);
    if(walking&&group&&people.length&&app.walkTime>.3&&!app.highlight){const speech=$('speech-'+s);speech.hidden=false;const finished=stats.arrived===stats.total,otherFinished=other.total>0&&other.arrived===other.total;speech.innerHTML=finished&&!otherFinished?'<strong>«¡Ya llegamos!»</strong>La otra terminal todavía está recorriendo esta conexión.':!finished&&otherFinished?'<strong>«¿Todavía nos queda camino?»</strong>El mismo grupo ya llegó en la otra terminal.':pair&&pair.leftDistance===pair.rightDistance?'<strong>Misma distancia, mismo recorrido.</strong>La comparación de tiempo de cálculo está arriba.':`<strong>${finished?'Grupo completado':'«Mi maleta también cuenta los pasos…»'}</strong>${people[0].d} unidades por figura; ${stats.totalDistance} para todo el grupo.`;}
    else if(!app.highlight)$('speech-'+SIDES[side]).hidden=true;
  }
  function goWalk(keepPair=false) {
    if(app.n>2&&app.runs.some(r=>!r)&&!app.manual.some(Boolean)){app.toast('Falta la traza de este tamaño. Puedes intercambiar vuelos en modo manual.');return;}
    app.phase='walk';app.clock=duration();configureWalk(keepPair===true);app.playing=walkDuration()>0;
    if(!app.playing)app.phase='done';refresh(true);
  }
  function play() {
    if(app.playing){app.playing=false;refresh();return;}
    if(app.phase==='done'){goWalk(true);return;}
    if(app.phase==='sampledone'){samples();return;}
    if(app.manual.some(Boolean)){app.phase='walk';app.playing=true;refresh();return;}
    if(app.n<=2){goWalk();return;}
    if(app.phase==='ready')app.phase='search';
    app.playing=true;refresh();
  }
  function samples() {app.manual=[null,null];app.referenceSide=null;app.phase='samples';app.sampleTime=0;app.clock=duration();app.playing=true;app.picked=null;app.highlight=null;refresh(true);}
  function pauseForEdit(side) {
    if(!valid(app.frames[side]?.assignment)){app.toast('Selecciona una muestra válida o termina el muestreo antes de editar.');return false;}
    app.playing=false;return true;
  }
  function swap(side,from,to) {
    if(from===to||!pauseForEdit(side))return;
    const a=app.frames[side].assignment.slice();const i=a.indexOf(from),k=a.indexOf(to);
    if(i<0||k<0)return;
    [a[i],a[k]]=[a[k],a[i]];app.manual[side]=a;if(app.referenceSide===side)app.referenceSide=null;app.phase='walk';configureWalk(true);app.playing=walkDuration()>0;app.picked=null;app.highlight=null;
    app.lastEditNonce=Date.now();refresh(true);app.send('edit',{n:app.n,side,assignment:a,cost:cost(a),nonce:app.lastEditNonce});
    app.toast(`Vuelos ${LETTERS[i]} y ${LETTERS[k]} intercambiados · costo ${cost(a)}`);
  }
  app.toast=function(text){$('toast').textContent=text;$('toast').hidden=false;clearTimeout(app.toastTimer);app.toastTimer=setTimeout(()=>{$('toast').hidden=true;},3000);};
  const handlers=[];
  function listen(el,type,handler){const wrapped=e=>{handler(e);app.last=performance.now();refresh();requestLoop();};el.addEventListener(type,wrapped);handlers.push(()=>el.removeEventListener(type,wrapped));}
  listen($('size'),'input',e=>{app.n=Number(e.target.value);if(app.n<=3)app.mode='mixers';else if(app.n>4)app.mode='lns';app.seed=defaultSeed();reset();});
  root.querySelectorAll('[data-size]').forEach(button=>listen(button,'click',()=>{app.n=Number(button.dataset.size);app.mode=app.n===4?'mixers':'lns';app.seed=defaultSeed();reset();}));
  listen($('mode'),'change',e=>{app.mode=e.target.value;if(app.mode==='mixers'&&app.n>4)app.n=4;app.seed=defaultSeed();reset();});
  listen($('seed'),'change',e=>{app.seed=Number(e.target.value);reset();});
  listen($('depth'),'change',e=>{app.depth=Number(e.target.value);reset();});
  listen($('speed'),'change',e=>{if(isWalking()||isSampling())app.travelSpeed=Number(e.target.value);else app.speed=Number(e.target.value);refresh();});
  listen($('play'),'click',play);listen($('restart'),'click',reset);listen($('restore'),'click',reset);listen($('walk'),'click',()=>goWalk(true));listen($('samples'),'click',samples);
  listen($('timeline'),'input',e=>{app.playing=false;app.highlight=null;const f=Number(e.target.value)/1000;if(isWalking()){app.walkTime=f*walkDuration();app.phase=f===1?'done':'walk';}else if(isSampling()){app.sampleTime=f*sampleDuration();app.phase=f===1?'sampledone':'samples';}else{app.phase='search';app.clock=f*duration();}refresh(true);});
  listen($('next'),'click',()=>{app.playing=false;if(isSampling()){const count=Math.max(1,app.runs[0]?.samples?.length||256);app.sampleTime=Math.min(sampleDuration(),app.sampleTime+sampleDuration()/count);if(app.sampleTime>=sampleDuration())app.phase='sampledone';refresh(true);return;}app.manual=[null,null];app.referenceSide=null;app.phase='search';const times=app.runs.flatMap(r=>(r?.events||[]).map(e=>Number(e.elapsed_s))).filter(t=>t>app.clock+1e-7);app.clock=times.length?Math.min(...times):duration();refresh(true);});
  listen($('show-optimum'),'click',()=>{app.manual=[null,null];app.walkCompare='optimum';app.referenceSide=0;goWalk();app.toast('Referencia exacta cargada: compara la distancia total, no solo la última llegada.');});
  listen($('walk-compare'),'change',e=>{app.walkCompare=e.target.value;app.manual=[null,null];app.referenceSide=app.walkCompare==='optimum'?0:null;goWalk(true);});
  listen($('walk-view'),'change',e=>{app.walkView=e.target.value;goWalk(true);});
  listen($('transfer'),'change',e=>{app.pairId=e.target.value;app.walkView='group';goWalk(true);});
  function stepTransfer(delta){const index=app.pairs.findIndex(p=>p.id===app.pairId);app.pairId=app.pairs[(index+delta+app.pairs.length)%app.pairs.length]?.id;app.walkView='group';goWalk(true);}
  listen($('prev-transfer'),'click',()=>stepTransfer(-1));listen($('next-transfer'),'click',()=>stepTransfer(1));
  listen($('evidence'),'click',()=>{renderEvidence();$('drawer').hidden=false;});listen($('close-evidence'),'click',()=>{$('drawer').hidden=true;});
  listen($('live'),'click',()=>{if(app.livePending)return;app.playing=false;app.livePending=true;app.toast(`Qiskit vuelve a calcular ambos mixers con p=${app.depth}. Puede tardar ${app.depth===3?'~20-60':'varios'} segundos.`);app.send('live',{n:app.n,seed:app.seed,depth:app.depth,nonce:Date.now()});refresh();});
  SIDES.forEach((s,side)=>{
    const svg=$('gates-'+s),map=$('map-'+s);let drag=null;
    listen(svg,'pointerdown',e=>{const gate=e.target.closest('[data-gate]');if(!gate)return;if(!pauseForEdit(side))return;drag={gate:Number(gate.dataset.gate),x:e.clientX,y:e.clientY};svg.setPointerCapture(e.pointerId);});
    listen(svg,'pointerup',e=>{if(!drag)return;const start=drag;drag=null;const point=new DOMPoint(e.clientX,e.clientY).matrixTransform(svg.getScreenCTM().inverse());const pts=coordinates();let nearest=0,best=Infinity;pts.forEach(([x,y],g)=>{const d=Math.hypot(point.x-x,point.y-y);if(d<best){nearest=g;best=d;}});const moved=Math.hypot(e.clientX-start.x,e.clientY-start.y)>6;if(moved&&best<70){swap(side,start.gate,nearest);return;}if(app.picked?.side===side&&app.picked.gate!==start.gate)swap(side,app.picked.gate,start.gate);else{app.picked={side,gate:start.gate};refresh(true);app.toast('Selecciona otra puerta para intercambiar sus vuelos.');}});
    listen(svg,'pointercancel',()=>{drag=null;});
    listen(svg,'keydown',e=>{if(!['Enter',' '].includes(e.key))return;const g=e.target.closest('[data-gate]');if(!g||!pauseForEdit(side))return;e.preventDefault();const gate=Number(g.dataset.gate);if(app.picked?.side===side&&app.picked.gate!==gate)swap(side,app.picked.gate,gate);else{app.picked={side,gate};refresh(true);}});
    listen(map,'click',e=>{if(e.target.closest('[data-gate]')||!['walk','done'].includes(app.phase))return;const p=new DOMPoint(e.clientX,e.clientY).matrixTransform(svg.getScreenCTM().inverse());const candidate=cohorts(side).find(person=>{const xy=point(person,app.walkTime);return Math.hypot(xy.x-p.x,xy.y-p.y)<13;});if(candidate){app.highlight={side,id:candidate.id};const speech=$('speech-'+s);speech.hidden=false;speech.innerHTML=`<strong>Viajero ${candidate.id+1}: ${LETTERS[candidate.i]} → ${LETTERS[candidate.k]}</strong>Puertas ${candidate.g+1} → ${candidate.h+1}<br>${candidate.d} unidades de distancia<br><small>Una figura representa una unidad de flujo del benchmark.</small>`;}});
  });
  function renderEvidence() {
    const I=instance(),row=I.stats;
    const runCards=app.runs.map((r,s)=>app.frames[s]?.baseline?`<div class="source-card"><strong>Terminal izquierda · asignación inicial</strong><p>Costo ${cost(app.frames[s].assignment)}. Es el punto de partida de la corrida derecha; no representa el resultado de otro algoritmo.</p></div>`:app.referenceSide===s?`<div class="source-card"><strong>Terminal izquierda · referencia exacta global</strong><p>Costo ${I.optimum}; tiempo medido ${sec(I.exact_seconds)}. Solución global certificada por ${I.reference_method==='branch_bound_gilmore_lawler'?'ramificación y poda (Gilmore–Lawler)':'enumeración completa'}, sin animación de pasos intermedios.</p></div>`:app.manual[s]?`<div class="source-card"><strong>Tu asignación · ${s?'derecha':'izquierda'}</strong><p>Costo ${cost(app.manual[s])}; exploración manual, sin nueva ejecución de algoritmos.</p></div>`:r?`<div class="source-card"><strong>${s?'Terminal derecha':'Terminal izquierda'} · ${esc(r.id)}</strong><p>Semilla ${r.seed}; tiempo ${sec(r.seconds)}; ${r.live?'calculada ahora':'corrida registrada'}. ${r.timing_scope==='optimizer_and_sampling'?'El tiempo cubre entrenamiento y muestreo.':''}</p><code>${esc(JSON.stringify(r.config))}</code>${r.kind==='qaoa'?`<p>P(óptimo): ${fmt(r.p_optimal*100)}%; factibilidad ideal: ${fmt(r.p_feasible*100)}%; muestras válidas: ${fmt(r.raw_feasible_fraction*100)}%.</p><p>Se visualizan ${r.samples?.length||0} shots reales de ${r.total_shots||r.config.shots}. La selección de una buena muestra no es su probabilidad de aparición.</p>${r.resources?.qubits?`<p>Circuito compilado p=${r.config.reps}: ${r.resources.qubits} qubits, ${r.resources.transpiled_two_qubit_gates} compuertas de dos qubits, profundidad ${r.resources.transpiled_depth}. Backend genérico; no ejecutado en hardware.</p>`:''}`:''}</div>`:'<div class="source-card">No hay traza para esta combinación.</div>').join('');
    const qn=app.n===3?3:4,qI=app.data.instances.find(x=>x.n===qn);
    const randomText=r=>r.p_optimal_random>=.001?`${fmt(100*r.p_optimal_random)}%`:`1 entre ${Math.round(1/r.p_optimal_random).toLocaleString('es-PE')}`;
    const ratio=v=>v<.1?v.toFixed(2):v.toFixed(1);
    const recorded=(app.data.studies?.qaoa_recorded||[]).filter(r=>r.n===qn).sort((a,b)=>(a.mixer===b.mixer?a.reps-b.reps:a.mixer==='x'?-1:1));
    const recordedRows=recorded.map(r=>{const used=r.p_optimal_by_seed.filter((_,i)=>!r.start_optimal_seeds.includes(i)).sort((a,b)=>a-b);const mid=used.length%2?used[(used.length-1)/2]:(used[used.length/2-1]+used[used.length/2])/2;const flag=used.length<r.p_optimal_by_seed.length?'†':'';return `<tr><td>${r.mixer==='x'?'Penalización (X)':'Intercambio'} · p=${r.reps}${flag}</td><td><strong>${fmt(100*mid)}%</strong></td><td>${fmt(100*used[0])}–${fmt(100*used[used.length-1])}%</td><td>${fmt(100*r.median_p_feasible)}%</td><td>${ratio(mid/r.random_p_optimal)}×</td></tr>`;}).join('');
    const startOpt=recorded.filter(r=>r.start_optimal_seeds.length).map(r=>`${r.mixer==='x'?'X':'intercambio'} p=${r.reps}: semillas ${r.start_optimal_seeds.join(', ')}`).join('; ');
    const METHODS={qaoa:'LNS + QAOA',exact:'LNS + exacto local (3 vuelos)',random:'LNS + azar',scipy_faq:'SciPy FAQ (heurística clásica)'};
    const ext=app.data.extension;
    const extRows=(ext?.summary||[]).map(r=>`<tr><td>${r.n}${r.n>10?'*':''}</td><td>${esc(METHODS[r.method]||r.method)}</td><td>${r.median_cost}</td><td>${r.best_cost}</td><td>${r.optimal_hits}/${r.runs}</td><td>+${fmt(r.median_gap_percent)}%</td><td>${sec(r.median_seconds)}</td><td>${fmt(r.median_peak_rss_bytes/2**20)} MiB</td></tr>`).join('');
    const certRows=(ext?.rows||[]).map(r=>`<tr><td>${r.n}</td><td>${r.optimum}</td><td>${r.reference_lower_bound}</td><td>${r.optimal_assignments}</td><td>${sec(r.exact_seconds)}</td><td>${fmt(r.exact_peak_rss_bytes/2**20)} MiB</td></tr>`).join('');
    const extensionEvidence=ext?.complete?`<h3>Final: N=10…14 · comparación nueva y emparejada</h3><p>Cinco semillas (0…4), K=3, 60 iteraciones, p=2, 512 shots y hasta 60 evaluaciones por subproblema. Entrenamiento clásico en el subespacio factible de seis estados; distribución verificada en el circuito completo de Aer y muestreo Qiskit en cada llamada. Los tres LNS comparten inicio y secuencia de vecindarios por semilla. El óptimo solo se consulta para evaluar; no se usa como inicio. *N&gt;10: ampliación sintética, con datos congelados antes de medir.</p><table><thead><tr><th>N</th><th>Método</th><th>Mediana</th><th>Mejor</th><th>Óptimo</th><th>Brecha</th><th>Tiempo mediano</th><th>RSS mediana</th></tr></thead><tbody>${extRows}</tbody></table><p>Todas las asignaciones medidas son válidas. Se compara un presupuesto de iteraciones; los tiempos son distintos. RSS es la memoria del proceso del simulador (incluye Python y librerías), con intervalo de muestreo solicitado de 5 ms; puede omitir picos muy breves. Los archivos por corrida conservan memoria inicial, incremento, CPU, versiones y semillas.</p><h3>Certificados del óptimo global</h3><table><thead><tr><th>N</th><th>Mejor costo</th><th>Cota inferior final</th><th>Nº de óptimos</th><th>Tiempo exacto</th><th>RSS pico</th></tr></thead><tbody>${certRows}</tbody></table><p>Ramificación y poda con cota Gilmore–Lawler y asignación lineal exacta de SciPy. Se certifica cuando la búsqueda completa descarta cualquier mejora y la cota final coincide con el costo. En N=10 también se coteja con la enumeración histórica (340); N=3/4 se validan por enumeración. No se recorren las 14! permutaciones. Resultados y reproducción: <code>python scaling14_study.py</code>, <code>results/scaling14.json</code>, <code>docs/scaling14_results.md</code>.</p>`:'';
    const historical10=app.data.scaling.rows.find(x=>x.n===10);
    const I10={optimum:historical10.optimum,exact_seconds:historical10.exact_seconds};
    const scalingRows=app.data.instances.map(x=>`<tr><td>${x.n}</td><td>${x.optimum}</td><td>${sec(x.exact_seconds)}</td><td>${x.stats.lns_exact_median??'—'}</td><td>${x.stats.lns_qaoa_median??'—'}</td></tr>`).join('');
    $('evidence-body').innerHTML=`<h3>Cómo interpretar la animación</h3><p>Antes → resultado compara el punto de partida con el mejor plan del híbrido. «Los dos algoritmos» reproduce la comparación de resultados. Una conexión muestra solo sus figuras; el costo superior siempre incluye todos los flujos. Las tres conexiones clave se ordenan por cambio absoluto del aporte F×D, incluyendo empeoramientos. En «Todos los flujos», la distancia acumulada al finalizar coincide exactamente con el costo QAP.</p><p>Las dos terminales comparten velocidad y pauta de salida. La cámara de una conexión usa la misma escala en ambos lados. Terminar antes un grupo no implica menor costo global: se evalúa la suma de distancias ponderadas, no solo la última llegada.</p><h3>Lo que se representa</h3><p>${I.synthetic?'N='+app.n+' es una ampliación sintética reproducible (semilla 20261025). Preserva íntegro QAP10; añade flujos muestreados de sus 45 pares y continúa la misma cuadrícula. No pertenece al benchmark oficial.':'N≤10 utiliza las matrices originales de QAP10.'}</p><p>La aplicación interpreta QAP10 como vuelos y puertas. El dibujo utiliza la geometría exacta de D: una cuadrícula de cuatro columnas, con distancia Manhattan multiplicada por dos. Las primeras N filas y columnas definen cada subinstancia.</p><p>Una figura representa una unidad de flujo. El costo es <code>Σ F[i,k] × D[puerta_i,puerta_k], i&lt;k</code>. Cada par se cuenta una sola vez. Las emociones y los segundos de movimiento son recursos visuales; no se midieron pasajeros, metros, demoras ni satisfacción de un aeropuerto real.</p><h3>Referencia exacta de N=${app.n}</h3><p><span class="key-number">${I.optimum}</span> · ${row.optimal_assignments} óptimas de ${row.assignments.toLocaleString('es-PE')} permutaciones. Azar válido: ${randomText(row)}.</p><h3>Corridas animadas</h3>${runCards}<p>En el híbrido se muestran asignaciones actuales, incluida la exploración después de una patada. Las personas salen con la mejor asignación encontrada. En QAOA directo los pasos del optimizador son energías esperadas; no son planes de puertas. Los cambios del plano durante el muestreo son shots leídos de la ejecución.</p><h3>QAOA directo · N=${qn} · cinco semillas por configuración</h3><p>Son las mismas corridas que se animan (α=1, hasta 100 evaluaciones, 2048 shots, Aer ideal). Azar válido: ${fmt(100*qI.stats.p_optimal_random)}% de P(óptimo). "Mejor shot válido" no sirve para comparar: con 2048 shots casi cualquier muestreo encuentra el óptimo; cuentan P(óptimo) y el % de shots válidos.</p><table><thead><tr><th>Configuración</th><th>P(óptimo)<br>mediana</th><th>Rango<br>por semilla</th><th>Shots válidos<br>mediana</th><th>vs. azar</th></tr></thead><tbody>${recordedRows}</tbody></table><p>p=3 es la configuración más estable de las probadas: el rango por semilla de la tabla muestra que las cinco superan al azar. Es una sola instancia y cinco semillas; no se garantiza en otras. Con p=2 el intercambio depende de la semilla: algunas se quedan en el estado inicial y otras aciertan el 100%. La penalización (X) no supera al azar en ninguna de las dos profundidades probadas. ${startOpt?`† Se excluyen las semillas que arrancaron ya en el óptimo, porque no demuestran nada (${startOpt}).`:''} No se ha demostrado ventaja cuántica.</p><h3>Escalamiento · ${ext?.complete?'N≤9: tres semillas; N≥10: cinco semillas':'tres semillas'}; 60 iteraciones</h3><table><thead><tr><th>N</th><th>Óptimo</th><th>Exacto</th><th>LNS clásico<br>mediana</th><th>LNS QAOA<br>mediana</th></tr></thead><tbody>${scalingRows}</tbody></table>${extensionEvidence}<h3>Estudio de N=10 · cinco semillas, 150 iteraciones</h3><p>Mediana del mejor costo de 5 semillas por método. Todas las asignaciones son válidas y ninguna corrida llegó a 340. Las medianas 368–380 describen estas corridas; cinco semillas no bastan para afirmar superioridad general ni ausencia de diferencias.</p><table><thead><tr><th>Método</th><th>Mediana</th><th>Mejor</th><th>Brecha<br>mediana</th><th>Tiempo<br>mediano</th></tr></thead><tbody><tr><td><strong>Enumeración exacta (referencia)</strong></td><td>${I10.optimum}</td><td>${I10.optimum}</td><td>0%</td><td>${sec(I10.exact_seconds)}</td></tr>${app.data.legacy.map(r=>`<tr><td>${esc(METHODS[r.method]||r.method)}</td><td>${r.median_cost}</td><td>${r.best_cost}</td><td>+${fmt(r.median_gap_percent)}%</td><td>${sec(r.median_seconds)}</td></tr>`).join('')}</tbody></table><h3>Reproducir y continuar</h3><p><code>python tools/export_visual_demo.py</code> genera trazas; <code>streamlit run app/app.py</code> abre esta app. Aer statevector ideal, sin ruido. Qiskit construye/simula circuitos; COBYLA y la búsqueda externa son clásicos.</p><p>${ext?.complete?'La ampliación N=11…14 ya tiene mediciones de tiempo, memoria, calidad y factibilidad en esta demo. Usa N=14 y abre la referencia óptima para comparar sus conexiones con el híbrido.':'El selector muestra las instancias con mediciones disponibles.'} Una aplicación operativa necesitaría horarios, compatibilidad de aeronaves, conexiones reales y distancias caminables.</p><p><a href="https://miplib.zib.de/instance_details_qap10.html" target="_blank" rel="noreferrer">Fuente del benchmark: MIPLIB QAP10 ↗</a></p>`;
  }
  function tick(now) {
    app.raf=0;
    if(app.destroyed)return;
    // Include time spent rendering the previous frame. Capping the increment
    // or resetting it on every scheduled frame makes slow devices play slower.
    // User input reanchors the clock, so paused time is never accumulated.
    const dt=Math.max(0,(now-(app.last||now))/1000);app.last=now;
    if(app.playing) {
      if(app.phase==='search') {app.clock=Math.min(duration(),app.clock+dt*app.speed);if(app.clock>=duration()){if(app.mode==='mixers')samples();else goWalk();}}
      else if(app.phase==='samples'){app.sampleTime=Math.min(sampleDuration(),app.sampleTime+dt*app.travelSpeed);if(app.sampleTime>=sampleDuration()){app.phase='sampledone';app.playing=false;refresh(true);}}
      else if(app.phase==='walk'){
        const end=walkDuration();app.walkTime=Math.min(end,app.walkTime+dt*app.travelSpeed);
        if(app.walkTime>=end){
          if(app.walkView==='tour'&&app.tourIndex+1<app.tourIds.length){app.tourIndex++;app.pairId=app.tourIds[app.tourIndex];app.peopleCache=[null,null];app.walkTime=0;app.highlight=null;refresh(true);}
          else{app.phase='done';app.playing=false;refresh(true);}
        }
      }
    }
    if(now-app.lastUI>100){refresh();app.lastUI=now;}
    else{drawPeople(0);drawPeople(1);}
    if(app.playing)requestLoop();
  }
  function requestLoop(){if(!app.destroyed&&app.playing&&!app.raf)app.raf=requestAnimationFrame(tick);}
  const resizeObserver=new ResizeObserver(()=>{if(!app.destroyed){drawPeople(0);drawPeople(1);}});resizeObserver.observe(root);
  app.cleanup=()=>{app.destroyed=true;cancelAnimationFrame(app.raf);clearTimeout(app.toastTimer);resizeObserver.disconnect();handlers.forEach(f=>f());instances.delete(parentElement);};
  chooseRuns();refresh(true);
  return app.cleanup;
}
"""

_ASSET_VERSION = sha256((HTML + CSS + JS).encode("utf-8")).hexdigest()[:10]
_LAB = st.components.v2.component(f"airport_visual_lab_{_ASSET_VERSION}", html=HTML, css=CSS, js=JS)


def airport_lab(catalog, *, key, on_edit_change, on_live_change):
    """Mount the simulation; callbacks validate edits and request actual QAOA runs."""
    return _LAB(
        data=catalog, key=key, width="stretch", height="content",
        on_edit_change=on_edit_change, on_live_change=on_live_change,
    )
