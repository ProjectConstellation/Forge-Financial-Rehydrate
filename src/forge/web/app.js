"use strict";
/* FORGE founder portal — every number is pushed live from the engine (SSE /api/live); nothing is simulated in the browser. */
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
const usd = (x, d = 2) => (x == null || isNaN(x)) ? "—" : (x < 0 ? "−$" : "$") + Math.abs(+x).toLocaleString(undefined, {minimumFractionDigits: d, maximumFractionDigits: d});
const pct = (x, d = 2) => (x == null || isNaN(x)) ? "—" : (x >= 0 ? "+" : "−") + Math.abs(100 * x).toFixed(d) + "%";
const sgn = (x) => x > 0 ? "pos" : x < 0 ? "neg" : "";
const ago = (s) => s == null ? "—" : s < 60 ? `${s}s` : s < 3600 ? `${Math.floor(s / 60)}m` : `${Math.floor(s / 3600)}h ${Math.floor(s % 3600 / 60)}m`;
let CSRF = null, history = [], lastVals = {}, lastMsg = 0;

function setNum(id, text, raw) {           // animated flash on change
  const el = $(id); if (!el) return; if (el.textContent !== text) {
    const prev = lastVals[id]; el.textContent = text;
    if (prev != null && raw != null && raw !== prev) { el.classList.remove("flash-up", "flash-dn"); void el.offsetWidth; el.classList.add(raw > prev ? "flash-up" : "flash-dn"); }
    lastVals[id] = raw; } }

async function api(path, opts = {}) {
  const r = await fetch(path, {credentials: "same-origin", ...opts, headers: {"Content-Type": "application/json", ...(CSRF ? {"X-CSRF": CSRF} : {}), ...(opts.headers || {})}});
  if (r.status === 401) { location.href = "/login"; throw new Error("login"); }
  if (!r.ok) throw new Error((await r.text()).slice(0, 200)); return r.json(); }

/* ---------------- tabs ---------------- */
$("tabs").addEventListener("click", (e) => { const t = e.target.dataset.t; if (!t) return;
  document.querySelectorAll(".tabs button").forEach(b => b.classList.toggle("on", b.dataset.t === t));
  document.querySelectorAll(".tab").forEach(x => x.classList.toggle("on", x.id === "t-" + t)); });

/* ---------------- chart ---------------- */
function drawChart() {
  const svg = $("chart"); const pts = history.filter(p => p.v != null); if (pts.length < 2) { svg.innerHTML = ""; return; }
  const W = 600, H = 140, min = Math.min(...pts.map(p => p.v)), max = Math.max(...pts.map(p => p.v)), span = (max - min) || Math.max(0.01, Math.abs(max) * 0.002);
  const t0 = pts[0].t, t1 = pts[pts.length - 1].t || t0 + 1;
  const xy = pts.map(p => [((p.t - t0) / Math.max(1, t1 - t0)) * W, H - 10 - ((p.v - min) / span) * (H - 20)]);
  const d = xy.map((q, i) => (i ? "L" : "M") + q[0].toFixed(1) + " " + q[1].toFixed(1)).join(" ");
  const up = pts[pts.length - 1].v >= pts[0].v, col = up ? "#22e39a" : "#ff4d6a";
  svg.innerHTML = `<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${col}" stop-opacity=".35"/><stop offset="1" stop-color="${col}" stop-opacity="0"/></linearGradient></defs>
    <path d="${d} L ${W} ${H} L 0 ${H} Z" fill="url(#g)"/><path d="${d}" fill="none" stroke="${col}" stroke-width="2.2" vector-effect="non-scaling-stroke"/>
    <circle cx="${xy[xy.length - 1][0]}" cy="${xy[xy.length - 1][1]}" r="4" fill="${col}"><animate attributeName="r" values="3;6;3" dur="1.6s" repeatCount="indefinite"/></circle>`; }

/* ---------------- renderers ---------------- */
function kpi(label, value, cls = "") { return `<div class="kpi"><label>${esc(label)}</label><div class="v ${cls}">${value}</div></div>`; }

