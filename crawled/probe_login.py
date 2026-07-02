"""Probe login form via StealthySession, then drive the browser ourselves."""
from pathlib import Path
from scrapling.fetchers import StealthySession

OUT = Path(r"D:\kaifa\gaokao\crawled")
URL = "https://agentsfeed.org/auth/signin"

with StealthySession(headless=True) as s:
    page = s.context.new_page()
    page.goto(URL, wait_until="networkidle")
    page.wait_for_timeout(2500)

    info = page.evaluate("""() => ({
      url: location.href,
      title: document.title,
      forms: Array.from(document.forms).map(f => ({
        action: f.action, method: f.method,
        inputs: Array.from(f.elements).map(e => ({name: e.name, type: e.type, id: e.id, placeholder: e.placeholder})),
        dataAttrs: Object.fromEntries(Array.from(f.attributes).filter(a => a.name.startsWith('data-')).map(a => [a.name, a.value])),
      })),
      submitButtons: Array.from(document.querySelectorAll('button[type=submit]')).map(b => ({
        text: b.innerText.trim().slice(0,40), formAction: b.formAction, formMethod: b.formMethod,
      })),
      cookies: document.cookie,
    })""")
    print("INFO:", info)