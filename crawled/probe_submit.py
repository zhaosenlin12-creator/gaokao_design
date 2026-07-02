"""Watch what request the login form actually fires when submitted.
We instrument the page to log all requests, fill in the form, and click submit.
"""
from scrapling.fetchers import StealthySession

USERNAME = "1255330251@qq.com"
PASSWORD = "zsl13177068887"
URL = "https://agentsfeed.org/auth/signin"

with StealthySession(headless=True) as s:
    page = s.context.new_page()
    captured = []
    page.on("request", lambda req: captured.append((req.method, req.url, req.headers.get("content-type",""), req.post_data[:400] if req.post_data else "")))
    page.on("response", lambda res: captured.append(("RESP", res.request.method, res.url, res.status)))

    page.goto(URL, wait_until="networkidle")
    page.wait_for_timeout(2000)

    # Fill in the only text + password inputs
    page.fill('input[type=text]', USERNAME)
    page.fill('input[type=password]', PASSWORD)
    page.click('button[type=submit]')

    # Wait for either navigation or any response from a /api or /auth path
    try:
        page.wait_for_url(lambda u: "/app-demo" in u or "/feed" in u or "/auth" not in u, timeout=15000)
    except Exception:
        page.wait_for_timeout(3000)

    print("FINAL_URL:", page.url)
    print("COOKIES:", [c["name"] + "=" + c["value"][:24] for c in s.context.cookies()])
    print("\n--- CAPTURED (first 25) ---")
    for entry in captured[:25]:
        print(entry)