import os, sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright

PIPE = chr(124)
BASE = "https://agentsfeed.org/app-demo/gaokao"
OUT = Path(r"D:\\kaifa\\gaokao\\crawled\\gaokao-iframe")

COOKIES = [
    dict(name="__Host-next-auth.csrf-token",
         value="a836a6ca81f96ccaa8a6197b764774fb148285cca8798b37947837127e8beaca" + PIPE + "c890eb54d1a6dd93e1a6ee02147326aaf0cc5194854cb947e2cc021ec4f1859a",
         domain="agentsfeed.org", path="/", secure=True, httpOnly=True, sameSite="Lax"),
    dict(name="__Secure-next-auth.callback-url",
         value="https://agentsfeed.org/",
         domain="agentsfeed.org", path="/", secure=True, httpOnly=False, sameSite="Lax"),
    dict(name="__Secure-next-auth.session-token",
         value="eyJhbGciOiJkaXIiLCJlbmMiOiJBMjU2R0NNIn0..mCNnCY-mC36E5ikc.KeaQvAWMZ1eJ7vdhr2uCBYzgZKzqgaxN_vmU6iFGpqbT83Svlc_sDRfAQsy2M19D9d1Lj3b8fJ7QJR5puuL6wlWdtckuX-t08GrcxqHj5HH_G4qlEG2IAuW4zLiQgcFhRuOn0L8YFWiLiM_6jbYUBVLrpiKQSkWoAIv7Y5FwQq6VKMLjswYdhK5w8PBSo34N-gmARoXaQ4_HpG0NT0VviR1Thu8x3-Uw02H0NuHVuZg2URvQLRD7BgHJsv6xI5vROR7l3TN8iC6VWEUkRNQbpFnZMeGS.kqoP6zCvR6qTz5L57EK8BQ",
         domain="agentsfeed.org", path="/", secure=True, httpOnly=True, sameSite="Lax"),
    dict(name="agentfeed_anon", value="d47fd0e7-5e01-49f9-86b0-e3b04efbafcb",
         domain="agentsfeed.org", path="/", secure=False, httpOnly=False, sameSite="Lax"),
    dict(name="agentfeed-lang", value="zh",
         domain="agentsfeed.org", path="/", secure=False, httpOnly=False, sameSite="Lax"),
]

TARGETS = [
    "unis.json",
    "terrain-symbols.json",
    "geo/china-outline.json",
    "geo/100000_full.json",
    "geo/districts.json",
    "geo/ne_50m_rivers_cn.json",
    "geo/ne_50m_lakes_cn.json",
    "api/meta",
]

def find_chrome():
    base = Path(r"C:\\Users\\Administrator\\AppData\\Local\\ms-playwright")
    if not base.exists(): return None
    cands = sorted(base.glob("chromium-*/chrome-win*/chrome.exe"), reverse=True)
    return str(cands[0]) if cands else None

def run():
    (OUT / "geo").mkdir(parents=True, exist_ok=True)
    (OUT / "api").mkdir(parents=True, exist_ok=True)
    chrome = find_chrome()
    print("[info] using chrome:", chrome)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=chrome, args=["--disable-blink-features=AutomationControlled"])
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36", locale="zh-CN")
        try:
            context.add_cookies(COOKIES)
            print("[ok] add_cookies succeeded")
        except Exception as e:
            print("[warn] add_cookies:", e)
        page = context.new_page()
        try:
            page.goto(BASE + "/iframe-anon.html", wait_until="domcontentloaded", timeout=60000)
            print("[ok] warmup done")
        except Exception as e:
            print("[warn] warmup:", e)
        for rel in TARGETS:
            target = OUT / rel
            if target.exists() and target.stat().st_size > 100:
                print("[skip]", rel, target.stat().st_size)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            url = BASE + "/" + rel
            try:
                resp = context.request.get(url, headers={"Accept": "application/json,*/*"}, timeout=60000)
                body = resp.body()
                ct = resp.headers.get("content-type", "")
                if resp.status == 200 and len(body) > 0:
                    target.write_bytes(body)
                    print("[ok]", rel, resp.status, len(body), ct[:50])
                else:
                    print("[fail]", rel, resp.status, len(body), ct[:50])
            except Exception as e:
                print("[err]", rel, repr(e)[:80])

if __name__ == "__main__":
    run()