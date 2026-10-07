"use strict";
document.getElementById("f").addEventListener("submit", async (e) => {
  e.preventDefault(); const err = document.getElementById("err"); err.textContent = "";
  try {
    const r = await fetch("/auth/login", {method: "POST", headers: {"Content-Type": "application/json"}, credentials: "same-origin",
      body: JSON.stringify({username: document.getElementById("u").value, password: document.getElementById("p").value})});
    if (!r.ok) { err.textContent = (await r.json()).detail || "Sign-in failed"; return; }
    location.href = "/";
  } catch (x) { err.textContent = "Network error"; }
});
