"""Login via real browser (Playwright), capture the resulting session cookies + localStorage,
and write them to disk for re-use by HTTP-only crawlers.
"""
import json
from pathlib import Path
from scrapling.fetchers import StealthySession

OUT = Path(r"D:\kaifa\gaokao\crawled")
USERNAME = "1255330251@qq.com"
PASSWORD = "zsl13177068887"
LOGIN_PAGE = "https://agentsfeed.org/auth/signin"
TARGET = "https://agentsfeed.org/app-demo/gaokao-map"

with StealthySession(headless=True) as s:
    page = s.context.new_page()
    page.goto(LOGIN_PAGE, wait_until="networkidle")
    page.wait_for_timeout(2500)

    page.fill('input[type=text]', USERNAME)
    page.fill('input[type=password]', PASSWORD)
    page.click('button[type=submit]')

    # Wait until we're no longer on /auth/signin
    try:
        page.wait_for_url(lambda u: "/auth/signin" not in u, timeout=20000)
        print("Navigated to:", page.url)
    except Exception:
        print("Stayed on:", page.url, "- waiting more")
        page.wait_for_timeout(5000)

    # Capture state
    cookies = []
    for c in s.context.cookies():
        cookies.append({"name": c["name"], "value": c["value"], "domain": c["domain"], "path": c["path"]})
    print("Cookies captured:", len(cookies))
    for c in cookies:
        print(" -", c["name"], "=", c["value"][:24] + ("..." if len(c["value"]) > 24 else ""))

    storage = page.evaluate("""() => {
      const out = {};
      for (let i=0; i<localStorage.length; i++) {
        const k = localStorage.key(i);
        out[k] = localStorage.getItem(k);
      }
      return out;
    }""")
    print("localStorage keys:", list(storage.keys()))

    # Verify
    sess = page.evaluate("async () => (await fetch('/api/auth/session')).text()")
    print("/api/auth/session =>", sess[:300])

    (OUT / "auth_state.json").write_text(
        json.dumps({"cookies": cookies, "localStorage": storage, "final_url": page.url},
                   indent=2, ensure_ascii=False), encoding="utf-8")
    print("Saved", OUT / "auth_state.json")