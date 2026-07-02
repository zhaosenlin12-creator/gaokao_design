"""With cookies loaded on agentsfeed.org, intercept every fetch/XHR the page fires,
print URL + status + content-type + size. This reveals the real API surface."""
from pathlib import Path
from scrapling.fetchers import StealthySession

URL = "https://agentsfeed.org/app-demo/gaokao/index.html"
COOKIE_HDR = (
    "__Host-next-auth.csrf-token=a836a6ca81f96ccaa8a6197b764774fb148285cca8798b37947837127e8beaca%7Cc890eb54d1a6dd93e1a6ee02147326aaf0cc5194854cb947e2cc021ec4f1859a; "
    "__Secure-next-auth.callback-url=https%3A%2F%2Fagentsfeed.org%2Fauth%2Fsignin; "
    "__Secure-next-auth.session-token=eyJhbGciOiJkaXIiLCJlbmMiOiJBMjU2R0NNIn0..mCNnCY-mC36E5ikc.KeaQvAWMZ1eJ7vdhr2uCBYzgZKzqgaxN_vmU6iFGpqbT83Svlc_sDRfAQsy2M19D9d1Lj3b8fJ7QJR5puuL6wlWdtckuX-t08GrcxqHj5HH_G4qlEG2IAuW4zLiQgcFhRuOn0L8YFWiLiM_6jbYUBVLrpiKQSkWoAIv7Y5FwQq6VKMLjswYdhK5w8PBSo34N-gmARoXaQ4_HpG0NT0VviR1Thu8x3-Uw02H0NuHVuZg2URvQLRD7BgHJsv6xI5vROR7l3TN8iC6VWEUkRNQbpFnZMeGS.kqoP6zCvR6qTz5L57EK8BQ; "
    "agentfeed_anon=d47fd0e7-5e01-49f9-86b0-e3b04efbafcb; "
    "agentfeed-lang=zh"
)

with StealthySession(headless=True) as s:
    page = s.context.new_page()
    page.set_extra_http_headers({"Cookie": COOKIE_HDR})

    api_calls = []
    def on_request(req):
        if req.resource_type in ("fetch", "xhr", "other") and "agentsfeed.org" in req.url and "/_next/static" not in req.url:
            api_calls.append(("REQ", req.method, req.url, (req.post_data or "")[:200]))
    def on_response(res):
        if "agentsfeed.org" in res.url and "/_next/static" not in res.url and "/_next/data" not in res.url and "/cdn-cgi" not in res.url:
            try:
                body = res.body()[:300]
            except Exception:
                body = "<no body>"
            api_calls.append(("RESP", res.request.method, res.url, res.status, body))
    page.on("request", on_request)
    page.on("response", on_response)

    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto(URL, wait_until="networkidle")
    page.wait_for_timeout(5000)
    # Also try clicking the "我的推荐大学" button to trigger the recommend API
    try:
        page.click("text=我的推荐大学", timeout=2000)
        page.wait_for_timeout(4000)
    except Exception as e:
        api_calls.append(("NOTE", "could not click", repr(e)[:200]))

    print(f"=== {len(api_calls)} events ===")
    for e in api_calls:
        print(e)