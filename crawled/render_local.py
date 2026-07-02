"""Render the locally-served iframe page in a real Chromium and screenshot it.
This validates the crawl end-to-end: HTML + assets served from disk actually boot
the gaokao map app in a browser.
"""
from pathlib import Path
from scrapling.fetchers import StealthySession

OUT = Path(r"D:\kaifa\gaokao\crawled")
URL = "http://127.0.0.1:8765/iframe-anon.html"

with StealthySession(headless=True) as s:
    page = s.context.new_page()
    page.set_viewport_size({"width": 1440, "height": 900})

    page.goto(URL, wait_until="networkidle")
    # Let MapLibre + the gk-engine fully boot
    page.wait_for_timeout(6000)

    # Pull a few health signals from the DOM
    h1 = page.locator("h1").first.inner_text() if page.locator("h1").count() else "<no h1>"
    canvas_count = page.locator("canvas").count()
    button_count = page.locator("button").count()
    title = page.title()

    print("title:", title)
    print("h1:", h1)
    print("canvases:", canvas_count, "buttons:", button_count)

    # Screenshot full page
    full = OUT / "screenshot-full.png"
    page.screenshot(path=str(full), full_page=True)
    print("Saved", full, full.stat().st_size, "bytes")

    # Screenshot just the viewport
    vp = OUT / "screenshot-viewport.png"
    page.screenshot(path=str(vp), full_page=False)
    print("Saved", vp, vp.stat().st_size, "bytes")