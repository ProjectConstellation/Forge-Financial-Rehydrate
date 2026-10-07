"use strict";
const $ = (id) => document.getElementById(id);
const usd = (x, d = 2) => (x == null || isNaN(x)) ? "—" : (x < 0 ? "-$" : "$") + Math.abs(+x).toFixed(d);
const pct = (x, d = 2) => (x == null || isNaN(x)) ? "—" : (x >= 0 ? "+" : "") + (100 * x).toFixed(d) + "%";
const cls = (x) => x > 0 ? "pos" : x < 0 ? "neg" : "";
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const token = () => localStorage.getItem("forge_token") || "";
async function api(path, opts = {}) {
  const r = await fetch(path, {...opts, headers: {"Content-Type": "application/json", ...(token() ? {Authorization: "Bearer " + token()} : {}), ...(opts.headers || {})}});
  if (!r.ok) throw new Error(r.status + " " + (await r.text()));
  return r.json();
}
function kpi(label, value, c = "") { return `<div class="kpi"><label>${esc(label)}</label><div class="v ${c}">${value}</div></div>`; }

async function refresh() {
  try {
    const o = await api("/api/overview");
    const t = o.treasury || {}, reg = t.regime || {}, ts = (o.trading || {}).state;
    $("mode").textContent = o.mode + (o.mode === "LIVE" ? " · REAL MONEY" : "");
    $("mode").className = "badge " + (o.mode === "LIVE" ? "live" : "paper");
    $("tstate").textContent = ts; $("tstate").className = "badge " + (ts === "STOPPED" ? "stopped" : ts === "OBSERVE_ONLY" ? "observe" : "");
    $("equity").textContent = usd(t.equity_usd);
    $("regime").textContent = `${reg.name || "—"} regime · reserve ${usd(t.reserve_usd)} · cash ${usd(t.cash_usd)}`;
    $("truenet").textContent = usd(t.true_net_usd, 4); $("truenet").className = "num " + cls(t.true_net_usd);
    $("truenet_sub").textContent = `realized ${usd(t.realized_pnl_usd, 4)} · unrealized ${usd(t.unrealized_pnl_usd, 4)} · today ${usd(t.daily_pnl_usd, 4)}`;
    const intel = o.intelligence || {}, comp = o.compute || {};
    $("kpis").innerHTML = [
      kpi("Deployed", usd(t.deployed_usd)), kpi("Exchange fees", usd(t.fees_usd, 4)),
      kpi("DeepSeek spend", usd(t.opex_inference_usd, 4)), kpi("Modal spend", usd(t.opex_compute_usd, 4)),
      kpi("DeepSeek balance", intel.balance_usd != null ? usd(intel.balance_usd) : "—"),
      kpi("Modal month", comp.month_usd != null ? `${usd(comp.month_usd)} / ${usd(comp.budget_usd, 0)}` : "—"),
      kpi("Hurdle / day", pct(o.hurdle_per_day)), kpi("Markets watched", o.universe),
      kpi("Opportunities 24h", o.opportunities_24h), kpi("Open positions", (o.positions || []).length),
      kpi("Improvement cycles", o.improvement_cycles), kpi("Fees (" + esc(o.fees.tier) + ")", pct(o.fees.maker) + " / " + pct(o.fees.taker)),
    ].join("");
    $("agents").innerHTML = Object.entries(o.agents || {}).map(([k, v]) => `<div><b>${esc(k)}</b><span>${esc(v.text)}</span></div>`).join("") || '<span class="muted">starting…</span>';
    $("positions").innerHTML = (o.positions || []).map(p => `<div class="posn"><b>${esc(p.symbol)}</b> ${esc(p.status)} · qty ${(+p.qty).toPrecision(6)} · cost ${usd(p.cost_usd)} <span class="muted">${esc(p.strategy_id)}</span></div>`).join("") || '<span class="muted">No open positions — capital waits for evidence-backed edge.</span>';
    $("pop").innerHTML = Object.entries(o.population || {}).map(([k, v]) => `<span class="tag ${k}">${k} ${v}</span>`).join("");
    $("foot").textContent = `uptime ${Math.round(o.uptime_s / 60)} min · feed ${o.feed.connected ? "live" : "DOWN"} · ${o.feed.messages} msgs · breakers ${(o.breakers || []).length}`;
  } catch (e) { $("foot").textContent = "API error: " + e.message; }
  try {
    const opps = await api("/api/opportunities?limit=25");
    $("opps").innerHTML = opps.map(x => { const c = x.components || {};
      return `<div class="opp"><div class="h"><b>${esc(x.symbol)} · ${esc(x.family)}</b><span class="tag ${x.status}">${esc(x.status)}</span></div>
      <div class="muted">p=${(+x.probability).toFixed(2)} · exp ${(+x.expected_net_bps).toFixed(0)}bps · velocity ${pct(c.velocity_per_day)}/day vs hurdle ${pct(c.hurdle_per_day)} · half-life ${Math.round((c.half_life_s || 0) / 60)}m</div>
      <div class="muted">${esc(x.reason || "")}${x.outcome ? " · outcome " + esc(x.outcome.outcome) + " " + pct(x.outcome.net) : ""}</div></div>`; }).join("") || '<span class="muted">Scanning…</span>';
    const s = await api("/api/strategies");
    $("strats").innerHTML = (s.active || []).map(a => { const e = a.evidence || {}, f = a.forward || {};
      return `<div class="strat"><div class="h"><b>${esc(a.family)}</b><span class="tag ${a.state}">${a.state}</span></div>
      <div class="muted">${esc(a.id)} · gen ${a.generation} · P(edge>0) ${e.p_edge != null ? e.p_edge.toFixed(2) : "—"} · win ${e.p_win != null ? (100 * e.p_win).toFixed(0) + "%" : "—"} · forward n=${f.n || 0} ${pct(f.mean_net)}</div></div>`; }).join("") || '<span class="muted">No strategy has passed the 90% evidence gate yet — the Improvement Loop is evolving candidates continuously.</span>';
  } catch (e) {}
}
async function loadTimeline() {
  try {
    const rows = await api("/api/timeline?limit=80");
    $("timeline").innerHTML = rows.map(r => `<div class="${esc(r.level)}"><time>${esc(r.ts.slice(11, 19))}</time><b>${esc(r.agent)}</b> — ${esc(r.message)}</div>`).join("");
  } catch (e) {}
}
function stream() {
  const es = new EventSource("/api/stream");
  es.onmessage = (m) => { try { const e = JSON.parse(m.data);
    const div = document.createElement("div"); div.className = e.level;
    div.innerHTML = `<time>${esc(e.ts.slice(11, 19))}</time><b>${esc(e.agent)}</b> — ${esc(e.message)}`;
    $("timeline").prepend(div); } catch (_) {} };
  es.onerror = () => { es.close(); setTimeout(stream, 5000); };
}
$("token").onclick = () => { const t = prompt("Operator token (stored on this device only):", token()); if (t !== null) localStorage.setItem("forge_token", t.trim()); };
$("stop").onclick = async () => {
  if (!confirm("STOP ALL TRADING now? New orders are blocked and pending entries cancelled.")) return;
  const flatten = confirm("Also flatten open positions when safe? (Cancel = keep protective exits)");
  try { await api("/api/control/stop", {method: "POST", body: JSON.stringify({reason: "dashboard emergency stop", flatten})}); refresh(); alert("Trading STOPPED."); }
  catch (e) { alert("Stop failed: " + e.message + "\nSet the operator token first, or run `forge stop-all` on the server."); }
};
$("resume").onclick = async () => {
  const c = prompt("Type RESUME TRADING to resume:"); if (!c) return;
  try { await api("/api/control/resume", {method: "POST", body: JSON.stringify({confirm: c})}); refresh(); } catch (e) { alert(e.message); }
};
$("cashout").onclick = async () => {
  const a = prompt("Cash out how much USD? (number or 'all')", "all"); if (!a) return;
  const now = confirm("Urgent (market orders now)? Cancel = patient (maker orders, lower fees)");
  try { await api("/api/control/cashout", {method: "POST", body: JSON.stringify({amount: a, now})}); alert("Cash-out requested."); } catch (e) { alert(e.message); }
};
if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
refresh(); loadTimeline(); stream(); setInterval(refresh, 5000);
