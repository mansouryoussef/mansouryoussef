"""Generate the README's name wordmark (light and dark) into ../assets.

The wordmark is the only image on the profile: the name set in Newsreader, a serif that
GitHub's own fonts cannot provide. Everything else in the README is plain text so it
stays sharp, searchable and readable on phones.

The SVG is sized tightly to the glyphs and shown at its natural width, so it never
scales down on mobile. Transparent background, GitHub's own text colours per theme.
Font: Newsreader (SIL OFL) from Google Fonts, subset to the name, fetched into
scripts/fonts/ on first run (not committed): TTF to measure, woff2 to embed.

    python3 scripts/build.py
"""
import base64
import os
import re
import urllib.parse
import urllib.request
from xml.sax.saxutils import escape

from PIL import ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "assets")
FONTS = os.path.join(HERE, "fonts")

NAME = "Youssef Mansour"
SPEC = "Newsreader:opsz,wght@72,500"
SIZE = 44
TRACKING = -0.5
GAP = 14  # transparent space under the name, so the intro does not crowd it
COLOURS = {"light": "#1F2328", "dark": "#F0F6FC"}  # GitHub Primer fg.default

CHROME_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"


def fetch_font():
    os.makedirs(FONTS, exist_ok=True)
    for ext, ua in (("ttf", "curl/8"), ("woff2", CHROME_UA)):
        path = os.path.join(FONTS, "newsreader." + ext)
        if os.path.exists(path):
            continue
        q = urllib.parse.urlencode({"family": SPEC, "text": NAME})
        css = urllib.request.urlopen(urllib.request.Request("https://fonts.googleapis.com/css2?" + q, headers={"User-Agent": ua})).read().decode()
        with open(path, "wb") as f:
            f.write(urllib.request.urlopen(re.search(r"url\((https://[^)]+)\)", css).group(1)).read())


def wordmark(colour):
    font = ImageFont.truetype(os.path.join(FONTS, "newsreader.ttf"), SIZE)
    left, top, right, bottom = font.getbbox(NAME, anchor="ls")
    w = int(round(right - left + TRACKING * (len(NAME) - 1))) + 2
    h = int(round(bottom - top)) + 4 + GAP
    with open(os.path.join(FONTS, "newsreader.woff2"), "rb") as f:
        data = base64.b64encode(f.read()).decode()
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" role="img" aria-label="%s">'
            '<title>%s</title>'
            "<style>@font-face{font-family:'Newsreader';font-weight:500;src:url(data:font/woff2;base64,%s) format('woff2')}</style>"
            '<text x="%.1f" y="%.1f" font-family="Newsreader, Georgia, serif" font-size="%d" font-weight="500" letter-spacing="%s" fill="%s">%s</text>'
            '</svg>' % (w, h, w, h, NAME, NAME, data, -left, -top + 2, SIZE, TRACKING, colour, escape(NAME))), w, h


def main():
    fetch_font()
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        os.remove(os.path.join(OUT, f))
    for theme, colour in COLOURS.items():
        svg, w, h = wordmark(colour)
        with open(os.path.join(OUT, "name-%s.svg" % theme), "w") as f:
            f.write(svg)
    print("name-{light,dark}.svg  %dx%d" % (w, h))


if __name__ == "__main__":
    main()
