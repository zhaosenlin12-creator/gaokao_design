"""Login via NextAuth Credentials with proper Referer + Origin headers."""
import json
from pathlib import Path
from scrapling.fetchers import FetcherSession

OUT = Path(r"D:\kaifa\gaokao\crawled")
USERNAME = "1255330251@qq.com"
PASSWORD = "zsl13177068887"
BASE = "https://agentsfeed.org"
LOGIN_PAGE = f"{BASE}/auth/signin"

extra = {
    "Referer": LOGIN_PAGE,
    "Origin": BASE,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

with FetcherSession(impersonate="chrome", headers=extra, follow_redirects=False) as sess:
    csrf = (sess.get(f"{BASE}/api/auth/csrf").json() or {}).get("csrfToken")
    print("csrfToken:", (csrf or "")[:24] + "...")

    body = {
        "csrfToken": csrf,
        "email": USERNAME,
        "password": PASSWORD,
        "callbackUrl": f"{BASE}/app-demo/gaokao-map",
        "json": "true",
    }
    r = sess.post(f"{BASE}/api/auth/callback/credentials", data=body)
    print("SIGNIN status:", r.status, "url:", r.url)
    print("Location header:", r.headers.get("location", "<none>"))
    print("Set-Cookie header (raw):", str({k:v for k,v in (r.headers or {}).items() if 'cookie' in k.lower()})[:300])
    print("Body:", (r.text or "")[:300])

    r2 = sess.get(f"{BASE}/api/auth/session")
    print("\n/api/auth/session status:", r2.status)
    print("body:", r2.text[:400])