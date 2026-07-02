"""Inject cookies via raw Cookie header, set after first navigation."""
from pathlib import Path
from scrapling.fetchers import StealthySession

OUT = Path(r"D:\kaifa\gaokao\crawled")
URL = "https://agentsfeed.org/app-demo/gaokao/index.html"

cookie_header = "; ".join([
    "__Host-next-auth.csrf-token=a836a6ca81f96ccaa8a6197b764774fb148285cca8798b37947837127e8beaca%7Cc890eb54d1a6dd93e1a6ee02147326aaf0cc5194854cb947e2cc021ec4f1859a",
    "__Secure-next-auth.callback-url=https%3A%2F%2Fagentsfeed.org%2Fauth%2Fsignin",
    "__Secure-next-auth.session-token=eyJhbGciOiJkaXIiLCJlbmMiOiJBMjU2R0NNIn0..mCNnCY-mC36E5ikc.KeaQvAWMZ1eJ7vdhr2uCBYzgZKzqgaxN_vmU6iFGpqbT83Svlc_sDRfAQsy2M19D9d1Lj3b8fJ7QJR5puuL6wlWdtckuX-t08GrcxqHj5HH_G4qlEG2IAuW4zLiQgcFhRuOn0L8YFWiLiM_6jbYUBVLrpiKQSkWoAIv7Y5FwQq6VKMLjswYdhK5w8PBSo34N-gmARoXaQ4_HpG0NT0VviR1Thu8x3-Uw02H0NuHVuZg2URvQLRD7BgHJsv6xI5vROR7l3TN8iC6VWEUkRNQbpFnZMeGS.kqoP6zCvR6qTz5L57EK8BQ",
    "agentfeed_anon=d47fd0e7-5e01-49f9-86b0-e3b04efbafcb",
    "agentfeed-lang=zh",
])

with StealthySession(headless=True) as s:
    page = s.context.new_page()
    page.set_extra_http_headers({"Cookie": cookie_header})
    page.set_viewport_size({"width": 1440, "height": 900})

    page.goto(URL, wait_until="networkidle")
    page.wait_for_timeout(6000)

    print("title:", page.title())
    print("url:", page.url)
    sess = page.evaluate("async() => (await fetch('/api/auth/session')).text()")
    print("session in browser:", sess[:300])

    vp   = OUT / "screenshot-authed-viewport.png"
    full = OUT / "screenshot-authed-full.png"
    page.screenshot(path=str(vp), full_page=False)
    page.screenshot(path=str(full), full_page=True)
    print("Saved:", vp.stat().st_size, full.stat().st_size, "bytes")