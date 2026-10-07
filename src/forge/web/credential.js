(async () => {
  const $ = (id) => document.getElementById(id);
  const r = new URLSearchParams(location.search).get("r") || "";
  sessionStorage.setItem("credq", "?r=" + encodeURIComponent(r));
  const res = await fetch("/api/setup/credential?r=" + encodeURIComponent(r));
  if (res.status === 401) { location.href = "/login?next=/setup/credential"; return; }
  const d = await res.json();
  if (!res.ok) { $("info").innerHTML = '<span class="err">' + (d.detail || "invalid link") + "</span>"; $("go").disabled = true; return; }
  $("info").innerHTML = "<b>" + d.name + "</b> — " + (d.purpose || "") + "<br>" + (d.kind === "pem" ? "Paste the whole key file (BEGIN … END)." : "Paste the value.") + " Link valid " + d.minutes_left + " min.";
  let csrf = ""; try { csrf = (await (await fetch("/api/session")).json()).csrf || ""; } catch (e) {}
  $("go").onclick = async () => {
    const v = $("val").value; $("msg").textContent = "Installing…";
    const p = await fetch("/api/setup/credential", { method: "POST", headers: { "Content-Type": "application/json", "x-csrf": csrf },
      body: JSON.stringify({ r: r, value: v }) });
    const j = await p.json(); $("val").value = "";
    $("msg").innerHTML = p.ok ? '<span class="ok">✅ Installed. Tell FORGE: "test the new connection".</span>' : '<span class="err">' + (j.detail || "error") + "</span>";
  };
})();
