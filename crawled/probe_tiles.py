from scrapling.fetchers import StealthyFetcher
for z, x, y in [(0,0,0), (4,13,6), (5,27,12), (6,53,24)]:
    url = f"https://agentsfeed.org/app-demo/gaokao/tiles/terrarium/{z}/{x}/{y}.webp"
    r = StealthyFetcher.fetch(url, headless=True, network_idle=False, timeout=20000)
    ct = r.headers.get("content-type", "?")
    if r.status == 200:
        print(f"OK  z={z} x={x} y={y}  {len(r.body)} bytes  ct={ct}")
    else:
        print(f"FAIL {r.status} z={z} x={x} y={y}")