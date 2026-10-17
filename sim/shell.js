const DEMO = ["shopping", "scoreboard", "hydration", "notes"];
const params = new URLSearchParams(location.search);
const STUB = params.get("stub") || "http://127.0.0.1:8787/v1/turn";
const KEY = "omni.registry.v2";

const state = {
  screen: "home",
  appId: null,
  registry: [],
  agent: "idle",
  say: "",
  proposal: null,
  modules: {},
};

let respondTimer = 0;

function clamp(n, lo, hi) {
  return Math.max(lo, Math.min(hi, n));
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[ch]));
}

function clockText() {
  return new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

function findApp(id) {
  return state.registry.find((app) => app.id === id) || null;
}

function currentApp() {
  return state.screen === "app" ? findApp(state.appId) : null;
}

function layoutOf(moduleName) {
  const layout = (state.modules[moduleName] && state.modules[moduleName].layout) || {};
  return {
    margin: layout.margin || 18,
    headerH: layout.header_h || 48,
    rowH: layout.row_h || 56,
    barH: layout.bar_h || 16,
  };
}

function blurb(app) {
  const data = app.state || {};
  if (app.module === "checklist") {
    const left = (data.items || []).filter((item) => !item.checked).length;
    return left === 1 ? "1 left" : left + " left";
  }
  if (app.module === "scoreboard") {
    return (data.sides || []).map((side) => side.name + " " + side.score).join("  ·  ");
  }
  if (app.module === "progress") {
    return data.value + " / " + data.goal + " " + data.unit;
  }
  const row = (data.rows || [])[0];
  return row ? row.label + ": " + row.value : "Empty";
}

function agentLabel() {
  if (state.agent === "listening") return "Listening";
  if (state.agent === "thinking") return "Thinking";
  if (state.say) return state.say;
  return "Ready when you are";
}

function save() {
  localStorage.setItem(KEY, JSON.stringify({
    registry: state.registry,
    screen: state.screen,
    appId: state.appId,
  }));
}

function loadSaved() {
  try {
    return JSON.parse(localStorage.getItem(KEY) || "null");
  } catch (err) {
    return null;
  }
}

function iconLetter(app) {
  return escapeHtml((app.title || "?").slice(0, 1).toUpperCase());
}

const OMNI_ARROWS = [
  { angle: -126, len: 58, headL: 18, headW: 11, shaftW: 4.5 },
  { angle: -52, len: 48, headL: 16, headW: 10, shaftW: 4.5 },
  { angle: 15, len: 58, headL: 18, headW: 11, shaftW: 4.5 },
  { angle: 90, len: 50, headL: 16, headW: 10, shaftW: 4.5 },
  { angle: 162, len: 46, headL: 16, headW: 10, shaftW: 4.5 },
];

function omniMark(size) {
  const scale = 1;
  const cx = 70;
  const cy = 70;
  const arrows = OMNI_ARROWS.map((arrow) => {
    const rad = (arrow.angle * Math.PI) / 180;
    const ux = Math.cos(rad);
    const uy = Math.sin(rad);
    const px = -uy;
    const py = ux;
    const startR = (22 - 4) * scale;
    const tip = arrow.len * scale;
    const headL = arrow.headL * scale;
    const headW = arrow.headW * scale;
    const shaftW = arrow.shaftW * scale;
    const base = tip - headL;
    const points = [
      [cx + ux * startR + px * shaftW, cy + uy * startR + py * shaftW],
      [cx + ux * base + px * shaftW, cy + uy * base + py * shaftW],
      [cx + ux * base + px * headW, cy + uy * base + py * headW],
      [cx + ux * tip, cy + uy * tip],
      [cx + ux * base - px * headW, cy + uy * base - py * headW],
      [cx + ux * base - px * shaftW, cy + uy * base - py * shaftW],
      [cx + ux * startR - px * shaftW, cy + uy * startR - py * shaftW],
    ];
    return "M" + points.map((point) => point[0].toFixed(1) + " " + point[1].toFixed(1)).join("L") + "Z";
  }).join("");
  return `
    <svg class="omni-mark" viewBox="0 0 140 140" width="${size}" height="${size}" aria-hidden="true">
      <path fill="currentColor" d="${arrows}"/>
      <path fill="currentColor" fill-rule="evenodd" d="M70 70m-22 0a22 22 0 1 0 44 0a22 22 0 1 0 -44 0M70 70m-11 0a11 11 0 1 0 22 0a11 11 0 1 0 -22 0"/>
    </svg>
  `;
}

function renderHome() {
  if (!state.registry.length) {
    return `
      <div class="home home-empty">
        <div class="home-brand">${omniMark(168)}<p class="wordmark boot-name">omni</p></div>
        <p class="empty">No apps yet. Ask for a list, a scoreboard, or a water log.</p>
      </div>
    `;
  }
  const tiles = state.registry.map((app) => `
    <button type="button" class="tile" data-act="open" data-id="${escapeHtml(app.id)}">
      <span class="tile-top">
        <span class="badge badge-${escapeHtml(app.module)}">${iconLetter(app)}</span>
        <span class="tile-title">${escapeHtml(app.title)}</span>
      </span>
      <span class="tile-blurb">${escapeHtml(blurb(app))}</span>
    </button>
  `).join("");
  return `
    <div class="home">
      <div class="home-brand">${omniMark(112)}<p class="wordmark">omni</p></div>
      <div class="app-list">${tiles}</div>
    </div>
  `;
}

function renderChecklist(app) {
  const layout = layoutOf(app.module);
  const cursor = app.state.cursor || 0;
  const rows = (app.state.items || []).map((item, index) => `
    <button type="button" class="row${index === cursor ? " is-cursor" : ""}${item.checked ? " is-checked" : ""}"
      data-act="toggle" data-index="${index}" style="min-height:${layout.rowH}px">
      <span class="check" aria-hidden="true">
        <svg viewBox="0 0 16 16"><path d="M3 8.5 6.2 12 13 4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
      </span>
      <span class="row-label">${escapeHtml(item.label)}</span>
    </button>
  `).join("");
  return rows || '<p class="empty">Nothing on the list.</p>';
}

function renderScoreboard(app) {
  const cursor = app.state.cursor || 0;
  const sides = (app.state.sides || []).map((side, index) => `
    <section class="side${index === cursor ? " is-cursor" : ""}">
      <h3 class="side-name">${escapeHtml(side.name)}</h3>
      <p class="side-score">${escapeHtml(side.score)}</p>
      <div class="side-actions">
        <button type="button" data-act="dec" data-index="${index}" aria-label="Decrease ${escapeHtml(side.name)}">−</button>
        <button type="button" data-act="inc" data-index="${index}" aria-label="Increase ${escapeHtml(side.name)}">+</button>
      </div>
    </section>
  `).join("");
  return `<div class="board">${sides}</div>`;
}

function renderProgress(app) {
  const layout = layoutOf(app.module);
  const data = app.state;
  const goal = Number(data.goal) || 1;
  const pct = Math.max(0, Math.min(100, (Number(data.value) / goal) * 100));
  const step = Number(data.step) || 1;
  return `
    <p class="metric-label">${escapeHtml(data.label)}</p>
    <p class="metric-value">${escapeHtml(data.value)}</p>
    <p class="metric-goal">of ${escapeHtml(data.goal)} ${escapeHtml(data.unit)}</p>
    <div class="bar" style="height:${layout.barH}px"><span style="width:${pct}%"></span></div>
    <div class="quick">
      <button type="button" data-act="add" data-amount="${step}">+${step} ${escapeHtml(data.unit)}</button>
      <button type="button" data-act="add" data-amount="${step * 2}">+${step * 2} ${escapeHtml(data.unit)}</button>
    </div>
  `;
}

function renderKeyValue(app) {
  const layout = layoutOf(app.module);
  const cursor = app.state.cursor || 0;
  return (app.state.rows || []).map((row, index) => `
    <button type="button" class="row kv${index === cursor ? " is-cursor" : ""}"
      data-act="focus" data-index="${index}" style="min-height:${layout.rowH}px">
      <span class="row-label">${escapeHtml(row.label)}</span>
      <strong>${escapeHtml(row.value)}</strong>
    </button>
  `).join("");
}

function renderApp(app) {
  const layout = layoutOf(app.module);
  let body = "";
  if (app.module === "checklist") body = renderChecklist(app);
  else if (app.module === "scoreboard") body = renderScoreboard(app);
  else if (app.module === "progress") body = renderProgress(app);
  else body = renderKeyValue(app);
  return `
    <div class="app-view" style="padding:${layout.margin}px">
      <header class="app-head" style="min-height:${layout.headerH}px">
        <button type="button" class="back" data-act="back" aria-label="Home">
          <svg viewBox="0 0 24 24"><path d="M15 5 8 12l7 7" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </button>
        <h2 class="app-title">${escapeHtml(app.title)}</h2>
        <span class="app-module">${escapeHtml(app.module)}</span>
      </header>
      <div class="rows">${body}</div>
    </div>
  `;
}

function renderProposal() {
  if (!state.proposal) return "";
  const say = state.proposal.say || "Create this app?";
  return `
    <div class="modal">
      <div class="dialog" role="dialog" aria-label="Create app">
        <p>${escapeHtml(say)}</p>
        <div class="dialog-actions">
          <button type="button" class="btn-primary" data-act="confirm">Yes, create it</button>
          <button type="button" class="btn-ghost" data-act="cancel">Cancel</button>
        </div>
      </div>
    </div>
  `;
}

function render() {
  const listening = state.agent === "listening";
  const screen = document.getElementById("screen");
  const app = currentApp();
  screen.className = "screen" + (listening ? " is-listening" : "");
  screen.innerHTML = `
    <header class="agent agent-${state.agent}">
      <span class="brand">${omniMark(32)}<span class="wordmark">omni</span></span>
      <span class="agent-copy">
        <span class="dot dot-${state.agent}"></span>
        <span class="waves" aria-hidden="true"><i></i><i></i><i></i><i></i></span>
        <span class="agent-label">${escapeHtml(agentLabel())}</span>
      </span>
      <time id="clock" class="clock">${escapeHtml(clockText())}</time>
    </header>
    <main class="body">${app ? renderApp(app) : renderHome()}</main>
    <footer class="dock">
      <button type="button" class="ptt${listening ? " is-hot" : ""}" data-act="talk">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 14a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v5a3 3 0 0 0 3 3zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.92V21h2v-3.08A7 7 0 0 0 19 11z"/></svg>
        <span class="ptt-label">${listening ? "Release to send" : "Hold to talk"}</span>
      </button>
    </footer>
    ${renderProposal()}
  `;
  renderJumps();
}

function renderJumps() {
  const jumps = document.getElementById("jumps");
  if (!jumps) return;
  const apps = state.registry.map((app) =>
    `<button type="button" data-jump="${escapeHtml(app.id)}">${escapeHtml(app.title)}</button>`
  ).join("");
  jumps.innerHTML = `<button type="button" data-jump="home">Home</button>${apps}`;
}

function applyAction(app, action) {
  const name = action.action;
  const args = action.args || {};
  const data = app.state;
  if (!data) return;
  if (app.module === "checklist") {
    const items = data.items || (data.items = []);
    if (name === "scroll") {
      data.cursor = clamp((data.cursor || 0) + Number(args.dir || 0), 0, Math.max(0, items.length - 1));
    } else if (name === "toggle") {
      const item = items[data.cursor || 0];
      if (item) item.checked = !item.checked;
    } else if (name === "append" && args.label) {
      items.push({ label: String(args.label), checked: false });
    } else if (name === "remove") {
      items.splice(data.cursor || 0, 1);
      data.cursor = clamp(data.cursor || 0, 0, Math.max(0, items.length - 1));
    }
  } else if (app.module === "scoreboard") {
    const sides = data.sides || [];
    if (name === "scroll") {
      data.cursor = clamp((data.cursor || 0) + Number(args.dir || 0), 0, Math.max(0, sides.length - 1));
    } else if (name === "inc" || name === "dec") {
      const side = sides[data.cursor || 0];
      if (side) side.score = Math.max(0, Number(side.score || 0) + (name === "inc" ? 1 : -1));
    }
  } else if (app.module === "progress" && name === "add") {
    const amount = args.amount == null ? Number(data.step || 0) : Number(args.amount);
    data.value = Math.min(Number(data.goal || 0), Number(data.value || 0) + amount);
  } else if (app.module === "key_value" && name === "scroll") {
    const rows = data.rows || [];
    data.cursor = clamp((data.cursor || 0) + Number(args.dir || 0), 0, Math.max(0, rows.length - 1));
  }
}

function armIdle() {
  clearTimeout(respondTimer);
  respondTimer = setTimeout(() => {
    if (state.agent === "responding") {
      state.agent = "idle";
      render();
    }
  }, 4200);
}

function applyTurn(turn) {
  state.say = turn.say || "";
  state.agent = "responding";
  if (turn.op === "propose" && turn.app) {
    state.proposal = turn;
    clearTimeout(respondTimer);
  } else if (turn.op === "mutate") {
    const app = findApp(turn.app_id);
    if (app) {
      (turn.actions || []).forEach((action) => applyAction(app, action));
      state.screen = "app";
      state.appId = app.id;
    }
    state.proposal = null;
    armIdle();
  } else {
    state.proposal = null;
    armIdle();
  }
  save();
  render();
}

function setStatus(text) {
  const el = document.getElementById("stub-status");
  if (el) el.textContent = text;
}

async function sendTurn(text) {
  clearTimeout(respondTimer);
  if (!text) {
    state.agent = "responding";
    state.say = "Type a request in the simulator, then send it.";
    armIdle();
    render();
    return;
  }
  state.agent = "thinking";
  state.proposal = null;
  render();
  setStatus("Sending to the stub…");
  try {
    const response = await fetch(STUB, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text,
        registry: state.registry,
        focused_app_id: state.appId,
      }),
    });
    if (!response.ok) throw new Error("HTTP " + response.status);
    const turn = await response.json();
    setStatus("Last turn: " + (turn.op || "unknown"));
    applyTurn(turn);
  } catch (err) {
    state.agent = "responding";
    state.say = "The turn stub is not running.";
    setStatus("Start python3 cloud/stub_server.py");
    armIdle();
    render();
  }
}

