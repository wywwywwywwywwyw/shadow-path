"""Rebuild the two self-hosted web fonts as subsets of the characters the game actually shows.

The game used to load ZCOOL XiaoWei and Marcellus from Google Fonts, which is slow or blocked in
mainland China. Now both live in vendor/fonts/ as woff2 files that hold only the glyphs index.html
uses (the full Chinese font is several MB; the subset is a few dozen KB). Google Fonts' `text=`
parameter does the subsetting, so this script needs the network but no third-party packages.

  python tools/fonts.py           re-download both subsets after changing any Chinese text
  python tools/fonts.py --check   exit 1 if index.html uses a character the subset lacks

Characters: every non-ASCII character in index.html plus printable ASCII. The list that was
downloaded is kept in vendor/fonts/chars.txt so --check works offline.
Behind a proxy, set HTTPS_PROXY first (urllib picks it up).
"""
import os
import re
import sys
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'vendor', 'fonts')
CHARS = os.path.join(OUT, 'chars.txt')
ASCII = ''.join(chr(c) for c in range(32, 127))
# Google serves woff2 only to browsers it recognises
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'
FONTS = [
    # (Google family, file name, which characters)
    ('ZCOOL XiaoWei', 'zcool-xiaowei.woff2', 'all'),
    ('Marcellus', 'marcellus.woff2', 'latin'),
]


def used_chars():
    with open(os.path.join(ROOT, 'index.html'), encoding='utf-8') as f:
        html = f.read()
    return ''.join(sorted(set(ASCII) | {c for c in html if ord(c) > 126}))


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def build():
    chars = used_chars()
    latin = ''.join(c for c in chars if ord(c) < 0x2000)
    os.makedirs(OUT, exist_ok=True)
    for family, name, which in FONTS:
        text = chars if which == 'all' else latin
        css = fetch('https://fonts.googleapis.com/css2?' + urllib.parse.urlencode(
            {'family': family, 'text': text, 'display': 'swap'})).decode('utf-8')
        urls = re.findall(r"url\((https://[^)]+)\)\s*format\('woff2'\)", css)
        if len(urls) != 1:
            sys.exit(f'{family}: expected one woff2 url, got {len(urls)}\n{css}')
        data = fetch(urls[0])
        with open(os.path.join(OUT, name), 'wb') as f:
            f.write(data)
        print(f'{name}: {len(text)} characters, {len(data) // 1024} KB')
    with open(CHARS, 'w', encoding='utf-8', newline='\n') as f:
        f.write(chars + '\n')


def check():
    try:
        with open(CHARS, encoding='utf-8') as f:
            have = set(f.read().rstrip('\n'))
    except FileNotFoundError:
        sys.exit('vendor/fonts/chars.txt is missing: run python tools/fonts.py')
    missing = sorted(set(used_chars()) - have)
    if missing:
        print('index.html uses characters the font subset lacks: ' + ''.join(missing))
        print('run: python tools/fonts.py')
        sys.exit(1)
    print('font subset covers every character in index.html')


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    check() if '--check' in sys.argv[1:] else build()
