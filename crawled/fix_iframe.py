"""Repair iframe-anon.html: re-encode the broken UTF-8 -> proper UTF-8, and replace
URL-encoded logo references with the actual disk filenames."""
from pathlib import Path
import urllib.parse

ROOT = Path(r"D:\kaifa\gaokao\crawled\gaokao-iframe")
html_path = ROOT / "iframe-anon.html"
raw = html_path.read_bytes()

# 1) Try strict utf-8 first; if mojibake, re-decode
try:
    text = raw.decode("utf-8")
except UnicodeDecodeError:
    # PowerShell wrote as GBK 0x80-0xFF mapping to Unicode 0x20AC-0xFFFD?  Re-decode as cp1252
    text = raw.decode("cp1252", errors="replace")

# 2) Replace each URL-encoded logo reference with its disk filename
logo_dir = ROOT / "assets" / "logos"
fixed = 0
for f in logo_dir.iterdir():
    enc = urllib.parse.quote(f.stem) + f.suffix  # e.g. %E5%8C%97%E4%BA%AC%E5%A4%A7%E5%AD%A6.webp
    if enc in text:
        text = text.replace(enc, f.name)
        fixed += 1

html_path.write_text(text, encoding="utf-8")
print("re-encoded, replaced", fixed, "logo references")
print("new size:", html_path.stat().st_size)
# Sanity: re-read and look for the welcome heading
s = html_path.read_text(encoding="utf-8")
print("contains 高考志愿填报模拟器:", "高考志愿填报模拟器" in s)
print("contains 北京大学.webp:", "北京大学.webp" in s)