function confirmProposal() {
  const turn = state.proposal;
  if (!turn || !turn.app) return;
  const index = state.registry.findIndex((app) => app.id === turn.app.id);
  if (index >= 0) state.registry[index] = turn.app;
  else state.registry.push(turn.app);
  state.screen = "app";
  state.appId = turn.app.id;
  state.proposal = null;
  state.agent = "idle";
  state.say = "";
  save();
  render();
}

function cancelProposal() {
  state.proposal = null;
  state.agent = "idle";
  state.say = "";
  save();
  render();
}

function openApp(id) {
  if (!findApp(id)) return;
  state.screen = "app";
  state.appId = id;
  state.proposal = null;
  save();
  render();
}

function goHome() {
  state.screen = "home";
  state.appId = null;
  state.proposal = null;
  save();
  render();
}

function onScreenClick(event) {
  const el = event.target.closest("[data-act]");
  if (!el || el.dataset.act === "talk") return;
  if (state.agent === "thinking") return;
  const act = el.dataset.act;
  if (act === "open") return openApp(el.dataset.id);
  if (act === "back") return goHome();
  if (act === "confirm") return confirmProposal();
  if (act === "cancel") return cancelProposal();
  const app = currentApp();
  if (!app) return;
  if (act === "toggle" || act === "inc" || act === "dec" || act === "focus") {
    app.state.cursor = Number(el.dataset.index);
  }
  if (act === "toggle") applyAction(app, { action: "toggle", args: {} });
  else if (act === "inc" || act === "dec") applyAction(app, { action: act, args: {} });
  else if (act === "add") applyAction(app, { action: "add", args: { amount: Number(el.dataset.amount) } });
  save();
  render();
}

