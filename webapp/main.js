// main.js
const host = window.location.host;
const API_BASE = `http://${host}/api`;
const WS_URL = `ws://${host}/api/vehiculos/1/ws`;
const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const setStatus = t => $('statusBox').textContent = `ESTADO: ${t}`;

let ws, commandsList = [];

// ==========================================
// ESTADO VISUAL (se anima en un bucle continuo)
// ==========================================
const WORLD = 1200;                              // ancho de la vista lateral (al salir por un lado entra por el otro)
const S = { x: 400, rot: 0, cab: 0, arm: 25, wx: 0, wy: 0 };
const MOTION = ['AVANZAR','RETROCEDER','IZQUIERDA','DERECHA','GIRAR_IZQUIERDA','GIRAR_DERECHA','SUBIR_BRAZO','BAJAR_BRAZO'];
const active = new Set();                        // movimientos con el bit encendido en la ESP
const demoTimers = {};
let lightOn = false, soundOn = false;

function render() {
    $('exSide').style.transform = `translateX(${S.x}px)`;
    $('ground').setAttribute('patternTransform', `translate(${-S.wx} ${-S.wy})`); // la excavadora se queda centrada, se mueve el suelo
    $('exTop').style.transform = `rotate(${S.rot}deg)`;
    $('cabTop').style.transform = `rotate(${S.cab}deg)`;
    $('armBase').style.transform = `rotate(${S.arm}deg)`;
}

let last = performance.now();
function tick(t) {
    const dt = Math.min(0.1, (t - last) / 1000); last = t;
    const d = (p, n) => (active.has(p) ? 1 : 0) - (active.has(n) ? 1 : 0);
    const fwd = d('AVANZAR', 'RETROCEDER'), turn = d('DERECHA', 'IZQUIERDA'),
          cab = d('GIRAR_DERECHA', 'GIRAR_IZQUIERDA'), arm = d('SUBIR_BRAZO', 'BAJAR_BRAZO');
    if (fwd || turn || cab || arm) {
        const r = S.rot * Math.PI / 180;
        S.x = (((S.x - fwd * 90 * dt) % WORLD) + WORLD) % WORLD;   // estilo Pac-Man
        S.wx += Math.sin(r) * fwd * 60 * dt; S.wy -= Math.cos(r) * fwd * 60 * dt;
        S.rot += turn * 45 * dt; S.cab += cab * 45 * dt;
        S.arm = clamp(S.arm + arm * 35 * dt, 0, 60);
        render();
    }
    requestAnimationFrame(tick);
}

function setLight(v) {
    lightOn = v;
    ['exSide', 'exTop', 'btnLight', 'chipLight'].forEach(id => $(id).classList.toggle(id === 'exSide' || id === 'exTop' ? 'light-on' : 'on', v));
}
function setSound(v) {
    soundOn = v;
    $('exSide').classList.toggle('sound-on', v); $('btnHorn').classList.toggle('on', v); $('chipSound').classList.toggle('on', v);
}

// La ESP alterna el bit con cada orden manual: 1ª orden = enciende, 2ª = apaga.
function onVehicleEvent(name, evento, dur) {
    if (evento === 'MOV_DEMO') active.clear();   // en demo la ESP enciende solo ese bit
    if (MOTION.includes(name)) {
        if (evento === 'MOV_DEMO') {
            active.add(name); clearTimeout(demoTimers[name]);
            demoTimers[name] = setTimeout(() => active.delete(name), dur);
        } else active.has(name) ? active.delete(name) : active.add(name);
    } else if (name === 'LUZ') setLight(!lightOn);
    else if (name === 'SONIDO') setSound(!soundOn);
    else if (name === 'DETENER') active.clear();
}