function renderSnapshot(o) {
  lastMsg = Date.now(); $("live").classList.add("on");
  const live = o.mode === "LIVE";
  $("modeb").textContent = live ? "LIVE · REAL MONEY" : o.mode + " · " + (o.book || "").toUpperCase(); $("modeb").className = "pill" + (live ? " live" : "");
  $("sub").textContent = `${o.regime || "—"} regime · uptime ${ago(o.uptime_s)} · ${o.universe} markets`;
  // lights
  const L = o.lights || {}; $("lights").innerHTML = ["engine", "earning", "discovering", "brain", "feed", "safety"].map(k => L[k] ?
    `<div class="light ${L[k].state}"><i></i><span>${esc(L[k].label)}</span></div>` : "").join("");
  // hero
  const a = o.account || {}, b = o.book_balance || {}, inv = o.invested || {};
  setNum("acct", usd(a.coinbase_total_usd ?? b.equity_usd), a.coinbase_total_usd ?? b.equity_usd);
  setNum("book", usd(b.equity_usd), b.equity_usd); setNum("inv", `${usd(inv.market_value_usd)} · ${pct(inv.share_of_equity, 0)}`, inv.market_value_usd);
  setNum("cash", usd(b.cash_usd), b.cash_usd); $("doing").textContent = o.doing_now || "—";
  history.push({t: o.ts, v: b.equity_usd}); if (history.length > 2000) history.shift(); drawChart();
  // earnings windows
  const e = o.earnings || {};
  $("earn").innerHTML = [["1h", "Past hour"], ["8h", "Past 8 hours"], ["12h", "Past 12 hours"], ["24h", "Past 24 hours"]].map(([k, lab]) => {
    const w = e[k] || {}; return `<div class="earn"><label>${lab}</label><div class="v ${sgn(w.net_usd)}">${usd(w.net_usd, 4)}</div>
      <div class="s">avg ${usd(w.per_hour_usd, 4)}/h · ${w.trades || 0} trades</div><div class="s">trading ${usd(w.trading_net_usd, 4)} · costs ${usd(w.costs_usd, 4)}</div></div>`; }).join("");
  $("kpis").innerHTML = [
    kpi("Lifetime true net", usd(e.lifetime_true_net_usd, 4), sgn(e.lifetime_true_net_usd)), kpi("Return on capital", pct(b.roi), sgn(b.roi)),
    kpi("Realized", usd(e.realized_usd, 4), sgn(e.realized_usd)), kpi("Unrealized (live)", usd(e.unrealized_usd, 4), sgn(e.unrealized_usd)),
    kpi("Win rate", e.win_rate != null ? (100 * e.win_rate).toFixed(0) + "%" : "—"), kpi("Trades closed", e.trades_closed ?? 0),
    kpi("Exchange fees", usd(e.fees_usd, 4)), kpi("AI (DeepSeek)", usd(e.ai_usd, 4)), kpi("Compute (Modal)", usd(e.compute_usd, 4)),
    kpi("Protected reserve", usd(b.reserve_usd)), kpi("Capital in", usd(b.contributed_usd)), kpi("Fee tier", `${esc(o.fees.tier)} ${pct(o.fees.maker)}/${pct(o.fees.taker)}`)].join("");
  $("positions").innerHTML = (o.positions || []).map(p => `<div class="item"><div class="h"><b>${esc(p.symbol)} ${p.profit_locked ? "🔒" : ""}</b>
    <span class="${sgn(p.live_pnl_usd)}">${usd(p.live_pnl_usd, 4)} · ${pct(p.live_pnl_pct)}</span></div>
    <div class="muted tiny">${esc(p.status)} · cost ${usd(p.cost_usd)} · value ${usd(p.value_usd)} · price ${p.price ?? "—"} · ${esc(p.strategy)}</div></div>`).join("")
    || `<div class="muted">No open positions — capital waits for evidence-backed edge, then deploys automatically.</div>`;
  // workers
  $("workers").innerHTML = (o.workers || []).map(w => { const n = Math.max(0, w.count || 0), busy = n > 0;
    const dots = busy ? Array.from({length: Math.min(n, 32)}, () => "<i></i>").join("") : "<i class='off'></i>";
    return `<div class="worker ${busy ? "busy" : ""}"><div class="h"><b>${esc(w.name.replace("_", " ").toUpperCase())}</b><span class="tag ${busy ? "ACTIVE" : ""}">${busy ? n + " active" : "idle"}</span></div>
      <div class="dots">${dots}</div><div>${esc(w.what)}</div><div class="muted tiny">${esc(w.where || "")} · ${ago(w.elapsed_s)}</div></div>`; }).join("");
  $("loops").innerHTML = (o.loops || []).map(l => `<span class="chip ${l.alive && l.silent_s <= l.limit_s ? "ok" : "bad"}" title="${esc(l.last_error)}">${esc(l.loop)}${l.restarts ? " ↻" + l.restarts : ""}</span>`).join("");
  const I = o.intelligence || {}, C = o.compute || {}, S = o.deepseek_sentinel || {};
  $("intel").innerHTML = [kpi("DeepSeek balance", usd(I.balance_usd ?? S.balance)), kpi("AI spend today", `${usd(I.today_usd, 4)} / ${usd(I.daily_budget_usd, 2)}`),
    kpi("Brain tier", esc(I.tier || "—")), kpi("Modal this month", `${usd(C.month_usd)} / ${usd(C.budget_usd, 0)}`), kpi("Compute state", esc(C.state || "—")),
    kpi("Improvement cycles", o.improvement_cycles), kpi("Self-funding", S.self_funding && S.self_funding.coverage != null ? (100 * S.self_funding.coverage).toFixed(0) + "%" : "—")].join("");
  const br = o.breadth || {}, fd = o.feed || {};
  $("pulse").innerHTML = [kpi("Breadth (uptrend)", pct(br.up_frac, 0)), kpi("BTC regime", esc(br.btc_regime || "—")), kpi("Feed messages", (fd.messages || 0).toLocaleString()),
    kpi("Feed reconnects", fd.reconnects ?? 0), kpi("Markets watched", o.universe), kpi("Capital regime", esc(o.regime || "—"))].join("");
  if (S.status === "LOW") { $("refill").hidden = false; $("refill").textContent = `⚠ DeepSeek balance ${usd(S.balance)} — tap to add $10 (AI research throttled until funded)`; }
  else $("refill").hidden = true;
  $("foot").textContent = `live · updated ${new Date(o.ts * 1000).toLocaleTimeString()} · trading ${o.trading.state} · breakers ${(o.breakers || []).length}`; }

