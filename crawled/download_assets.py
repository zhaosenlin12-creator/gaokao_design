"""Download all static assets referenced by the gaokao iframe page using Scrapling."""
import re
from pathlib import Path
from scrapling.fetchers import Fetcher

ROOT = Path(r"D:\kaifa\gaokao\crawled\gaokao-iframe")
HTML_FILE = ROOT / "iframe-anon.html"
html = HTML_FILE.read_text(encoding="utf-8")
BASE = "https://agentsfeed.org/app-demo/gaokao/"

urls = set()
for m in re.finditer(r'<script[^>]*\bsrc="([^"]+)"', html):
    urls.add(m.group(1))
for m in re.finditer(r'<link[^>]*\bhref="([^"]+)"', html):
    urls.add(m.group(1))
for m in re.finditer(r'<img[^>]*\bsrc="([^"]+)"', html):
    urls.add(m.group(1))
for m in re.finditer(r'url\(([^)]+)\)', html):
    u = m.group(1).strip().strip('"').strip("'")
    if u and not u.startswith("data:"):
        urls.add(u)
urls = {u for u in urls if "${" not in u}
EXTERNAL = ("https://a.basemaps.cartocdn.com",
            "https://b.basemaps.cartocdn.com",
            "https://c.basemaps.cartocdn.com",
            "https://static.cloudflareinsights.com")
urls = {u for u in urls if not any(u.startswith(e) for e in EXTERNAL)}

def to_abs(u: str) -> str:
    if u.startswith("http://") or u.startswith("https://"):
        return u
    if u.startswith("/"):
        return "https://agentsfeed.org" + u
    return BASE + u.lstrip("./")

ok = fail = 0
for rel in sorted(urls):
    absu = to_abs(rel)
    target = ROOT / rel.split("?")[0]
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        r = Fetcher.get(absu, timeout=20000)
        if r.status == 200 and r.body:
            target.write_bytes(r.body)
            ok += 1
            print(f"OK  {rel}  ({len(r.body)} bytes)")
        else:
            fail += 1
            print(f"FAIL {rel}  status={r.status}")
    except Exception as e:
        fail += 1
        print(f"ERR {rel}  {e!r}")
print(f"\nDONE ok={ok} fail={fail}")