// ==========================================
// WEBSOCKET, HISTORIAL Y COMANDOS
// ==========================================
function connectWebSocket() {
    ws = new WebSocket(WS_URL);
    ws.onopen = () => $('wsDot').className = 'dot on';
    ws.onclose = () => { $('wsDot').className = 'dot off'; setTimeout(connectWebSocket, 2000); };
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.evento === "MOV_INDIVIDUAL" || data.evento === "MOV_DEMO") {
            const name = data.comando || nameById(data.id_comando);
            onVehicleEvent(name, data.evento, data.duracion_ms || 0);
            const st = MOTION.includes(name) ? (active.has(name) ? 'ACTIVO' : 'DETENIDO')
                : name === 'LUZ' ? (lightOn ? 'ENCENDIDA' : 'APAGADA')
                : name === 'SONIDO' ? (soundOn ? 'ACTIVO' : 'APAGADO') : '';
            setStatus(`${name.replace(/_/g, ' ')} ${st}`.trim());
            if (data.evento === "MOV_INDIVIDUAL") loadHistorySoon();
        } else if (data.evento === "FIN_DEMO") {
            active.clear(); setStatus('DEMO FINALIZADA');
        } else if (data.evento === "CANCELADO") {
            active.clear(); setStatus('DEMO CANCELADA');
        }
    };
}

let histTimer;
const loadHistorySoon = () => { clearTimeout(histTimer); histTimer = setTimeout(loadHistory, 400); };

async function loadHistory() {
    try {
        const res = await fetch(`${API_BASE}/vehiculos/1/historial`);
        const data = await res.json();
        $('historyList').innerHTML = data.historial.map(h =>
            `<li>[${esc((h.fecha_hora || '').split('T')[1])}] <b>${esc(h.comando)}</b></li>`).join('') || '<li>Sin movimientos aún</li>';
    } catch (e) {}
}

async function fetchCommands() {
    try {
        const res = await fetch(`${API_BASE}/vehiculos/1/comandos`);
        commandsList = await res.json();
        $('cmdSelect').innerHTML = commandsList.map(c => `<option value="${c.id_comando}">${esc(c.nombre)}</option>`).join('');
    } catch (e) {}
}

const nameById = id => (commandsList.find(c => c.id_comando === id) || {}).nombre || '';
const idByName = name => (commandsList.find(c => c.nombre === name) || {}).id_comando || 0;
const findCmd = re => commandsList.find(c => re.test(c.nombre));

// ==========================================
// CONTROL REMOTO
// ==========================================
function sendCommand(id_comando) {
    if (!id_comando) return;
    fetch(`${API_BASE}/vehiculos/1/movimientos`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, keepalive: true,
        body: JSON.stringify({ id_vehiculo: 1, id_comando, conectado: true, origen: "WEB_GUI" })
    }).catch(() => setStatus('SIN CONEXIÓN CON LA API'));
}

const JOYS = [
    { el: 'joyLeft', title: 'ORUGAS', dirs: {
        up: ['AVANZAR', 'AVANZAR', '▲'], down: ['RETROCEDER', 'RETROCEDER', '▼'], left: ['IZQUIERDA', 'IZQUIERDA', '◀'], right: ['DERECHA', 'DERECHA', '▶'] } },
    { el: 'joyRight', title: 'CABINA Y BRAZO', dirs: {
        up: ['SUBIR_BRAZO', 'SUBIR BRAZO', '▲'], down: ['BAJAR_BRAZO', 'BAJAR BRAZO', '▼'], left: ['GIRAR_IZQUIERDA', 'CABINA IZQ.', '◀'], right: ['GIRAR_DERECHA', 'CABINA DER.', '▶'] } }
];