function renderLists(x) {
  const pop = (x.strategies || {}).counts || {};
  $("pop").innerHTML = Object.entries(pop).map(([k, v]) => `<span class="tag ${k}">${k} ${v}</span>`).join("");
  $("strats").innerHTML = ((x.strategies || {}).active || []).map(a => { const e = a.evidence || {}, f = a.forward || {};
    return `<div class="item"><div class="h"><b>${esc(a.family)}</b><span class="tag ${a.state}">${a.state}</span></div>
      <div class="muted tiny">${esc(a.id)} · gen ${a.generation} · forward ${f.n || 0} trades ${pct(f.mean_net)}</div>
      <div class="bar"><i style="width:${Math.round(100 * (e.p_edge || 0))}%"></i></div><div class="muted tiny">P(edge&gt;0) ${e.p_edge != null ? (100 * e.p_edge).toFixed(0) + "%" : "—"} · win ${e.p_win != null ? (100 * e.p_win).toFixed(0) + "%" : "—"}</div></div>`; }).join("")
    || `<div class="muted">Racing candidates toward the evidence gate — validated strategies appear here and start earning.</div>`;
  $("opps").innerHTML = (x.opportunities || []).map(o => { const c = o.components || {};
    return `<div class="item"><div class="h"><b>${esc(o.symbol)} · ${esc(o.family)}</b><span class="tag ${o.status}">${esc(o.status)}</span></div>
      <div class="muted tiny">p=${(+o.probability).toFixed(2)} · exp ${(+o.expected_net_bps).toFixed(0)}bps · ${pct(c.velocity_per_day)}/day vs hurdle ${pct(c.hurdle_per_day)}</div>
      <div class="muted tiny">${esc(o.reason || "")}${o.outcome ? " · outcome " + esc(o.outcome.outcome) + " " + pct(o.outcome.net) : ""}</div></div>`; }).join("") || `<div class="muted">Scanning every bar close…</div>`;
  $("rails").innerHTML = (x.rails || []).map(r => `<div class="item"><div class="h"><b>${esc(r.provider)}</b><span class="tag ${r.status}">${esc(r.status)}</span></div>
    <div>${esc(r.category)} — ${esc(r.edge)}</div>${r.needs && r.needs !== "—" ? `<div class="muted tiny">needs: ${esc(r.needs)}</div>` : ""}</div>`).join(""); }

