"""Same proxy as proxy.py, but the upstream hop uses Scrapling'\''s Fetcher
so we send real Chrome TLS/headers and the origin doesn'\''t 403 us."""
import http.server
import socketserver
import sys
import mimetypes
from pathlib import Path
from scrapling.fetchers import Fetcher

ROOT = Path(__file__).resolve().parent / "gaokao-iframe"
UPSTREAM = "https://agentsfeed.org"
COOKIE_HDR = (
    "__Host-next-auth.csrf-token=a836a6ca81f96ccaa8a6197b764774fb148285cca8798b37947837127e8beaca%7Cc890eb54d1a6dd93e1a6ee02147326aaf0cc5194854cb947e2cc021ec4f1859a; "
    "__Secure-next-auth.callback-url=https%3A%2F%2Fagentsfeed.org%2Fauth%2Fsignin; "
    "__Secure-next-auth.session-token=eyJhbGciOiJkaXIiLCJlbmMiOiJBMjU2R0NNIn0..mCNnCY-mC36E5ikc.KeaQvAWMZ1eJ7vdhr2uCBYzgZKzqgaxN_vmU6iFGpqbT83Svlc_sDRfAQsy2M19D9d1Lj3b8fJ7QJR5puuL6wlWdtckuX-t08GrcxqHj5HH_G4qlEG2IAuW4zLiQgcFhRuOn0L8YFWiLiM_6jbYUBVLrpiKQSkWoAIv7Y5FwQq6VKMLjswYdhK5w8PBSo34N-gmARoXaQ4_HpG0NT0VviR1Thu8x3-Uw02H0NuHVuZg2URvQLRD7BgHJsv6xI5vROR7l3TN8iC6VWEUkRNQbpFnZMeGS.kqoP6zCvR6qTz5L57EK8BQ; "
    "agentfeed_anon=d47fd0e7-5e01-49f9-86b0-e3b04efbafcb; "
    "agentfeed-lang=zh"
)
PROXY_PREFIXES = ("/api/", "/app-demo/")

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("[proxy] " + fmt % args + "\n")

    def do_GET(self):  self._route("GET")
    def do_POST(self): self._route("POST")
    def do_OPTIONS(self): self._cors()

    def _cors(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def _route(self, method):
        if self.path.startswith(PROXY_PREFIXES):
            return self._proxy(method)
        return self._serve_static()

    def _serve_static(self):
        rel = self.path.lstrip("/").split("?")[0]
        path = (ROOT / rel).resolve()
        if ROOT.resolve() not in path.parents and path != ROOT:
            return self._error(403, "forbidden")
        if not path.is_file():
            return self._error(404, rel)
        ctype, _ = mimetypes.guess_type(str(path))
        if ctype is None: ctype = "application/octet-stream"
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _proxy(self, method):
        url = UPSTREAM + self.path
        # Read body for POST
        length = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(length) if length else None
        extra = {"Cookie": COOKIE_HDR}
        for h in ("User-Agent", "Accept", "Accept-Language", "Referer", "Origin", "Content-Type"):
            v = self.headers.get(h)
            if v: extra[h] = v
        try:
            r = Fetcher.get(url, impersonate="chrome", headers=extra, timeout=30) if method == "GET" \
                else Fetcher.post(url, impersonate="chrome", headers=extra, data=body, timeout=30)
        except Exception as e:
            return self._error(502, f"upstream: {e!r}")
        data = r.body or b""
        # Pick a content type from response headers if present
        ctype = r.headers.get("Content-Type") or r.headers.get("content-type") or "application/octet-stream"
        self.send_response(r.status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def _error(self, code, msg):
        body = f"{code} {msg}".encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("127.0.0.1", port), Handler) as httpd:
        print(f"[proxy] serving {ROOT}", flush=True)
        print(f"[proxy] proxying {PROXY_PREFIXES} -> {UPSTREAM} (via Scrapling chrome impersonate)", flush=True)
        print(f"[proxy] listen on http://127.0.0.1:{port}", flush=True)
        httpd.serve_forever()