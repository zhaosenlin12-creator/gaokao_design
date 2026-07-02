"""Diagnose: capture all console messages and page errors, and inspect
the API/baseURL globals in the page."""
from pathlib import Path
from scrapling.fetchers import StealthySession

OUT = Path(r"D:\kaifa\gaokao\crawled")
URL = "http://127.0.0.1:8765/iframe-anon.html"
COOKIE_HDR = (
    "__Host-next-auth.csrf-token=a836a6ca81f96ccaa8a6197b764774fb148285cca8798b37947837127e8beaca%7Cc890eb54d1a6dd93e1a6ee02147326aaf0cc5194854cb947e2cc021ec4f1859a; "
    "__Secure-next-auth.callback-url=https%3A%2F%2Fagentsfeed.org%2Fauth%2Fsignin; "
    "__Secure-next-auth.session-token=eyJhbGciOiJkaXIiLCJlbmMiOiJBMjU2R0NNIn0..mCNnCY-mC36E5ikc.KeaQvAWMZ1eJ7vdhr2uCBYzgZKzqgaxN_vmU6iFGpqbT83Svlc_sDRfAQsy2M19D9d1Lj3b8fJ7QJR5puuL6wlWdtckuX-t08GrcxqHj5HH_G4qlEG2IAuW4zLiQgcFhRuOn0L8YFWiLiM_6jbYUBVLrpiKQSkWoAIv7Y5FwQq6VKMLjswYdhK5w8PBSo34N-gmARoXaQ4_HpG0NT0VviR1Thu8x3-Uw02H0NuHVuZg2URvQLRD7BgHJsv6xI5vROR7l3TN8iC6VWEUkRNQbpFnZMeGS.kqoP6zCvR6qTz5L57EK8BQ; "
    "agentfeed_anon=d47fd0e7-5e01-49f9-86b0-e3b04efbafcb; "
    "agentfeed-lang=zh"
)

with StealthySession(headless=True) as s:
    page = s.context.new_page()
    page.set_extra_http_headers({"Cookie": COOKIE_HDR})
    page.set_viewport_size({"width": 1440, "height": 900})

    msgs = []
    page.on("console",   lambda m: msgs.append(("CON", m.type, m.text[:300])))
    page.on("pageerror", lambda e: msgs.append(("ERR", "pageerror", str(e)[:300])))
    page.on("requestfailed", lambda r: msgs.append(("FAIL", r.method, r.url[:200], r.failure)))

    page.goto(URL, wait_until="networkidle")
    page.wait_for_timeout(8000)

    state = page.evaluate("""() => ({
      // Globals we expect
      hasAPI: typeof API !== 'undefined',
      API: typeof API !== 'undefined' ? API : null,
      hasUnis: typeof unisP !== 'undefined',
      hasRECS: typeof RECS !== 'undefined',
      // Map state
      mapHas: !!document.getElementById('map') && !!document.getElementById('map')._maplibre,
      // Errors visible
      visibleErrs: Array.from(document.querySelectorAll('div, span, p'))
        .map(e => (e.innerText||'').trim())
        .filter(t => t.length > 2 && t.length < 100 && /无法|失败|错误|无法连接/.test(t))
        .slice(0, 10),
    })""")
    print("STATE:", state)

    print(f"\n=== {len(msgs)} console/error/failed events ===")
    for m in msgs[:40]:
        print(" ", m)