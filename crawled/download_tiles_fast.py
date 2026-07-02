"""Fast parallel download of terrarium tiles using Fetcher (curl_cffi) with
TLS impersonation. Much faster than StealthyFetcher for static assets."""
import concurrent.futures
from pathlib import Path
from scrapling.fetchers import Fetcher

OUT = Path(r"D:\kaifa\gaokao\crawled\gaokao-iframe\tiles\terrarium")
OUT.mkdir(parents=True, exist_ok=True)
BASE = "https://agentsfeed.org/app-demo/gaokao/tiles/terrarium"

ZOOM_RANGES = {
    4: (12, 14, 5, 7),
    5: (25, 28, 10, 15),
    6: (50, 57, 21, 30),
    7: (100, 114, 43, 61),
}

tasks = []
for z, (xmin, xmax, ymin, ymax) in ZOOM_RANGES.items():
    for x in range(xmin, xmax + 1):
        for y in range(ymin, ymax + 1):
            tasks.append((z, x, y))

def grab(t):
    z, x, y = t
    target = OUT / str(z) / str(x) / f"{y}.webp"
    if target.exists() and target.stat().st_size > 0:
        return ("skip", t)
    target.parent.mkdir(parents=True, exist_ok=True)
    url = f"{BASE}/{z}/{x}/{y}.webp"
    try:
        r = Fetcher.get(url, impersonate="chrome", timeout=20000)
        if r.status == 200 and r.body:
            target.write_bytes(r.body)
            return ("ok", t, len(r.body))
        return ("fail", t, r.status)
    except Exception as e:
        return ("err", t, repr(e)[:60])

ok = fail = err = skip = 0
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
    for i, res in enumerate(pool.map(grab, tasks, chunksize=4), 1):
        kind = res[0]
        if kind == "ok":
            ok += 1
        elif kind == "skip":
            skip += 1
        elif kind == "fail":
            fail += 1
        else:
            err += 1
        if i % 30 == 0 or i == len(tasks):
            print(f"[tiles] {i}/{len(tasks)} ok={ok} skip={skip} fail={fail} err={err}", flush=True)

print(f"[tiles] DONE total={len(tasks)} ok={ok} skip={skip} fail={fail} err={err}")