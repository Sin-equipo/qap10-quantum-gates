"""Browser-side airport renderer. CCv2 keeps animation off the Python rerun loop."""

from hashlib import sha256

import streamlit as st

HTML = r"""
<main id="lab" class="lab">
  <header class="masthead">
    <div class="brand"><span class="brand-icon">↗</span><div><h1>Misión conexiones<span class="brand-period">.</span></h1><p>Un aeropuerto. Millones de decisiones.</p></div></div>
    <div class="head-right"><span class="small-tag"><i></i> LABORATORIO QAP10</span><button id="evidence" class="quiet" aria-label="Abrir evidencia y metodología">Evidencia <span>↗</span></button></div>
  </header>
  <nav class="toolbar" aria-label="Controles del experimento">
    <div class="size-control"><span class="eyebrow">VUELOS / PUERTAS</span><div><strong id="n-label">10</strong><input id="size" aria-label="Número de vuelos y puertas" type="range" min="1" max="10" value="10"><button data-size="4" class="preset">N=4</button><button data-size="10" class="preset active">N=10</button></div></div>
    <span class="toolbar-rule"></span>
    <label class="experiment-label"><span class="eyebrow">EXPERIMENTO</span><select id="mode" aria-label="Comparación de algoritmos"><option value="lns">Clásico vs. híbrido QAOA</option><option value="mixers">QAOA: penalización vs. intercambio</option></select></label>
    <label class="seed-label"><span class="eyebrow">SEMILLA</span><select id="seed" aria-label="Semilla de la corrida"><option>0</option><option>1</option><option>2</option><option>3</option><option>4</option></select></label>
    <button class="reference-pill" id="show-optimum" title="Mostrar la asignación exacta en la terminal izquierda"><span class="eyebrow">ÓPTIMO EXACTO ↗</span><strong id="reference">340</strong><small id="exact-time">2,6 s · 10! opciones</small></button>
  </nav>
  <section class="phase-line"><div class="phase-steps"><span id="step-search" class="phase-step selected"><b>1</b> Buscar asignación</span><span class="phase-dash"></span><span id="step-walk" class="phase-step"><b>2</b> Ver las conexiones</span></div><span id="phase-message" class="phase-message">Mismo inicio. Mismos vecindarios. Distinto subsolver.</span></section>
  <section class="arena" aria-label="Comparación visual de dos aeropuertos">
    <article class="terminal terminal-left" data-side="0">
      <div class="terminal-head"><div><span class="eyebrow method-label" id="method-left">BÚSQUEDA CLÁSICA</span><h2 id="title-left">LNS + exacto</h2></div><span id="status-left" class="status">En espera</span></div>
      <div class="metrics"><div><small>Costo actual</small><strong id="cost-left">—</strong></div><div><small>Mejor encontrado</small><strong id="best-left">—</strong></div><div class="time-metric"><small>Cálculo medido</small><strong id="time-left">—</strong></div><span id="gap-left" class="gap">—</span></div>
      <div class="map" id="map-left"><canvas id="canvas-left" aria-label="Pasajeros y pasillos de la terminal izquierda"></canvas><svg id="gates-left" viewBox="0 0 600 330" role="group" aria-label="Puertas de la terminal izquierda, selecciona dos para intercambiar vuelos"></svg><div class="speech" id="speech-left" hidden></div></div>
      <div class="terminal-foot"><span id="detail-left">60 iteraciones · K=3</span><span id="arrivals-left">↔ Arrastra o selecciona dos puertas</span></div>
    </article>
    <article class="terminal terminal-right" data-side="1">
      <div class="terminal-head"><div><span class="eyebrow method-label" id="method-right">BÚSQUEDA HÍBRIDA</span><h2 id="title-right">LNS + QAOA</h2></div><span id="status-right" class="status">En espera</span></div>
      <div class="metrics"><div><small>Costo actual</small><strong id="cost-right">—</strong></div><div><small>Mejor encontrado</small><strong id="best-right">—</strong></div><div class="time-metric"><small>Cálculo medido</small><strong id="time-right">—</strong></div><span id="gap-right" class="gap">—</span></div>
      <div class="map" id="map-right"><canvas id="canvas-right" aria-label="Pasajeros y pasillos de la terminal derecha"></canvas><svg id="gates-right" viewBox="0 0 600 330" role="group" aria-label="Puertas de la terminal derecha, selecciona dos para intercambiar vuelos"></svg><div class="speech" id="speech-right" hidden></div></div>
      <div class="terminal-foot"><span id="detail-right">60 iteraciones · 9 qubits por llamada</span><span id="arrivals-right">↔ Arrastra o selecciona dos puertas</span></div>
    </article>
  </section>
  <section class="insight-strip"><span class="insight-icon">↳</span><p id="insight">¿Un buen subsolver garantiza una buena asignación global? Reproduce el duelo y observa.</p><button id="restore" class="text-button" hidden>Restaurar duelo ↺</button></section>
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
.reference-pill{background:transparent;border-top:0;border-right:0;border-bottom:0;text-align:left;border-radius:0}.reference-pill:hover{background:#e0e8da}
"""