// Mantener la palanca = UNA orden al entrar (enciende el bit) y UNA al soltar (lo apaga).
function setupJoystick(cfg) {
    const wrap = $(cfg.el + 'Wrap');
    wrap.innerHTML = `<div class="joy-title">${cfg.title}</div><div class="joy-area">` +
        Object.entries(cfg.dirs).map(([d, [, txt, ic]]) => `<div class="hint ${d}" data-d="${d}"><b>${ic}</b>${txt}</div>`).join('') +
        `<div class="joy-base"><div class="joy-stick" id="${cfg.el}"></div></div></div>`;
    const base = wrap.querySelector('.joy-base'), stick = $(cfg.el);
    let dragging = false, dir = null, axis = null;

    const light = d => wrap.querySelectorAll('.hint').forEach(h => h.classList.toggle('on', h.dataset.d === d));
    const setDir = d => {
        if (d === dir) return;
        if (dir) sendCommand(idByName(cfg.dirs[dir][0]));   // soltar la dirección anterior: la ESP alterna → se apaga
        dir = d; light(d);
        if (d) sendCommand(idByName(cfg.dirs[d][0]));       // nueva dirección: se enciende
    };
    // Palanca tipo "+": al salir del centro se elige UN eje (horizontal o vertical) y la palanca solo corre por ese eje.
    // Para cambiar de eje hay que volver al centro, así no se cuelan movimientos vecinos en las diagonales.
    const move = e => {
        if (!dragging) return;
        const r = base.getBoundingClientRect(), MAX = r.width * 0.22, ON = MAX * 0.5, OFF = MAX * 0.3;
        let dx = e.clientX - (r.left + r.width / 2), dy = e.clientY - (r.top + r.height / 2);
        if (!axis) {   // solo se decide el eje cuando la intención es clara (no en la diagonal)
            const ax = Math.abs(dx), ay = Math.abs(dy);
            if (Math.max(ax, ay) >= ON && Math.max(ax, ay) > 1.4 * Math.min(ax, ay)) axis = ax > ay ? 'h' : 'v';
        }
        if (axis === 'h') dy = 0; else if (axis === 'v') dx = 0;
        const dist = Math.hypot(dx, dy);
        if (dist > MAX) { dx *= MAX / dist; dy *= MAX / dist; }
        stick.style.transform = `translate(${dx}px,${dy}px)`;
        let d = null;
        if (axis) {
            const v = axis === 'h' ? dx : dy, a = Math.abs(v);
            if (a >= ON || (dir && a >= OFF)) d = axis === 'h' ? (v > 0 ? 'right' : 'left') : (v > 0 ? 'down' : 'up'); // histéresis
            else axis = null;   // volvió al centro: puede elegir otro eje
        }
        setDir(d);
    };
    // send=false: solo reinicia la palanca sin mandar nada (lo usa PARAR)
    const release = (send = true) => {
        dragging = false; axis = null; stick.classList.remove('drag'); stick.style.transform = '';
        if (send) setDir(null); else { dir = null; light(null); }
    };
    stick.addEventListener('pointerdown', e => { dragging = true; stick.setPointerCapture(e.pointerId); stick.classList.add('drag'); move(e); });
    stick.addEventListener('pointermove', move);
    stick.addEventListener('pointerup', () => release());
    stick.addEventListener('pointercancel', () => release());
    return release;
}
const stopFns = JOYS.map(setupJoystick);
// Si la pestaña pierde el foco con la palanca presionada, se suelta (evita bits pegados)
window.addEventListener('blur', () => stopFns.forEach(f => f()));
document.addEventListener('visibilitychange', () => { if (document.hidden) stopFns.forEach(f => f()); });

function namedCmd(re, label) {
    const c = findCmd(re);
    c ? sendCommand(c.id_comando) : setStatus(`COMANDO "${label}" NO DISPONIBLE`);
}
$('btnLight').onclick = () => namedCmd(/luz|luces|light/i, 'LUCES');
$('btnHorn').onclick = () => namedCmd(/sonido|claxon|bocina|horn/i, 'SONIDO');
$('btnStop').onclick = () => {
    stopFns.forEach(f => f(false));      // no mandar "soltar": DETENER ya apaga todo en la ESP
    active.clear();
    const c = findCmd(/parar|stop|detener/i);
    if (c) sendCommand(c.id_comando);
    setStatus('DETENIDO');
};

// ==========================================
// DEMOS Y MODAL
// ==========================================
let demos = [], draftDemoId = null, draftSteps = [], dragFrom = -1, oldStepIds = [];

