from pathlib import Path
p = Path(r"D:\kaifa\gaokao\crawled\gaokao-iframe\iframe-anon.html")
h = p.read_text(encoding="utf-8")
old = 'http://${location.hostname||"127.0.0.1"}:8787'
new = "https://agentsfeed.org"
print("found 8787 snippet:", old in h)
h2 = h.replace(old, new)
h2 = h2.replace('fetch("unis.json?v=1")', 'fetch("https://agentsfeed.org/app-demo/gaokao/unis.json?v=1")')
p.write_text(h2, encoding="utf-8")
print("contains agentsfeed.org:", "agentsfeed.org" in h2)
print("still contains 8787:", "8787" in h2)