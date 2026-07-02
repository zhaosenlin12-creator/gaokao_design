#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# serve.py: minimal static HTTP server on 8765 for gaokao-iframe/
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, unquote

ROOT = Path(r"D:\\kaifa\\gaokao\\crawled\\gaokao-iframe")
PORT = 8765
HOST = "0.0.0.0"

MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".mp3": "audio/mpeg",
    ".ico": "image/x-icon",
    ".txt": "text/plain; charset=utf-8",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
}

class H(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write(("%s - - [%s] " + fmt + chr(10)) % (self.address_string(), self.log_date_time_string(), *args))

    def do_GET(self):
        u = urlparse(self.path)
        rel = unquote(u.path).lstrip("/")
        if not rel: rel = "iframe-anon.html"
        target = (ROOT / rel).resolve()
        try:
            target.relative_to(ROOT.resolve())
        except ValueError:
            self.send_error(403, "forbidden"); return
        if not target.exists():
            self.send_error(404, "not found"); return
        if target.is_dir():
            target = target / "index.html"
            if not target.exists(): self.send_error(404); return
        ext = target.suffix.lower()
        ct = MIME.get(ext, "application/octet-stream")
        try:
            data = target.read_bytes()
        except Exception as e:
            self.send_error(500, str(e)); return
        self.send_response(200)
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

def main():
    if not ROOT.exists():
        print("[serve] ERROR: ROOT does not exist: " + str(ROOT))
        sys.exit(1)
    bind = "127.0.0.1" if HOST=="0.0.0.0" else HOST
    print("[serve] listening on http://" + bind + ":" + str(PORT))
    print("[serve] serving " + str(ROOT))
    print("[serve] iframe-anon: http://" + bind + ":" + str(PORT) + "/iframe-anon.html")
    s = ThreadingHTTPServer((HOST, PORT), H)
    try: s.serve_forever()
    except KeyboardInterrupt: s.shutdown()

if __name__ == "__main__": main()