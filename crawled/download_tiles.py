"""Download all terrarium DEM tiles for China region (zoom 4-7).
Uses Scrapling StealthyFetcher to bypass Cloudflare, and a single shared
browser session via StealthySession for speed (reuse one chromium for all
requests).
China approx bounds (web mercator):
  z=4: x in [12,14], y in [5,7]   (12-15 * 4-7 = small)
  z=5: x in [25,28], y in [10,15]
  z=6: x in [50,57], y in [21,30]
  z=7: x in [100,114], y in [43,61]
"""
import sys
from pathlib import Path
from scrapling.fetchers import StealthySession

OUT = Path(r"D:\kaifa\gaokao\crawled\gaokao-iframe\tiles\terrarium")
OUT.mkdir(parents=True, exist_ok=True)
BASE = "https://agentsfeed.org/app-demo/gaokao/tiles/terrarium"

# Bounds (inclusive) - determined empirically
ZOOM_RANGES = {
    4: (12, 14, 5, 7),
    5: (25, 28, 10, 15),
    6: (50, 57, 21, 30),
    7: (100, 114, 43, 61),
}

# Quick probe: write a "ready" file with maxzoom
ready_file = OUT.parent / "ready"
ready_file.write_text("7", encoding="utf-8")
print(f"[tiles] ready -> {ready_file} (7)")

# Build full task list
tasks = []
for z, (xmin, xmax, ymin, ymax) in ZOOM_RANGES.items():
    for x in range(xmin, xmax + 1):
        for y in range(ymin, ymax + 1):
            tasks.append((z, x, y))
print(f"[tiles] planned: {len(tasks)} tiles")

# Reuse one StealthySession
ok = fail = skip = 0
with StealthySession(headless=True) as s:
    for z, x, y in tasks:
        rel = OUT / str(z) / str(x)
        target = rel / f"{y}.webp"
        if target.exists() and target.stat().st_size > 0:
            skip += 1
            continue
        rel.mkdir(parents=True, exist_ok=True)
        url = f"{BASE}/{z}/{x}/{y}.webp"
        try:
            r = s.fetch(url, network_idle=False, timeout=30000)
            if r.status == 200 and r.body:
                target.write_bytes(r.body)
                ok += 1
                if ok % 20 == 0:
                    print(f"[tiles] ok={ok} fail={fail} skip={skip}  last=z{z}/x{x}/y{y}", flush=True)
            else:
                fail += 1
        except Exception as e:
            fail += 1
            print(f"[tiles] ERR z{z} x{x} y{y}: {e!r}", flush=True)

print(f"[tiles] DONE ok={ok} fail={fail} skip={skip} total={len(tasks)}")