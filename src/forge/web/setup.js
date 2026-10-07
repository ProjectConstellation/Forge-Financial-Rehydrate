(async () => {
  const $ = (id) => document.getElementById(id);
  let csrf = "";
  try { csrf = (await (await fetch("/api/session")).json()).csrf || ""; } catch (e) {}
  async function poll() {
    const r = await fetch("/api/setup/telegram");
    if (r.status === 401) { location.href = "/login"; return; }
    const d = await r.json();
    if (d.connected) {
      $("flow").hidden = true; $("connected").hidden = false;
      $("connInfo").textContent = "Bot @" + d.connected.bot_username + " answers only " + (d.connected.owner_first_name || "you") + ".";
      $("openBot").href = "https://t.me/" + d.connected.bot_username;
      return;
    }
    const p = d.pairing || {};
    if (p.state === "waiting") { $("s4").hidden = false; $("link").href = p.deep_link; }
    if (p.state === "expired" || p.state === "error") { $("msg").innerHTML = '<span class="err">' + (p.note || p.state) + "</span>"; }
    setTimeout(poll, 2500);
  }
  $("go").onclick = async () => {
    $("msg").textContent = "Checking with Telegram…";
    const r = await fetch("/api/setup/telegram", { method: "POST", headers: { "Content-Type": "application/json", "x-csrf": csrf },
      body: JSON.stringify({ token: $("tok").value.trim(), replace: true }) });
    const d = await r.json();
    if (!r.ok) { $("msg").innerHTML = '<span class="err">' + (d.detail || "error") + "</span>"; return; }
    $("tok").value = ""; $("msg").innerHTML = '<span class="ok">Bot @' + d.bot_username + " verified.</span>";
    $("s4").hidden = false; $("link").href = d.deep_link;
  };
  poll();
})();