async function loadDemos() {
    try {
        const res = await fetch(`${API_BASE}/vehiculos/1/demos`);
        if (!res.ok) throw new Error(res.status);
        demos = await res.json();
    } catch (e) {
        $('demosList').innerHTML = '<p class="empty">No se pudieron cargar las demos. Revisa la API.</p>';
        return;
    }
    $('demoSelect').innerHTML = demos.length
        ? demos.map(d => `<option value="${d.id_demo}">${esc(d.nombre)}</option>`).join('')
        : '<option value="">(sin demos)</option>';
    $('demosList').innerHTML = demos.length ? demos.map(d => `
        <div class="demo-item">
            <div class="demo-txt"><b>${esc(d.nombre)}</b><small>${esc(d.descripcion)}</small></div>
            <div class="demo-btns">
                <button class="btn-success" data-act="play" data-id="${d.id_demo}" title="Ejecutar">▶</button>
                <button class="btn-secondary" data-act="edit" data-id="${d.id_demo}" title="Editar">✏️</button>
                <button class="btn-danger" data-act="del" data-id="${d.id_demo}" title="Eliminar">🗑</button>
            </div>
        </div>`).join('') : '<p class="empty">Aún no hay demos. Crea la primera con «Nueva demo».</p>';
}

$('demosList').onclick = e => {
    const b = e.target.closest('button'); if (!b) return;
    const id = +b.dataset.id;
    if (b.dataset.act === 'play') playDemo(id);
    else if (b.dataset.act === 'edit') editDemo(id);
    else if (b.dataset.act === 'del') deleteDemo(id);
};
$('runBtn').onclick = () => { const id = $('demoSelect').value; if (id) playDemo(id); else setStatus('NO HAY DEMOS PARA EJECUTAR'); };
$('newDemoBtn').onclick = openDemoModal;
$('cancelDemoBtn').onclick = () => { if (ws && ws.readyState === 1) ws.send('CANCELAR'); };
$('cancelBtn').onclick = closeDemoModal;
$('addStepBtn').onclick = addMovementToDraft;
$('saveBtn').onclick = saveDemo;

function playDemo(id) {
    const d = demos.find(x => x.id_demo === id);
    setStatus(`INICIANDO DEMO${d ? ' - ' + d.nombre : ''}`);
    fetch(`${API_BASE}/vehiculos/1/demos/${id}/iniciar`, { method: 'POST' })
        .then(r => { if (r.status === 409) setStatus('YA HAY UNA DEMO EN CURSO'); })
        .catch(() => setStatus('SIN CONEXIÓN CON LA API'));
}

async function editDemo(id) {
    const d = demos.find(x => x.id_demo === id); if (!d) return;
    draftDemoId = id;
    $('modalTitle').textContent = "Editar demo";
    $('demoName').value = d.nombre; $('demoDesc').value = d.descripcion || '';
    const res = await fetch(`${API_BASE}/demos/${id}/movimientos`);
    const steps = await res.json();
    oldStepIds = steps.map(s => s.id_demo_movimiento);
    draftSteps = steps.sort((a, b) => (a.orden || 0) - (b.orden || 0)).map(s => ({
        id_comando: s.id_comando, nombre: s.comando, duracion_ms: s.duracion_ms, pausa_ms: s.pausa_ms }));
    renderDraftSteps();
    $('demoModal').classList.remove('hidden');
}

function openDemoModal() {
    draftDemoId = null; draftSteps = []; oldStepIds = [];
    $('modalTitle').textContent = "Nueva demo";
    $('demoName').value = ""; $('demoDesc').value = "";
    renderDraftSteps();
    $('demoModal').classList.remove('hidden');
}
function closeDemoModal() { $('demoModal').classList.add('hidden'); }

function addMovementToDraft() {
    const sel = $('cmdSelect'); if (!sel.value) return;
    draftSteps.push({
        id_comando: parseInt(sel.value),
        nombre: sel.options[sel.selectedIndex].text,
        duracion_ms: parseInt($('cmdDuration').value) || 1000,
        pausa_ms: parseInt($('cmdPause').value) || 0
    });
    renderDraftSteps();
    const list = $('draftSteps'); list.scrollTop = list.scrollHeight;
}

