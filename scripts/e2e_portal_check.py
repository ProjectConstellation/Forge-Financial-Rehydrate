"""Real-browser end-to-end check of the public founder portal (login → live data rendered)."""
import asyncio, json, sys, time
from playwright.async_api import async_playwright
URL = sys.argv[1] if len(sys.argv) > 1 else "https://forge.northstarimagine.com"
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 412, "height": 915}, device_scale_factor=2)
        errs = []
        pg.on("pageerror", lambda e: errs.append(f"pageerror: {e}"))
        pg.on("console", lambda m: errs.append(f"console.{m.type}: {m.text}") if m.type in ("error",) else None)
        await pg.goto(URL + "/login"); await pg.fill("#u", "northstaros"); await pg.fill("#p", "northstaros")
        await pg.click("button[type=submit]"); await pg.wait_for_url(URL + "/", timeout=15000)
        t0 = time.time()
        while time.time() - t0 < 25:
            if (await pg.text_content("#livetxt")) == "LIVE":
                break
            await asyncio.sleep(0.2)
        first_live = time.time() - t0
        await pg.wait_for_timeout(6000)
        vals = await pg.evaluate("""() => ({live: document.getElementById('livetxt').textContent, counter: document.getElementById('mcounter').textContent,
          account: document.getElementById('acct').textContent, invested: document.getElementById('inv').textContent, cash: document.getElementById('cash').textContent,
          doing: document.getElementById('doing').textContent, health: document.getElementById('h_overall').textContent, organism: document.getElementById('h_state').textContent,
          systems: document.querySelectorAll('#systems .sys').length, positions: document.getElementById('positions').innerText.slice(0,200),
          earn: [...document.querySelectorAll('#earn .earn .v')].map(e => e.textContent), foot: document.getElementById('foot').textContent})""")
        await pg.screenshot(path="/srv/forge/.tools/portal-shot.png", full_page=False)
        print(json.dumps({"first_live_s": round(first_live, 2), **vals, "js_errors": errs[:5]}, indent=1))
        await b.close()
asyncio.run(main())