function onTalkDown(event) {
  const el = event.target.closest("[data-act=talk]");
  if (!el || state.agent === "thinking") return;
  el.setPointerCapture(event.pointerId);
  state.agent = "listening";
  const screen = document.getElementById("screen");
  screen.classList.add("is-listening");
  el.classList.add("is-hot");
  const label = screen.querySelector(".agent-label");
  const ptt = screen.querySelector(".ptt-label");
  const dot = screen.querySelector(".dot");
  if (label) label.textContent = "Listening";
  if (ptt) ptt.textContent = "Release to send";
  if (dot) dot.className = "dot dot-listening";
}

function onTalkUp() {
  const screen = document.getElementById("screen");
  if (!screen.classList.contains("is-listening")) return;
  screen.classList.remove("is-listening");
  sendTurn(document.getElementById("utterance").value.trim());
}

function preview(agent) {
  clearTimeout(respondTimer);
  state.agent = agent;
  if (agent === "responding" && !state.say) {
    state.say = "I can make a list, a scoreboard, or a water log.";
  }
  render();
}

async function loadJson(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(path);
  return response.json();
}

async function loadModules() {
  const names = ["checklist", "scoreboard", "progress", "key_value"];
  const files = await Promise.all(names.map((name) => loadJson("/contract/modules/" + name + ".json")));
  names.forEach((name, index) => {
    state.modules[name] = files[index];
  });
}