function moveStep(from, to) {
    if (from < 0 || to < 0 || to >= draftSteps.length || from === to) return;
    draftSteps.splice(to, 0, draftSteps.splice(from, 1)[0]);
    renderDraftSteps();
}

function renderDraftSteps() {
    const list = $('draftSteps'); list.innerHTML = '';
    $('stepCount').textContent = `(${draftSteps.length} pasos)`;
    if (!draftSteps.length) { list.innerHTML = '<li class="empty">Aún no hay pasos. Agrega el primero con el botón de la izquierda.</li>'; return; }
    draftSteps.forEach((s, i) => {
        const li = document.createElement('li');
        li.draggable = true;
        li.innerHTML = `<span class="grip">⠿</span><span class="num">${i + 1}</span>
            <span class="st"><b>${esc(s.nombre)}</b><small>${s.duracion_ms} ms · pausa ${s.pausa_ms} ms</small></span>
            <span class="mv"><button data-m="up">▲</button><button data-m="down">▼</button><button class="btn-danger" data-m="del">✕</button></span>`;
        li.ondragstart = e => { dragFrom = i; li.classList.add('dragging'); e.dataTransfer.effectAllowed = 'move'; e.dataTransfer.setData('text/plain', i); };
        li.ondragend = () => li.classList.remove('dragging');
        li.ondragover = e => { e.preventDefault(); li.classList.add('over'); };
        li.ondragleave = () => li.classList.remove('over');
        li.ondrop = e => { e.preventDefault(); moveStep(dragFrom, i); };
        li.onclick = e => {
            const m = e.target.dataset.m;
            if (m === 'up') moveStep(i, i - 1);
            else if (m === 'down') moveStep(i, i + 1);
            else if (m === 'del') { draftSteps.splice(i, 1); renderDraftSteps(); }
        };
        list.appendChild(li);
    });
}

async function saveDemo() {
    const name = $('demoName').value.trim(), desc = $('demoDesc').value.trim();
    if (!name || !draftSteps.length) return alert("Falta el nombre o agregar al menos un paso.");
    const btn = $('saveBtn'); btn.disabled = true;
    const json = { 'Content-Type': 'application/json' };
    try {
        let demoId = draftDemoId;
        if (!demoId) {
            const res = await fetch(`${API_BASE}/vehiculos/1/demos`, { method: 'POST', headers: json, body: JSON.stringify({ nombre: name, descripcion: desc }) });
            const data = await res.json();
            demoId = data.id_demo ?? data.id;
        } else {
            await fetch(`${API_BASE}/demos/${demoId}`, { method: 'PUT', headers: json, body: JSON.stringify({ nombre: name, descripcion: desc, activo: true }) });
            for (const m of oldStepIds) await fetch(`${API_BASE}/demo_movimientos/${m}`, { method: 'DELETE' }); // borra los pasos viejos
        }
        for (let i = 0; i < draftSteps.length; i++) {
            const s = draftSteps[i];
            const q = new URLSearchParams({ id_comando: s.id_comando, orden: i + 1, duracion_ms: s.duracion_ms, pausa_ms: s.pausa_ms }); // tu API los recibe como query params
            const r = await fetch(`${API_BASE}/demos/${demoId}/movimientos?${q}`, { method: 'POST' });
            if (!r.ok) throw new Error(`Paso ${i + 1}: ${r.status}`);
        }
        closeDemoModal();
        await loadDemos();
    } catch (e) {
        alert("No se pudo guardar la demo. Revisa la terminal de la API.");
    } finally { btn.disabled = false; }
}

async function deleteDemo(id) {
    if (!confirm("¿Borrar esta secuencia?")) return;
    await fetch(`${API_BASE}/demos/${id}`, { method: 'DELETE' });
    loadDemos();
}

// Inicialización (en serie para no saturar la conexión a MySQL al cargar)
(async () => {
    setLight(true); setSound(true);   // el carro arranca con luz y sonido encendidos
    render();
    requestAnimationFrame(tick);
    connectWebSocket();
    await fetchCommands();
    await loadHistory();
    await loadDemos();
})();