function addTimeline(ev, prepend = true) {
  const div = document.createElement("div"); div.className = ev.level || "";
  div.innerHTML = `<time>${esc((ev.ts || "").slice(11, 19))}</time><b>${esc(ev.agent)}</b> — ${esc(ev.message)}`;
  const tl = $("timeline"); prepend ? tl.prepend(div) : tl.append(div); while (tl.children.length > 400) tl.lastChild.remove(); }

/* ---------------- live stream ---------------- */
function connect() {
  const es = new EventSource("/api/live", {withCredentials: true});
  es.addEventListener("snapshot", (m) => { try { renderSnapshot(JSON.parse(m.data)); } catch (e) { console.error(e); } });
  es.addEventListener("lists", (m) => { try { renderLists(JSON.parse(m.data)); } catch (e) {} });
  es.addEventListener("timeline", (m) => { try { addTimeline(JSON.parse(m.data)); } catch (e) {} });
  es.onerror = () => { $("live").classList.remove("on"); es.close(); setTimeout(connect, 2000); }; }
setInterval(() => { if (Date.now() - lastMsg > 5000) $("live").classList.remove("on"); }, 1000);

/* ---------------- controls ---------------- */
async function control(path, body, okMsg) { try { await api(path, {method: "POST", body: JSON.stringify(body)}); $("ctlmsg").textContent = okMsg; } catch (e) { $("ctlmsg").textContent = "Failed: " + e.message; } }
$("stop").onclick = () => { if (!confirm("STOP ALL TRADING now? New orders are blocked and pending entries cancelled.")) return;
  const flatten = confirm("Also close open positions when safe? (Cancel = keep protective exits running)");
  control("/api/control/stop", {reason: "founder emergency stop", flatten}, "Trading STOPPED."); };
$("resume").onclick = () => { const c = prompt("Type RESUME TRADING to resume:"); if (c) control("/api/control/resume", {confirm: c}, "Trading resumed."); };
$("cashout").onclick = () => { const a = prompt("Cash out how much USD? (number or 'all')", "all"); if (!a) return;
  const now = confirm("Urgent (market orders now)? Cancel = patient (maker orders, lower fees)"); control("/api/control/cashout", {amount: a, now}, "Cash-out requested."); };
$("logout").onclick = async () => { await fetch("/auth/logout", {method: "POST", credentials: "same-origin"}); location.href = "/login"; };

/* ---------------- boot ---------------- */
(async () => {
  try { const s = await api("/api/session"); CSRF = s.csrf; } catch (e) { return; }
  try { const h = await api("/api/history?hours=24"); history = h.map(r => ({t: Date.parse(r.ts) / 1000, v: r.equity_usd})); } catch (e) {}
  try { (await api("/api/timeline?limit=120")).reverse().forEach(ev => addTimeline(ev)); } catch (e) {}
  connect();
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
})();
