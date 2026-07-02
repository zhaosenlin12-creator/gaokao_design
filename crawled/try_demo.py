"""Try the demo credentials hinted on the page; if those work, the flow itself is correct.
Then return and tell the user: their account is not the one for this site."""
import json
from pathlib import Path
from scrapling.fetchers import StealthySession

OUT = Path(r"D:\kaifa\gaokao\crawled")
USERNAME = "alice@agentsfeed.org"
PASSWORD = "demo1234"
LOGIN_PAGE = "https://agentsfeed.org/auth/signin"

with StealthySession(headless=True) as s:
    page = s.context.new_page()
    page.goto(LOGIN_PAGE, wait_until="networkidle")
    page.wait_for_timeout(2500)

    page.fill('input[type=text]', USERNAME)
    page.fill('input[type=password]', PASSWORD)
    page.click('button[type=submit]')
    page.wait_for_timeout(5000)

    print("URL after submit:", page.url)
    print("Body visible text (truncated):")
    print(page.evaluate("() => document.body.innerText")[:600])
    print()
    print("/api/auth/session =>", page.evaluate("async() => (await fetch('/api/auth/session')).text()")[:300])
    print()
    print("Cookies:")
    for c in s.context.cookies():
        print(" -", c["name"], "=", c["value"][:24] + ("..." if len(c["value"])>24 else ""))