async function loadDemos() {
  state.registry = await Promise.all(DEMO.map((name) => loadJson("/contract/fixtures/apps/" + name + ".json")));
  state.screen = "home";
  state.appId = null;
  state.proposal = null;
  state.agent = "idle";
  state.say = "";
  save();
  render();
}

function emptyDevice() {
  state.registry = [];
  state.screen = "home";
  state.appId = null;
  state.proposal = null;
  state.agent = "idle";
  state.say = "";
  save();
  render();
}

function fit() {
  const frame = document.getElementById("frame");
  if (!document.body.classList.contains("kiosk")) {
    frame.style.transform = "";
    return;
  }
  const turn = params.get("turn") === "left" ? -90 : 90;
  const scale = Math.min(window.innerWidth / 800, window.innerHeight / 480);
  frame.style.transform = "rotate(" + turn + "deg) scale(" + scale + ")";
}

function bind() {
  const screen = document.getElementById("screen");
  screen.addEventListener("click", onScreenClick);
  screen.addEventListener("pointerdown", onTalkDown);
  screen.addEventListener("pointerup", onTalkUp);
  screen.addEventListener("pointercancel", onTalkUp);
  document.getElementById("jumps").addEventListener("click", (event) => {
    const el = event.target.closest("[data-jump]");
    if (!el) return;
    if (el.dataset.jump === "home") goHome();
    else openApp(el.dataset.jump);
  });
  document.getElementById("previews").addEventListener("click", (event) => {
    const el = event.target.closest("[data-preview]");
    if (el) preview(el.dataset.preview);
  });
  document.getElementById("load-demos").addEventListener("click", () => {
    loadDemos().catch(() => setStatus("Could not load contract fixtures."));
  });
  document.getElementById("empty-device").addEventListener("click", emptyDevice);
  document.getElementById("send").addEventListener("click", () => {
    sendTurn(document.getElementById("utterance").value.trim());
  });
  document.getElementById("utterance").addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendTurn(event.target.value.trim());
    }
  });
  window.addEventListener("keydown", (event) => {
    if (event.ctrlKey && event.shiftKey && event.key.toLowerCase() === "q") {
      event.preventDefault();
      fetch("/__omni/quit", { method: "POST" }).catch(() => {});
    }
  });
  window.addEventListener("resize", fit);
  setInterval(() => {
    const clock = document.getElementById("clock");
    if (clock) clock.textContent = clockText();
  }, 10000);
}

async function boot() {
  if (params.has("kiosk")) document.body.classList.add("kiosk");
  bind();
  fit();
  try {
    await loadModules();
  } catch (err) {
    setStatus("Serve the repo root so /contract can load.");
  }
  const saved = loadSaved();
  if (saved && Array.isArray(saved.registry)) {
    state.registry = saved.registry;
    state.screen = saved.screen || "home";
    state.appId = saved.appId;
    if (state.screen === "app" && !findApp(state.appId)) goHome();
    else render();
    return;
  }
  try {
    await loadDemos();
  } catch (err) {
    render();
    setStatus("Serve the repo root so /contract can load.");
  }
}

boot();