JS = r"""
const instances = new WeakMap();
const BLUE = '#4d7fbb', TEAL = '#1b9380', INK = '#294b5c';
const LETTERS = 'ABCDEFGHIJ';
const SIDES = ['left','right'];
const FLIGHT_COLORS = ['#347da2','#d48b40','#458f7a','#9a7597','#b76b51','#687fb0','#a79849','#598e95','#ab6983','#709557'];
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
  app = {data, send:setTriggerValue, n:10, mode:'lns', seed:0, speed:10,
    phase:'ready', clock:0, walkTime:0, sampleTime:0, playing:false,
    manual:[null,null], referenceSide:null, picked:null, highlight:null, frames:[null,null],
    runs:[null,null], raf:0, last:0, lastUI:0, lastMap:['',''], toastUntil:0,
    liveDone:data.live_completed, livePending:false, destroyed:false};
  instances.set(parentElement,app);

  function instance() {return app.data.instances.find(x=>x.n===app.n);}
  function cost(a) {if(!a || a.length!==app.n || new Set(a).size!==app.n || a.some(x=>x<0||x>=app.n)) return null;let c=0;const I=instance();for(let i=0;i<app.n;i++)for(let k=i+1;k<app.n;k++)c+=I.flows[i][k]*I.distances[a[i]][a[k]];return c;}
  function valid(a) {return cost(a)!==null;}
  function duration() {return Math.max(.000001,...app.runs.filter(Boolean).map(r=>Number(r.seconds||0)));}
  function coordinates() {
    const rows = Math.ceil(app.n/4), cols=Math.min(app.n,4);
    const unit=Math.min(138, (600-155)/Math.max(1,cols-1), (330-125)/Math.max(1,rows-1));
    const x0=(600-(cols-1)*unit)/2, y0=(330-(rows-1)*unit)/2;
    return instance().coordinates.map(([x,y])=>[x0+x*unit,y0+y*unit]);
  }
  function chooseRuns() {
    const kind=app.mode==='lns'?'lns':'qaoa';
    const methods=kind==='lns'?['exact','qaoa']:['x','perm'];
    app.runs=methods.map(method=>app.data.runs.filter(r=>r.n===app.n && r.kind===kind && r.method===method && Number(r.seed)===app.seed && (kind==='lns'||Number(r.config?.reps ?? r.reps ?? 2)===2)).at(-1)||null);
  }
  function reset() {
    app.playing=false;app.phase='ready';app.clock=0;app.walkTime=0;app.sampleTime=0;
    app.manual=[null,null];app.referenceSide=null;app.picked=null;app.highlight=null;app.lastMap=['',''];
    SIDES.forEach(s=>$("speech-"+s).hidden=true);
    chooseRuns();refresh(true);
  }
  function frame(run,side) {
    const I=instance();
    if(app.manual[side]) {const a=app.manual[side];return {assignment:a,cost:cost(a),best_cost:cost(a),manual:true,reference:app.referenceSide===side,event:'manual'};}
    if(app.n<=2) return {assignment:I.exact_assignment,cost:I.optimum,best_cost:I.optimum,elapsed_s:0,event:'trivial'};
    if(!run) {const a=Array.from({length:app.n},(_,i)=>i);return {assignment:a,cost:cost(a),best_cost:null,missing:true,event:'missing'};}
    if(app.mode==='mixers') {
      if(app.phase==='samples') {
        const samples=run.samples||[];const index=Math.min(samples.length-1,Math.floor(app.sampleTime/8*samples.length));
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
    if(f.reference)return ['Referencia exacta','good'];
    if(f.manual)return ['Tu asignación','manual'];
    if(app.n<=2)return ['Óptimo trivial','good'];
    if(f.missing)return ['Traza no disponible','bad'];
    if(app.phase==='ready')return ['En espera',''];
    if(f.invalid)return ['Muestra inválida','bad'];
    if(f.event==='sample')return ['Muestra válida','good'];
    if(f.training)return [app.clock>=r.seconds?'Entrenamiento listo':'Entrenando QAOA',app.clock>=r.seconds?'good':'working'];
    if(app.phase==='walk'||app.phase==='done')return [f.cost===instance().optimum?'Óptimo encontrado':'Mejor de esta corrida',f.cost===instance().optimum?'good':''];
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
    root.querySelectorAll('[data-size]').forEach(b=>b.classList.toggle('active',Number(b.dataset.size)===app.n));
    $('mode').value=app.mode;$('mode').disabled=app.n<=3;
    $('seed').value=app.seed;$('seed').disabled=app.mode==='lns'||app.n<=2;
    $('reference').textContent=I.optimum;
    $('exact-time').textContent=`${sec(I.exact_seconds)} · ${Number(I.stats.assignments).toLocaleString('es-PE')} opciones`;
    $('live').hidden=app.mode!=='mixers'||app.n<3;
    $('live').disabled=app.livePending;
    $('live').textContent=app.livePending?'Qiskit está calculando…':'Ejecutar Qiskit ahora ↗';
    $('samples').hidden=app.mode!=='mixers'||app.n<=2;
    $('walk').textContent=app.phase==='walk'?'Otra oleada ↗':'Ver pasajeros ↗';
    const missing=app.n>2&&app.runs.some(r=>!r);
    $('play').disabled=missing;
    $('next').disabled=missing||app.n<=2||(app.mode==='mixers'&&app.phase!=='samples');
    $('samples').disabled=missing;
    $('play').innerHTML=app.playing?'<span>Ⅱ</span> Pausar':app.phase==='ready'?'<span>▶</span> Reproducir duelo':'<span>▶</span> Continuar';
    $('restore').hidden=!app.manual.some(Boolean);
    $('step-search').classList.toggle('selected',!['walk','done'].includes(app.phase));
    $('step-walk').classList.toggle('selected',['walk','done'].includes(app.phase));
    $('phase-message').textContent=app.manual.some(Boolean)?'Exploración manual · tu costo se calcula al instante':app.phase==='samples'?'Shots reales, en orden de lectura · se muestran hasta 256':app.phase==='walk'||app.phase==='done'?'Mismos flujos · se usa la mejor asignación válida de cada corrida':app.mode==='lns'?'Mismo inicio. Mismos vecindarios. Distinto subsolver.':'Mismo problema · distinta forma de imponer las restricciones';
    for(let side=0;side<2;side++) {
      const s=SIDES[side],r=app.runs[side],f=app.frames[side];
      const names=app.mode==='lns'?['LNS + exacto','LNS + QAOA']:['QAOA con penalización','QAOA de intercambio'];
      $('title-'+s).textContent=f.reference?'Referencia exacta':f.manual?'Tu asignación':app.n<=2?'Todas son óptimas':names[side];
      $('method-'+s).textContent=f.reference?'ENUMERACIÓN COMPLETA · RESULTADO GUARDADO':f.manual?'EXPLORACIÓN MANUAL':app.n<=2?'CASO INTRODUCTORIO':app.mode==='lns'?(side?'BÚSQUEDA HÍBRIDA':'BÚSQUEDA CLÁSICA'):(side?'MIXER DE INTERCAMBIO · P=2':'MIXER X · P=2');
      const [label,cls]=statusLabel(f,r);$('status-'+s).textContent=label;$('status-'+s).className='status '+cls;
      $('cost-'+s).textContent=f.cost==null?'—':f.cost;
      $('best-'+s).textContent=f.best_cost==null?'—':f.best_cost;
      const elapsed=app.phase==='ready'?0:Math.min(app.clock,Number(r?.seconds||0));
      $('time-'+s).textContent=f.reference?sec(I.exact_seconds):f.manual?'—':r?sec(['walk','done','samples'].includes(app.phase)?r.seconds:elapsed):app.n<=2?sec(I.exact_seconds):'—';
      root.querySelector('.terminal-'+s+' .metrics>div:nth-child(2) small').textContent=app.mode==='mixers'&&!f.manual?`Mejor de ${r?.total_shots??2048} shots`:'Mejor encontrado';
      const gap=f.cost!=null&&I.optimum>0?100*(f.cost-I.optimum)/I.optimum:0;
      $('gap-'+s).textContent=f.cost==null?'Sin plan':gap===0?'Óptimo':`+${fmt(gap)}%`;
      $('gap-'+s).className='gap '+(f.cost===I.optimum?'optimal':'');
      if(f.reference)$('detail-'+s).textContent='Óptimo por enumeración global · sin traza de pasos intermedios';
      else if(f.manual)$('detail-'+s).textContent=app.data.validation?.ok&&app.data.validation.nonce===app.lastEditNonce?'Costo verificado por Python · cada par una vez':'Costo QAP local · comprobando con Python';
      else if(app.n<=2)$('detail-'+s).textContent=app.n===1?'Una asignación · sin conexiones':'Dos asignaciones · ambas cuestan 10';
      else if(f.missing)$('detail-'+s).textContent='Resultado agregado en Evidencia; no hay pasos para reproducir';
      else if(app.mode==='mixers')$('detail-'+s).textContent=`P(óptimo) ${fmt(100*r.p_optimal)}% · válidas ${fmt(100*r.p_feasible)}% · semilla ${app.seed}`;
      else $('detail-'+s).textContent=`${r?.config?.iterations??60} iter. · K=${r?.config?.k??3} · semilla ${app.seed}${side?' · 9 qubits':''}${f.step?' · paso '+f.step:''}`;
      drawGates(side,force);
    }
    const runMax=duration();
    $('clock-label').textContent=app.phase==='walk'||app.phase==='done'?`${fmt(app.walkTime)} s visuales`:app.phase==='samples'?`Shot ${(app.frames[0]?.sampleIndex??0)+1}`:sec(app.clock);
    $('duration-label').textContent=app.phase==='walk'||app.phase==='done'?'8 s ilustrativos':app.phase==='samples'?'muestras registradas':`${sec(runMax)} medidos`;
    if(document.activeElement!==$('timeline'))$('timeline').value=Math.min(1000,Math.round(app.phase==='walk'||app.phase==='done'?app.walkTime/8*1000:app.phase==='samples'?app.sampleTime/8*1000:app.clock/runMax*1000));
    $('speed').value=app.speed;
    $('chart-title').textContent=app.manual.some(Boolean)?'Curvas de las corridas originales':app.mode==='lns'?'Costo por iteración · sólido = mejor':'Energía QUBO por evaluación · no es costo';
    $('legend-left').textContent=app.mode==='lns'?'LNS clásico':'Mixer X';
    $('legend-right').textContent=app.mode==='lns'?'LNS QAOA':'Intercambio';
    $('provenance').textContent=app.runs.some(r=>r?.live)?'Aer ideal · corrida calculada en esta sesión · sin hardware cuántico':'Aer ideal · reproducción de corridas registradas · sin hardware cuántico';
    insight();drawChart();
  }
  app.refresh=refresh;
  function insight() {
    const I=instance();let text;
    if(app.referenceSide!==null)text=`Así se ve el óptimo global ${I.optimum}, obtenido por enumeración en ${sec(I.exact_seconds)}. Compara sus recorridos con la mejor asignación del algoritmo.`;
    else if(app.manual.some(Boolean))text='Tu turno: intercambia vuelos y observa qué conexiones recorren más distancia. El duelo original se puede restaurar.';
    else if(app.n<=2)text=app.n===1?'Una puerta y un vuelo: no hay decisión que optimizar. Sube N para que aparezca el problema.':'Aquí las dos permutaciones cuestan lo mismo: todas son óptimas. Encontrar el óptimo todavía no demuestra habilidad.';
    else if(app.runs.some(r=>!r))text='Esta combinación aún no tiene una traza registrada. Puedes explorar asignaciones manuales o consultar los resultados en Evidencia.';
    else if(app.phase==='samples')text='Una muestra inválida puede dejar vuelos sin puerta o asignar varios a la misma. El mixer de intercambio conserva la regla uno a uno.';
    else if(app.mode==='mixers')text=`N=${app.n}: el azar entre permutaciones válidas tiene ${fmt(100*I.stats.p_optimal_random)}% de probabilidad de óptimo. La corrida mostrada es una semilla, no la mediana.`;
    else if(['walk','done'].includes(app.phase)) {
      const a=cost(app.runs[0].final_assignment),b=cost(app.runs[1].final_assignment);
      text=a===b?`En esta semilla ambos terminaron en ${a}. Compara también el tiempo medido; la calidad final por sí sola no cuenta toda la historia.`:`En esta semilla: clásico ${a}, híbrido ${b}; óptimo global ${I.optimum}. Los personajes representan el costo de conexiones de cada asignación.`;
    } else text='¿Resolver bien un vecindario garantiza una buena solución global? Observa las mesetas, los cambios y las patadas de exploración.';
    $('insight').textContent=text;
  }
  function drawGates(side,force=false) {
    const f=app.frames[side],pts=coordinates();
    const released=(app.phase==='search'&&f.flights)||[];
    const marker=JSON.stringify([f.assignment,f.matrix,f.invalid,released,app.picked,app.mode]);
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
    const f=app.frames[side];if(!valid(f.assignment))return [];
    const I=instance(),pts=coordinates(),people=[];let id=0;
    const maxD=Math.max(1,...I.distances.flat());
    for(let i=0;i<app.n;i++)for(let k=i+1;k<app.n;k++)for(let q=0;q<I.flows[i][k];q++) {
      const g=f.assignment[i],h=f.assignment[k],d=I.distances[g][h];
      people.push({id:id++,i,k,g,h,d,a:pts[g],b:pts[h],delay:((i*19+k*7+q*11)%17)/17*1.25,jitter:((q%5)-2)*3.2,mood:d/maxD>2/3?2:d/maxD>1/3?1:0});
    }return people;
  }
  function point(person,t) {
    const duration=person.d*.55;
    const f=Math.max(0,Math.min(1,(t-person.delay)/Math.max(.1,duration)));
    const [ax,ay]=person.a,[bx,by]=person.b;
    const h=Math.abs(bx-ax),v=Math.abs(by-ay),distance=(h+v)*f;
    const x=distance<=h?ax+Math.sign(bx-ax)*distance:bx;
    const y=distance<=h?ay:ay+Math.sign(by-ay)*(distance-h);
    return {x:x+person.jitter,y:y+23+((person.id%3)-1)*3.2,f,waiting:t<person.delay};
  }
  function rounded(ctx,x,y,w,h,r,fill) {ctx.beginPath();ctx.roundRect(x,y,w,h,r);ctx.fillStyle=fill;ctx.fill();}
  function avatar(ctx,x,y,id,mood,t,arrived=false) {
    const bob=arrived?0:Math.sin(t*14+id)*.8;
    const color=['#397f9f','#c69341','#bc6c50'][mood];
    ctx.save();ctx.translate(x,y+bob);
    ctx.fillStyle='#29492e1a';ctx.beginPath();ctx.ellipse(0,7,4.8,1.8,0,0,Math.PI*2);ctx.fill();
    ctx.strokeStyle='#3f5260';ctx.lineWidth=1.3;ctx.beginPath();ctx.moveTo(-1.5,3);ctx.lineTo(-2.5+Math.sin(t*12+id),6.5);ctx.moveTo(1.5,3);ctx.lineTo(2.5-Math.sin(t*12+id),6.5);ctx.stroke();
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
    const links=[];for(let g=0;g<app.n;g++){if(g%4<3&&g+1<app.n)links.push([g,g+1]);if(g+4<app.n)links.push([g,g+4]);}
    ctx.lineCap='round';for(const [a,b] of links){ctx.beginPath();ctx.moveTo(pts[a][0],pts[a][1]+23);ctx.lineTo(pts[b][0],pts[b][1]+23);ctx.lineWidth=24;ctx.strokeStyle='#e5ecdf';ctx.stroke();ctx.lineWidth=1;ctx.strokeStyle='#fcfdf9';ctx.setLineDash([3,5]);ctx.stroke();ctx.setLineDash([]);}
    ctx.font='8px "Segoe UI", sans-serif';ctx.fillStyle='#9aa58f';ctx.fillText('TERMINAL DE CONEXIONES',19,19);ctx.fillText('ESQUEMA DEL BENCHMARK · PASILLOS MANHATTAN',19,320);
    for(const [x,y] of [[35,62],[560,82],[45,255],[552,248]]){rounded(ctx,x-6,y,12,10,3,'#c1c7a9');for(let j=0;j<4;j++){ctx.fillStyle=j%2?'#83a874':'#9bb985';ctx.beginPath();ctx.ellipse(x+(j%2?3:-3),y-2-j*1.3,4,7,j*.9,0,Math.PI*2);ctx.fill();}}
    for(const [x,y] of [[40,160],[545,160]]){rounded(ctx,x,y,18,6,2,'#aebea5');rounded(ctx,x+2,y+7,2,3,1,'#8f9e88');rounded(ctx,x+14,y+7,2,3,1,'#8f9e88');}
  }
  function drawPeople(side) {
    const canvas=$('canvas-'+SIDES[side]),rect=canvas.getBoundingClientRect();if(rect.width<1||rect.height<1)return;
    const ratio=Math.min(2,window.devicePixelRatio||1);const w=Math.round(rect.width*ratio),h=Math.round(rect.height*ratio);
    if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;}
    const ctx=canvas.getContext('2d');ctx.setTransform(1,0,0,1,0,0);ctx.clearRect(0,0,w,h);
    const scale=Math.min(rect.width/600,rect.height/330),ox=(rect.width-600*scale)/2,oy=(rect.height-330*scale)/2;
    ctx.setTransform(scale*ratio,0,0,scale*ratio,ox*ratio,oy*ratio);
    const pts=coordinates();drawFloor(ctx,pts);
    const f=app.frames[side];if(!f)return;
    const walking=app.phase==='walk'||app.phase==='done';
    const people=cohorts(side);let arrived=0;
    if(walking||app.manual[side]) {
      for(const p of people) {
        const pos=point(p,app.walkTime);if(pos.f>=1)arrived++;
        if(pos.waiting)continue;
        if(app.highlight?.side===side&&app.highlight.id===p.id){ctx.beginPath();ctx.moveTo(p.a[0],p.a[1]+23);ctx.lineTo(p.b[0],p.a[1]+23);ctx.lineTo(p.b[0],p.b[1]+23);ctx.strokeStyle='#d49736';ctx.lineWidth=2;ctx.stroke();}
        avatar(ctx,pos.x,pos.y,p.id,p.mood,app.walkTime,pos.f>=1);
      }
    } else if(f.invalid || f.training&&app.mode==='mixers') {
      for(let i=0;i<Math.min(12,app.n*2);i++)avatar(ctx,238+(i%6)*17,280+Math.floor(i/6)*15,i,2,app.sampleTime,true);
      ctx.font='9px "Segoe UI",sans-serif';ctx.fillStyle='#a27355';ctx.fillText(f.invalid?'Esperando una asignación válida…':'Se entrena una distribución, todavía no es una asignación.',180,255);
    }
    const total=people.length;
    if(walking||app.manual[side])$('arrivals-'+SIDES[side]).textContent=`${arrived}/${total} llegadas · ${people.filter(p=>p.mood===2).length} trayectos largos`;
    else if(app.phase==='samples')$('arrivals-'+SIDES[side]).textContent=`Shot ${(f.sampleIndex??0)+1} · ${f.invalid?'hay conflictos':'permutación válida'}`;
    else $('arrivals-'+SIDES[side]).textContent=app.playing?'Pausa para intercambiar vuelos':'↔ Arrastra o selecciona dos puertas';
    if(walking&&app.walkTime>2.2&&app.walkTime<5.5&&!app.highlight){const p=people.find(p=>p.mood===2&&p.id%7===0);if(p){const speech=$('speech-'+SIDES[side]);speech.hidden=false;speech.innerHTML=`<strong>Vuelo ${LETTERS[p.i]} → ${LETTERS[p.k]}</strong>${side?'«¿No había una puerta más cerca?»':'«Mi maleta y yo necesitábamos hacer ejercicio…»'}<br><small>${p.d} unidades de distancia · emoción ilustrativa</small>`;}}
    else if(!app.highlight)$('speech-'+SIDES[side]).hidden=true;
  }
  function goWalk() {
    if(app.n>2&&app.runs.some(r=>!r)&&!app.manual.some(Boolean)){app.toast('Falta la traza de este tamaño. Puedes intercambiar vuelos en modo manual.');return;}
    app.phase='walk';app.clock=duration();app.walkTime=0;app.playing=true;app.picked=null;app.highlight=null;refresh(true);
  }
  function play() {
    if(app.playing){app.playing=false;refresh();return;}
    if(app.manual.some(Boolean)){app.phase='walk';if(app.walkTime>=8)app.walkTime=0;app.playing=true;refresh();return;}
    if(app.n<=2){goWalk();return;}
    if(app.phase==='done'){reset();}
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
    [a[i],a[k]]=[a[k],a[i]];app.manual[side]=a;if(app.referenceSide===side)app.referenceSide=null;app.phase='walk';app.walkTime=0;app.playing=true;app.picked=null;app.highlight=null;
    app.lastEditNonce=Date.now();refresh(true);app.send('edit',{n:app.n,side,assignment:a,cost:cost(a),nonce:app.lastEditNonce});
    app.toast(`Vuelos ${LETTERS[i]} y ${LETTERS[k]} intercambiados · costo ${cost(a)}`);
  }
  app.toast=function(text){$('toast').textContent=text;$('toast').hidden=false;app.toastUntil=performance.now()+3600;};
  const handlers=[];
  function listen(el,type,handler){el.addEventListener(type,handler);handlers.push(()=>el.removeEventListener(type,handler));}
  listen($('size'),'input',e=>{app.n=Number(e.target.value);if(app.n<=3)app.mode='mixers';else if(app.n>4)app.mode='lns';app.seed=0;reset();});
  root.querySelectorAll('[data-size]').forEach(button=>listen(button,'click',()=>{app.n=Number(button.dataset.size);app.mode=app.n===4?'mixers':'lns';app.seed=0;reset();}));
  listen($('mode'),'change',e=>{app.mode=e.target.value;if(app.mode==='mixers'&&app.n>4)app.n=4;app.seed=0;reset();});
  listen($('seed'),'change',e=>{app.seed=Number(e.target.value);reset();});
  listen($('speed'),'change',e=>{app.speed=Number(e.target.value);refresh();});
  listen($('play'),'click',play);listen($('restart'),'click',reset);listen($('restore'),'click',reset);listen($('walk'),'click',goWalk);listen($('samples'),'click',samples);
  listen($('timeline'),'input',e=>{app.playing=false;app.highlight=null;const f=Number(e.target.value)/1000;if(['walk','done'].includes(app.phase)){app.phase='walk';app.walkTime=f*8;}else if(app.phase==='samples'){app.sampleTime=f*8;}else{app.phase='search';app.clock=f*duration();}refresh(true);});
  listen($('next'),'click',()=>{app.playing=false;if(app.phase==='samples'){const count=Math.max(1,app.runs[0]?.samples?.length||256);app.sampleTime=Math.min(8,app.sampleTime+8/count);refresh(true);return;}app.manual=[null,null];app.referenceSide=null;app.phase='search';const times=app.runs.flatMap(r=>(r?.events||[]).map(e=>Number(e.elapsed_s))).filter(t=>t>app.clock+1e-7);app.clock=times.length?Math.min(...times):duration();refresh(true);});
  listen($('show-optimum'),'click',()=>{app.manual[0]=instance().exact_assignment.slice();app.referenceSide=0;goWalk();app.toast('Referencia exacta cargada a la izquierda; no se simulan pasos de búsqueda inexistentes.');});
  listen($('evidence'),'click',()=>{renderEvidence();$('drawer').hidden=false;});listen($('close-evidence'),'click',()=>{$('drawer').hidden=true;});
  listen($('live'),'click',()=>{if(app.livePending)return;app.playing=false;app.livePending=true;app.toast('Qiskit vuelve a calcular ambos mixers. Puede tardar varios segundos.');app.send('live',{n:app.n,seed:app.seed,nonce:Date.now()});refresh();});
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
    const runCards=app.runs.map((r,s)=>app.referenceSide===s?`<div class="source-card"><strong>Terminal izquierda · referencia exacta global</strong><p>Costo ${I.optimum}; tiempo medido ${sec(I.exact_seconds)}. Solución guardada de la enumeración completa, sin animación de pasos intermedios.</p></div>`:app.manual[s]?`<div class="source-card"><strong>Tu asignación · ${s?'derecha':'izquierda'}</strong><p>Costo ${cost(app.manual[s])}; exploración manual, sin nueva ejecución de algoritmos.</p></div>`:r?`<div class="source-card"><strong>${s?'Terminal derecha':'Terminal izquierda'} · ${esc(r.id)}</strong><p>Semilla ${r.seed}; tiempo ${sec(r.seconds)}; ${r.live?'calculada ahora':'corrida registrada'}. ${r.timing_scope==='optimizer_and_sampling'?'El tiempo cubre entrenamiento y muestreo.':''}</p><code>${esc(JSON.stringify(r.config))}</code>${r.kind==='qaoa'?`<p>P(óptimo): ${fmt(r.p_optimal*100)}%; factibilidad ideal: ${fmt(r.p_feasible*100)}%; muestras válidas: ${fmt(r.raw_feasible_fraction*100)}%.</p><p>Se visualizan ${r.samples?.length||0} shots reales de ${r.total_shots||r.config.shots}. La selección de una buena muestra no es su probabilidad de aparición.</p>${r.resources?.qubits?`<p>Circuito compilado p=${r.config.reps}: ${r.resources.qubits} qubits, ${r.resources.transpiled_two_qubit_gates} compuertas de dos qubits, profundidad ${r.resources.transpiled_depth}. Backend genérico; no ejecutado en hardware.</p>`:''}`:''}</div>`:'<div class="source-card">No hay traza para esta combinación.</div>').join('');
    const sweep=app.data.sweep.filter(r=>r.n===4&&r.experiment==='mixer_depth_cvar'&&r.alpha===1&&r.reps===2);
    const scalingRows=app.data.instances.map(x=>`<tr><td>${x.n}</td><td>${x.optimum}</td><td>${sec(x.exact_seconds)}</td><td>${x.stats.lns_exact_median??'—'}</td><td>${x.stats.lns_qaoa_median??'—'}</td></tr>`).join('');
    $('evidence-body').innerHTML=`<h3>Lo que se representa</h3><p>La aplicación interpreta QAP10 como vuelos y puertas. El dibujo utiliza la geometría exacta de D: una cuadrícula de cuatro columnas, con distancia Manhattan multiplicada por dos. Las primeras N filas y columnas definen cada subinstancia.</p><p>Una figura representa una unidad de flujo. El costo es <code>Σ F[i,k] × D[puerta_i,puerta_k], i&lt;k</code>. Cada par se cuenta una sola vez. Las emociones y los segundos de movimiento son recursos visuales; no se midieron pasajeros, metros, demoras ni satisfacción de un aeropuerto real.</p><h3>Referencia exacta de N=${app.n}</h3><p><span class="key-number">${I.optimum}</span> · ${row.optimal_assignments} óptimas de ${row.assignments.toLocaleString('es-PE')} permutaciones. Azar válido: ${fmt(row.p_optimal_random*100)}%.</p><h3>Corridas animadas</h3>${runCards}<p>En el híbrido se muestran asignaciones actuales, incluida la exploración después de una patada. Las personas salen con la mejor asignación encontrada. En QAOA directo los pasos del optimizador son energías esperadas; no son planes de puertas. Los cambios del plano durante el muestreo son shots leídos de la ejecución.</p><h3>Hallazgo del barrido original · N=4</h3><p>Cinco semillas, p=2, α=1, hasta 100 evaluaciones y 2048 shots. Azar válido: 8,3%. Las medianas pertenecen a este estudio, no a una sola corrida animada.</p><table><thead><tr><th>Ansatz</th><th>P(óptimo)</th><th>Factibilidad</th><th>Semillas</th></tr></thead><tbody>${sweep.map(r=>`<tr><td>${r.mixer==='x'?'Penalización':'Intercambio'}</td><td>${fmt(100*r.median_p_optimal)}%</td><td>${fmt(100*r.median_p_feasible)}%</td><td>${r.runs_used}/${r.runs}</td></tr>`).join('')}</tbody></table><p>El resultado depende de la semilla; la mejora mediana de N=4 no garantiza que todas las corridas mejoren. No se ha demostrado ventaja cuántica.</p><h3>Escalamiento existente · tres semillas, 60 iteraciones</h3><table><thead><tr><th>N</th><th>Óptimo</th><th>Exacto</th><th>LNS clásico<br>mediana</th><th>LNS QAOA<br>mediana</th></tr></thead><tbody>${scalingRows}</tbody></table><h3>Estudio anterior de N=10 · cinco semillas, 150 iteraciones</h3><table><thead><tr><th>Método</th><th>Mediana</th><th>Tiempo mediano</th></tr></thead><tbody>${app.data.legacy.map(r=>`<tr><td>${esc(r.method)}</td><td>${r.median_cost}</td><td>${sec(r.median_seconds)}</td></tr>`).join('')}</tbody></table><h3>Reproducir y continuar</h3><p><code>python tools/export_visual_demo.py</code> genera trazas; <code>streamlit run app/app.py</code> abre esta app. Aer statevector ideal, sin ruido. Qiskit construye/simula circuitos; COBYLA y la búsqueda externa son clásicos.</p><p>Para la final queda la prueba N≥14 y sus mediciones de tiempo, memoria, calidad y factibilidad. Una aplicación operativa necesitaría horarios, compatibilidad de aeronaves, conexiones reales y distancias caminables.</p><p><a href="https://miplib.zib.de/instance_details_qap10.html" target="_blank" rel="noreferrer">Fuente del benchmark: MIPLIB QAP10 ↗</a></p>`;
  }
  function tick(now) {
    if(app.destroyed)return;
    const dt=Math.min(.1,(now-(app.last||now))/1000);app.last=now;
    if(app.playing) {
      if(app.phase==='search') {app.clock=Math.min(duration(),app.clock+dt*app.speed);if(app.clock>=duration()){if(app.mode==='mixers')samples();else goWalk();}}
      else if(app.phase==='samples'){app.sampleTime+=dt;if(app.sampleTime>=8)goWalk();}
      else if(app.phase==='walk'){app.walkTime=Math.min(8,app.walkTime+dt);if(app.walkTime>=8){app.phase='done';app.playing=false;}}
    }
    if(now-app.lastUI>100){refresh();app.lastUI=now;}
    drawPeople(0);drawPeople(1);
    if(app.toastUntil&&now>app.toastUntil){$('toast').hidden=true;app.toastUntil=0;}
    app.raf=requestAnimationFrame(tick);
  }
  app.cleanup=()=>{app.destroyed=true;cancelAnimationFrame(app.raf);handlers.forEach(f=>f());instances.delete(parentElement);};
  chooseRuns();refresh(true);app.raf=requestAnimationFrame(tick);
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
