"use strict";
document.getElementById("f").addEventListener("submit", async (e) => {
  e.preventDefault(); const err = document.getElementById("err"); err.textContent = "";
  try {
    const r = await fetch("/auth/login", {method: "POST", headers: {"Content-Type": "application/json"}, credentials: "same-origin",
      body: JSON.stringify({username: document.getElementById("u").value, password: document.getElementById("p").value})});
    if (!r.ok) { err.textContent = (await r.json()).detail || "Sign-in failed"; return; }
    const nxt = new URLSearchParams(location.search).get("next");
    location.href = (nxt === "/setup" || nxt === "/setup/credential") ? (nxt === "/setup" ? "/setup" : "/setup/credential" + (sessionStorage.getItem("credq") || "")) : "/";   // fixed allowlist (no open redirect)
  } catch (x) { err.textContent = "Network error"; }
});
