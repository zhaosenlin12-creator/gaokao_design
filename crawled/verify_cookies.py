"""Validate the cookies the user pasted, then re-fetch the gaokao map page
in the logged-in state. Compare against the anonymous version."""
import json
from pathlib import Path
from scrapling.fetchers import Fetcher, FetcherSession

OUT = Path(r"D:\kaifa\gaokao\crawled")
BASE = "https://agentsfeed.org"

# 5 cookies, in the order the user pasted them
cookies = {
    "__Host-next-auth.csrf-token":          "a836a6ca81f96ccaa8a6197b764774fb148285cca8798b37947837127e8beaca%7Cc890eb54d1a6dd93e1a6ee02147326aaf0cc5194854cb947e2cc021ec4f1859a",
    "__Secure-next-auth.callback-url":      "https%3A%2F%2Fagentsfeed.org%2Fauth%2Fsignin",
    "__Secure-next-auth.session-token":     "eyJhbGciOiJkaXIiLCJlbmMiOiJBMjU2R0NNIn0..mCNnCY-mC36E5ikc.KeaQvAWMZ1eJ7vdhr2uCBYzgZKzqgaxN_vmU6iFGpqbT83Svlc_sDRfAQsy2M19D9d1Lj3b8fJ7QJR5puuL6wlWdtckuX-t08GrcxqHj5HH_G4qlEG2IAuW4zLiQgcFhRuOn0L8YFWiLiM_6jbYUBVLrpiKQSkWoAIv7Y5FwQq6VKMLjswYdhK5w8PBSo34N-gmARoXaQ4_HpG0NT0VviR1Thu8x3-Uw02H0NuHVuZg2URvQLRD7BgHJsv6xI5vROR7l3TN8iC6VWEUkRNQbpFnZMeGS.kqoP6zCvR6qTz5L57EK8BQ",
    "agentfeed_anon":                       "d47fd0e7-5e01-49f9-86b0-e3b04efbafcb",
    "agentfeed-lang":                       "zh",
}

# 1) Probe /api/auth/session first - it returns the user object if auth works
headers = {
    "Cookie": "; ".join(f"{k}={v}" for k, v in cookies.items()),
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
    "Accept": "application/json,text/html,*/*",
}
r = Fetcher.get(f"{BASE}/api/auth/session", headers=headers)
print("== /api/auth/session ==")
print("status:", r.status)
print("body:", (r.text or r.body.decode("utf-8","ignore"))[:400])

# 2) Fetch the iframe page with the cookies
r2 = Fetcher.get(f"{BASE}/app-demo/gaokao/index.html", headers=headers)
print("\n== /app-demo/gaokao/index.html ==")
print("status:", r2.status, "len:", len(r2.body))
(OUT / "authed-gaokao-raw.html").write_bytes(r2.body)
print("saved", OUT / "authed-gaokao-raw.html")

# 3) Quick diff signal: look for "登录" or user name in the page
text = r2.text or r2.body.decode("utf-8","ignore")
print("\nsize:", len(text), "chars")
print("contains 登录:", "登录" in text)
print("contains nickname-like:", any(k in text for k in ["zsl", "1255330251", "demo"]))
print("first 400 chars:")
print(text[:400])