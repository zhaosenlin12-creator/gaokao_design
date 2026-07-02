"""Diagnose: capture what happens AFTER clicking submit, including any toast/error,
the form's network activity, and a fresh page.evaluate of nextauth.message.
"""
from scrapling.fetchers import StealthySession

USERNAME = "1255330251@qq.com"
PASSWORD = "zsl13177068887"
LOGIN_PAGE = "https://agentsfeed.org/auth/signin"

with StealthySession(headless=True) as s:
    page = s.context.new_page()
    reqs = []
    page.on("request", lambda r: reqs.append(("REQ", r.method, r.url, (r.post_data or "")[:200])))
    page.on("response", lambda r: reqs.append(("RESP", r.request.method, r.url, r.status)))
    page.on("console", lambda msg: reqs.append(("CON", msg.type, msg.text[:200])))

    page.goto(LOGIN_PAGE, wait_until="networkidle")
    page.wait_for_timeout(2500)

    page.fill('input[type=text]', USERNAME)
    page.fill('input[type=password]', PASSWORD)

    # Get the current message just before submit
    pre = page.evaluate("() => localStorage.getItem('nextauth.message')")
    print("BEFORE submit, nextauth.message =", pre)

    page.click('button[type=submit]')
    page.wait_for_timeout(4000)

    print("\nURL after click:", page.url)
    print("Title:", page.title())
    print("Visible text on page (truncated):")
    body_text = page.evaluate("() => document.body.innerText")
    print(body_text[:800])

    print("\nlocalStorage.nextauth.message =", page.evaluate("() => localStorage.getItem('nextauth.message')"))
    print("All localStorage:", page.evaluate("() => Object.fromEntries(Object.keys(localStorage).map(k=>[k,localStorage.getItem(k)]))"))

    print("\n--- LAST 30 EVENTS ---")
    for e in reqs[-30:]:
        print(e)