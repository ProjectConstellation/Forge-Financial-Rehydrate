/* FORGE founder portal v3 — all numbers are pushed by the engine every second (SSE /api/live). Nothing is invented client-side. */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  const usd = (x, d = 2) => (x == null || isNaN(x)) ? "—" : (x < 0 ? "−$" : "$") + Math.abs(+x).toLocaleString(undefined, {minimumFractionDigits: d, maximumFractionDigits: d});
  const pct = (x, d = 1) => (x == null || isNaN(x)) ? "—" : (x >= 0 ? "+" : "−") + Math.abs(100 * x).toFixed(d) + "%";
  const sgn = (x) => x > 0 ? "pos" : x < 0 ? "neg" : "";
  const ago = (s) => s == null ? "—" : s < 60 ? `${s}s` : s < 3600 ? `${Math.floor(s / 60)}m` : `${Math.floor(s / 3600)}h ${Math.floor(s % 3600 / 60)}m`;
  const fmtN = (n) => (n ?? 0).toLocaleString();

  let CSRF = null, equitySeries = [], lastSnapAt = 0, prevMsgs = null, prevTs = null;
  const msgRate = [], counter = {shown: 0, target: 0, raf: 0};

  async function api(path, opts = {}) {
    const r = await fetch(path, {credentials: "same-origin", ...opts,
      headers: {"Content-Type": "application/json", ...(CSRF ? {"X-CSRF": CSRF} : {}), ...(opts.headers || {})}});
    if (r.status === 401) { location.href = "/login"; throw new Error("login required"); }
    if (!r.ok) throw new Error((await r.text()).slice(0, 200));
    return r.json();
  }

  /* ---------- money counter: smooth tween + coin burst on genuine increases ---------- */
  function setCounter(v) {
    const el = $("mcounter");
    if (v > counter.target + 0.00005 && counter.target !== 0) { burst(); el.classList.remove("bump"); void el.offsetWidth; el.classList.add("bump"); }
    counter.target = v;
    cancelAnimationFrame(counter.raf);
    const from = counter.shown, t0 = performance.now(), dur = 800;
    const step = (now) => {
      const k = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - k, 3);
      counter.shown = from + (v - from) * e;
      const d = Math.abs(counter.shown) < 10 ? 4 : 2;
      el.textContent = usd(counter.shown, d);
      el.parentElement.classList.toggle("neg", counter.shown < 0);
      if (k < 1) counter.raf = requestAnimationFrame(step);
    };
    counter.raf = requestAnimationFrame(step);
  }
  function burst() {
    const box = $("coins");
    for (let i = 0; i < 7; i++) {
      const c = document.createElement("span"); c.className = "coin"; c.textContent = i % 2 ? "💰" : "💵";
      c.style.left = (35 + Math.random() * 30) + "%"; c.style.animationDelay = (i * 60) + "ms";
      box.appendChild(c); setTimeout(() => c.remove(), 1600);
    }
  }

  /* ---------- chart ---------- */
  function drawChart() {
    const svg = $("chart"), pts = equitySeries.filter(p => p.v != null);
    if (pts.length < 2) { svg.innerHTML = ""; return; }
    const W = 600, H = 120, vals = pts.map(p => p.v), min = Math.min(...vals), max = Math.max(...vals);
    const span = (max - min) || Math.max(0.01, Math.abs(max) * 0.001), t0 = pts[0].t, t1 = pts[pts.length - 1].t;
    const xy = pts.map(p => [((p.t - t0) / Math.max(1, t1 - t0)) * W, H - 8 - ((p.v - min) / span) * (H - 16)]);
    const d = xy.map((q, i) => (i ? "L" : "M") + q[0].toFixed(1) + " " + q[1].toFixed(1)).join(" ");
    const col = vals[vals.length - 1] >= vals[0] ? "#ffc83d" : "#ff8aa0", last = xy[xy.length - 1];
    svg.innerHTML = `<defs><linearGradient id="cg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${col}" stop-opacity=".35"/><stop offset="1" stop-color="${col}" stop-opacity="0"/></linearGradient></defs>
      <path d="${d} L ${W} ${H} L 0 ${H} Z" fill="url(#cg)"/><path d="${d}" fill="none" stroke="${col}" stroke-width="2" vector-effect="non-scaling-stroke"/>
      <circle cx="${last[0]}" cy="${last[1]}" r="4" fill="${col}"><animate attributeName="r" values="3;6;3" dur="1.4s" repeatCount="indefinite"/></circle>`;
  }

  /* ---------- live systems ---------- */
  const meter = (arr, max) => `<div class="meter">${Array.from({length: 24}, (_, i) => {
    const v = arr[arr.length - 24 + i]; const h = v == null ? 2 : Math.max(2, Math.min(16, 16 * v / Math.max(max, 1e-9)));
    return `<i style="height:${h}px"></i>`; }).join("")}</div>`;
  function sys(state, name, status, detail, metric, extra = "") {
    return `<div class="sys ${state}"><div class="h"><i></i><b>${esc(name)}</b><span class="st">${esc(status)}</span></div>
      <div class="d">${esc(detail)}</div><div class="m">${esc(metric)}</div>${extra}</div>`;
  }
  function renderSystems(o) {
    const L = o.lights || {}, T = o.throughput || {}, W = Object.fromEntries((o.workers || []).map(w => [w.name, w]));
    const loops = o.loops || [], alive = loops.filter(l => l.alive && (l.limit_s == null || l.silent_s <= l.limit_s)).length;
    const restarts = loops.reduce((a, l) => a + (l.restarts || 0), 0);
    const pop = o.population || {}, validated = (pop.PRODUCTION || 0) + (pop.CHALLENGER || 0) + (o.book === "paper" ? (pop.SHADOW || 0) : 0);
    const rate = msgRate.length ? msgRate[msgRate.length - 1] : 0;
    const modal = W.modal || {}, research = W.research || {}, brain = W.brain || {};
    const evoBusy = (modal.count || 0) + (research.count || 0);
    $("systems").innerHTML = [
      sys(L.feed?.state || "amber", "Market Feed", L.feed?.state === "green" ? "LIVE" : "DOWN",
        `Streaming ${T.markets_streaming || 0} markets (${T.markets_discovered || 0} discovered)`, `${rate.toFixed(1)} msgs/s · ${fmtN(T.feed_messages)} total`,
        meter(msgRate, Math.max(...msgRate.slice(-24), 1))),
      sys(validated ? "green" : "blue", "Strategy Hunters", validated ? "HUNTING" : "WARMING UP",
        `${validated} validated strategies scan every bar close`, `${fmtN(T.opportunities_24h)} signals scored in 24h`),
      sys(L.earning?.state || "blue", "Trading Desk", (o.positions || []).length ? "IN MARKET" : (o.trading?.state || "—"),
        `${(o.book || "").toUpperCase()} book · ${(o.positions || []).length} positions · profit-lock armed`, L.earning?.label || ""),
      sys(evoBusy ? "green" : (L.discovering?.state || "amber"), "Evolution Lab", evoBusy ? `${evoBusy} WORKERS` : "BETWEEN CYCLES",
        modal.count ? `${modal.count} Modal workers · ${modal.what} · ${ago(modal.elapsed_s)}` : (research.what || "preparing next tournament"),
        `${fmtN(T.genomes_last_cycle)} genomes last cycle · ${fmtN(T.genomes_total)} total · ${T.cycles || 0} cycles`),
      sys(brain.count ? "green" : (L.brain?.state || "amber"), "DeepSeek Brain", brain.count ? "THINKING" : "STANDBY",
        brain.what || "waiting for next perception", L.brain?.label || ""),
      sys(L.safety?.state || "amber", "Risk Governor", L.safety?.label || "—", "Every order passes deterministic checks · stops + profit locks",
        `${(o.breakers || []).length} breakers tripped`),
      sys(alive === loops.length && loops.length ? "green" : "red", "Supervisor", `${alive}/${loops.length} LOOPS`,
        "Auto-restarts any stalled loop · systemd watchdog", `${restarts} restarts · uptime ${ago(o.uptime_s)}`),
      sys("green", "Learning Engine", "LEARNING", "Scores every opportunity after its horizon · calibrates confidence",
        `regime ${o.regime || "—"} · breadth ${pct(o.breadth?.up_frac, 0)} up`),
    ].join("");
  }

  /* ---------- snapshot ---------- */
  function renderSnapshot(o) {
    lastSnapAt = Date.now();
    $("livepill").className = "livepill on"; $("livetxt").textContent = "LIVE";
    const live = o.mode === "LIVE";
    $("modeb").textContent = live ? "LIVE · REAL MONEY" : o.mode === "PAPER" ? "PAPER TRADING" : o.mode;
    $("modeb").className = "pill" + (live ? " live" : "");
    if (prevMsgs != null && o.ts > prevTs) { msgRate.push(Math.max(0, ((o.throughput?.feed_messages || 0) - prevMsgs) / (o.ts - prevTs))); if (msgRate.length > 120) msgRate.shift(); }
    prevMsgs = o.throughput?.feed_messages || 0; prevTs = o.ts;
    const td = o.today || {}, forged = (td.realized_net_usd || 0) + (td.unrealized_usd || 0);
    setCounter(forged);
    $("m_real").textContent = usd(td.realized_net_usd, 4); $("m_open").textContent = usd(td.unrealized_usd, 4);
    $("m_pace").textContent = usd((o.earnings?.["1h"] || {}).per_hour_usd, 4);
    const a = o.account || {}, b = o.book_balance || {}, inv = o.invested || {};
    $("acct").textContent = usd(a.coinbase_total_usd ?? b.equity_usd);
    $("inv").textContent = usd(inv.market_value_usd); $("inv_s").textContent = `${inv.positions || 0} positions · ${pct(inv.share_of_equity, 0)} of book`;
    $("cash").textContent = usd(b.cash_usd); $("res_s").textContent = `reserve ${usd(b.reserve_usd)}`;
    $("doing").textContent = o.doing_now || "—";
    equitySeries.push({t: o.ts, v: b.equity_usd}); if (equitySeries.length > 3000) equitySeries.shift(); drawChart();
    renderSystems(o);
    const H = o.health || {};
    if (H.overall != null) {
      const ring = $("ringfg"), C = 326.7, col = H.overall >= 85 ? "#22e39a" : H.overall >= 60 ? "#ffb547" : "#ff4d6a";
      ring.style.strokeDashoffset = String(C * (1 - H.overall / 100)); ring.style.stroke = col;
      $("h_overall").textContent = H.overall; $("h_state").textContent = H.organism || "—"; $("h_state").className = "pill " + (H.organism || "").split(" ")[0];
      $("h_meta").textContent = `loop lag ${H.lag_ms}ms · ${H.rss_mb}MB · bench ${H.bench} ready · AI ${H.ai_circuit?.state || "—"} · Modal ${H.modal_circuit?.state || "—"}` +
        (H.quarantined?.length ? ` · quarantined ${H.quarantined.join(", ")}` : "");
      const names = {system: "System", feed: "Feed", execution: "Execution", strategy: "Strategy", ai: "AI", treasury: "Treasury"};
      $("h_parts").innerHTML = Object.entries(H.parts || {}).map(([k, v]) => `<div class="hpart"><label>${names[k] || k} · ${v}</label>
        <div class="bar"><i style="width:${v}%;background:${v >= 85 ? "linear-gradient(90deg,#0f7a55,#22e39a)" : v >= 60 ? "linear-gradient(90deg,#8a5a10,#ffb547)" : "linear-gradient(90deg,#7a1020,#ff4d6a)"}"></i></div></div>`).join("");
    }
    const e = o.earnings || {};
    $("earn").innerHTML = [["1h", "Past hour"], ["8h", "Past 8 hours"], ["12h", "Past 12 hours"], ["24h", "Past 24 hours"]].map(([k, lab]) => {
      const w = e[k] || {};
      return `<div class="earn"><label>${lab}</label><div class="v ${sgn(w.net_usd)}">${usd(w.net_usd, 4)}</div>
        <div class="s">avg ${usd(w.per_hour_usd, 4)}/h · ${w.trades || 0} trades</div></div>`; }).join("");
    $("positions").innerHTML = (o.positions || []).map(p => `<div class="item"><div class="h"><b>${esc(p.symbol)} ${p.profit_locked ? "🔒" : ""}</b>
      <span class="${sgn(p.live_pnl_usd)}">${usd(p.live_pnl_usd, 4)} · ${pct(p.live_pnl_pct, 2)}</span></div>
      <div class="muted tiny">${esc(p.status)} · cost ${usd(p.cost_usd)} · now ${usd(p.value_usd)} · ${esc(p.strategy)}</div></div>`).join("")
      || `<div class="muted">No open positions this moment — validated strategies enter automatically on their next signal.</div>`;
    const TL = o.testing || {}, HO = TL.holdout || {};
    const k2 = (l, v, c = "") => `<div class="kpi"><label>${esc(l)}</label><div class="v ${c}">${v}</div></div>`;
    if (HO.final_usd != null) {
      $("lab").innerHTML = [k2("Replay result", `${usd(TL.capital)} → ${usd(HO.final_usd)}`, sgn(HO.net_usd)), k2("Return (unseen days)", pct(HO.return, 1), sgn(HO.return)),
        k2("Per-day compounding", pct(HO.daily_compound_rate, 2), sgn(HO.daily_compound_rate)), k2("Profit factor", (HO.profit_factor ?? 0).toFixed(2)),
        k2("Max drawdown", pct(HO.max_drawdown, 1)), k2("Profitable days", HO.positive_days != null ? (100 * HO.positive_days).toFixed(0) + "%" : "—"),
        k2("Trades replayed", HO.trades), k2("Win rate", HO.win_rate != null ? (100 * HO.win_rate).toFixed(0) + "%" : "—")].join("");
      const EH = TL.elite_holdout || {};
      if (EH.return != null) $("lab").innerHTML += k2("Elite portfolio (unseen)", `${pct(EH.return, 1)} · PF ${(EH.profit_factor ?? 0).toFixed(2)}`, sgn(EH.return));
      $("lab_note").textContent = `elite: ${(TL.elite || []).length} strategies with full capital · ${TL.strategies} strategies × ${TL.markets} markets · ${(HO.days || 0).toFixed(0)} unseen days · replayed in ${(TL.seconds || 0).toFixed(0)}s · ${new Date((TL.ts || 0) * 1000).toLocaleTimeString()}`;
    } else { $("lab").innerHTML = ""; $("lab_note").textContent = "First full-system replay runs within minutes of startup."; }
    const I = o.intelligence || {}, C = o.compute || {}, S = o.deepseek_sentinel || {};
    const kpi = (l, v, c = "") => `<div class="kpi"><label>${esc(l)}</label><div class="v ${c}">${v}</div></div>`;
    $("kpis").innerHTML = [kpi("Lifetime true net", usd(e.lifetime_true_net_usd, 4), sgn(e.lifetime_true_net_usd)), kpi("Return on capital", pct(b.roi, 2), sgn(b.roi)),
      kpi("Win rate", e.win_rate != null ? (100 * e.win_rate).toFixed(0) + "%" : "—"), kpi("Trades closed", e.trades_closed ?? 0),
      kpi("Exchange fees", usd(e.fees_usd, 4)), kpi("AI (DeepSeek)", usd(e.ai_usd, 4)), kpi("Compute (Modal)", usd(e.compute_usd, 4)),
      kpi("DeepSeek balance", usd(I.balance_usd ?? S.balance)), kpi("AI budget today", `${usd(I.today_usd, 3)} / ${usd(I.daily_budget_usd, 2)}`),
      kpi("Modal month", `${usd(C.month_usd)} / ${usd(C.budget_usd, 0)}`), kpi("Fee tier", `${esc(o.fees?.tier)} ${pct(o.fees?.maker, 2)}/${pct(o.fees?.taker, 2)}`)].join("");
    $("loops").innerHTML = (o.loops || []).map(l => `<span class="chip ${l.alive && (l.limit_s == null || l.silent_s <= l.limit_s) ? "ok" : "bad"}" title="${esc(l.last_error)}">${esc(l.loop)}${l.restarts ? " ↻" + l.restarts : ""}</span>`).join("");
    const br = o.breadth || {}, fd = o.feed || {};
    $("pulse").innerHTML = [kpi("Breadth (uptrend)", pct(br.up_frac, 0)), kpi("BTC regime", esc(br.btc_regime || "—")), kpi("Capital regime", esc(o.regime || "—")),
      kpi("Feed reconnects", fd.reconnects ?? 0), kpi("Markets streaming", o.throughput?.markets_streaming ?? "—"), kpi("Opportunities 24h", o.throughput?.opportunities_24h ?? 0)].join("");
    if (S.status === "LOW") { $("refill").hidden = false; $("refill").textContent = `⚠ DeepSeek balance ${usd(S.balance)} — tap to add $10 (AI research throttled)`; } else $("refill").hidden = true;
    $("sub").textContent = `${o.regime || "—"} regime · ${o.throughput?.markets_streaming || 0} live markets`;
    $("foot").textContent = `pushed live by the engine · ${new Date(o.ts * 1000).toLocaleTimeString()} · trading ${o.trading?.state}`;
  }

  function renderLists(x) {
    const pop = (x.strategies || {}).counts || {};
    $("pop").innerHTML = Object.entries(pop).map(([k, v]) => `<span class="tag ${k}">${k} ${v}</span>`).join("");
    const AN = Object.fromEntries(((x.analyst || {}).strategies || []).map(r => [r.id, r]));
    $("strats").innerHTML = ((x.strategies || {}).active || []).map(a => { const e = a.evidence || {}, f = a.forward || {}, r = AN[a.id] || {};
      return `<div class="item"><div class="h"><b>${esc(a.family)}</b><span class="tag ${a.state}">${a.state}</span></div>
        <div class="muted tiny">${esc(a.id)} · gen ${a.generation} · live-forward ${f.n || 0} trades ${pct(f.mean_net, 2)}</div>
        <div class="bar"><i style="width:${Math.round(100 * (e.p_edge || 0))}%"></i></div>
        <div class="muted tiny">P(edge&gt;0) ${e.p_edge != null ? (100 * e.p_edge).toFixed(0) + "%" : "—"} · win ${e.p_win != null ? (100 * e.p_win).toFixed(0) + "%" : "—"}</div></div>`; }).join("")
      || `<div class="muted">Racing candidates toward the evidence gate.</div>`;
    $("opps").innerHTML = (x.opportunities || []).map(o => { const c = o.components || {};
      return `<div class="item"><div class="h"><b>${esc(o.symbol)} · ${esc(o.family)}</b><span class="tag ${o.status}">${esc(o.status)}</span></div>
        <div class="muted tiny">p=${(+o.probability).toFixed(2)} · exp ${(+o.expected_net_bps).toFixed(0)}bps · ${pct(c.velocity_per_day, 2)}/day vs hurdle ${pct(c.hurdle_per_day, 2)}</div>
        <div class="muted tiny">${esc(o.reason || "")}${o.outcome ? " · outcome " + esc(o.outcome.outcome) + " " + pct(o.outcome.net, 2) : ""}</div></div>`; }).join("")
      || `<div class="muted">Scanning every bar close…</div>`;
    $("rails").innerHTML = (x.rails || []).map(r => `<div class="item"><div class="h"><b>${esc(r.provider)}</b><span class="tag ${r.status}">${esc(r.status)}</span></div>
      <div>${esc(r.category)} — ${esc(r.edge)}</div>${r.needs && r.needs !== "—" ? `<div class="muted tiny">needs: ${esc(r.needs)}</div>` : ""}</div>`).join("");
  }

  function addFeed(ev) {
    const div = document.createElement("div"); div.className = ev.level || "";
    div.innerHTML = `<time>${esc((ev.ts || "").slice(11, 19))}</time><b>${esc(ev.agent)}</b> — ${esc(ev.message)}`;
    const tl = $("timeline"); tl.prepend(div); while (tl.children.length > 400) tl.lastChild.remove();
  }

  /* ---------- live stream ---------- */
  function connect() {
    const es = new EventSource("/api/live");
    es.addEventListener("snapshot", (m) => { try { renderSnapshot(JSON.parse(m.data)); } catch (err) { console.error("snapshot", err); } });
    es.addEventListener("lists", (m) => { try { renderLists(JSON.parse(m.data)); } catch (err) { console.error("lists", err); } });
    es.addEventListener("timeline", (m) => { try { addFeed(JSON.parse(m.data)); } catch (err) {} });
    es.onerror = () => { es.close(); setTimeout(connect, 2000); };
  }
  setInterval(() => { if (Date.now() - lastSnapAt > 5000) { $("livepill").className = "livepill off"; $("livetxt").textContent = lastSnapAt ? "RECONNECTING" : "CONNECTING"; } }, 1000);

  /* ---------- tabs & controls ---------- */
  $("tabs").addEventListener("click", (e) => { const t = e.target.dataset.t; if (!t) return;
    document.querySelectorAll(".tabs button").forEach(b => b.classList.toggle("on", b.dataset.t === t));
    document.querySelectorAll(".tab").forEach(x => x.classList.toggle("on", x.id === "t-" + t)); });
  async function control(path, body, ok) { try { await api(path, {method: "POST", body: JSON.stringify(body)}); $("ctlmsg").textContent = ok; } catch (e) { $("ctlmsg").textContent = "Failed: " + e.message; } }
  $("stop").onclick = () => { if (!confirm("STOP ALL TRADING now? New orders blocked; pending entries cancelled.")) return;
    control("/api/control/stop", {reason: "founder emergency stop", flatten: confirm("Also close open positions when safe? (Cancel = keep protective exits)")}, "Trading STOPPED."); };
  $("resume").onclick = () => { const c = prompt("Type RESUME TRADING to resume:"); if (c) control("/api/control/resume", {confirm: c}, "Trading resumed."); };
  $("cashout").onclick = () => { const a = prompt("Cash out how much USD? (number or 'all')", "all"); if (!a) return;
    control("/api/control/cashout", {amount: a, now: confirm("Urgent (market orders now)? Cancel = patient (lower fees)")}, "Cash-out requested."); };
  $("logout").onclick = async () => { await fetch("/auth/logout", {method: "POST", credentials: "same-origin"}); location.href = "/login"; };

  /* ---------- boot ---------- */
  (async () => {
    try { CSRF = (await api("/api/session")).csrf; } catch (e) { return; }
    connect();                                                   // live data first
    try { equitySeries = (await api("/api/history?hours=24")).map(r => ({t: Date.parse(r.ts) / 1000, v: r.equity_usd})); drawChart(); } catch (e) {}
    try { (await api("/api/timeline?limit=150")).reverse().forEach(addFeed); } catch (e) {}
    if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
  })();
})();
