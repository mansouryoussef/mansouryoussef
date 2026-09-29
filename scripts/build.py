"""Generate the profile README's SVG assets (light and dark) into ../assets.

Facts come from the career repo's profile.yaml; keep them in step with it.
Fonts: Inter and Montserrat subsets from Google Fonts (SIL OFL), fetched into scripts/fonts/
on first run (not committed) and embedded as woff2. Text is measured with the matching TTF
subsets so wrapping is deterministic. Icons: simple-icons (CC0) in scripts/icons/.

    python3 scripts/build.py
"""
import base64
import io
import math
import os
import re
import string
import urllib.parse
import urllib.request
from xml.sax.saxutils import escape

from PIL import Image, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "assets")
LOGOS = os.path.expanduser("~/dev/career/cv/assets/logos")
MMAI_ICON = os.path.expanduser("~/dev/me-myself-ai/public/icons/master.svg")

W = 1200  # viewBox width of every card; rendered at 100% of the README column

THEMES = {
    "light": dict(
        card="#FFFFFF", card2="#F6F8FA", border="#D0D7DE", grid="#D8DEE4",
        text="#1F2328", body="#31363C", muted="#59636E", faint="#8C959F",
        accent="#126EBF", accent_soft="#DDF0FF", glow="#126EBF", chip="#F6F8FA",
        tile="#FFFFFF", tile_border="#D0D7DE", now="#1A7F37",
    ),
    "dark": dict(
        card="#0D1117", card2="#161B22", border="#30363D", grid="#21262D",
        text="#F0F6FC", body="#D1D9E0", muted="#9198A1", faint="#6E7681",
        accent="#3D8FD8", accent_soft="#0F2A44", glow="#3D8FD8", chip="#161B22",
        tile="#FFFFFF", tile_border="#3D444D", now="#3FB950",
    ),
}

SANS = "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
HEAD = "Montserrat, Inter, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"

TTF = {
    ("Inter", 400): "inter-400", ("Inter", 500): "inter-500", ("Inter", 600): "inter-600",
    ("Montserrat", 700): "montserrat-700",
}
_fonts = {}
CHROME_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"


def fetch_fonts():
    """Download subset fonts from Google Fonts: TTF for measuring, woff2 for embedding."""
    chars = "".join(sorted(set(string.printable.strip() + " ·–—↗●’“”→×…")))
    os.makedirs(os.path.join(HERE, "fonts"), exist_ok=True)
    for (family, weight), stem in TTF.items():
        for ext, ua in (("ttf", "curl/8"), ("woff2", CHROME_UA)):
            path = os.path.join(HERE, "fonts", "%s.%s" % (stem, ext))
            if os.path.exists(path):
                continue
            q = urllib.parse.urlencode({"family": "%s:wght@%d" % (family, weight), "text": chars})
            css = urllib.request.urlopen(urllib.request.Request("https://fonts.googleapis.com/css2?" + q, headers={"User-Agent": ua})).read().decode()
            with open(path, "wb") as f:
                f.write(urllib.request.urlopen(re.search(r"url\((https://[^)]+)\)", css).group(1)).read())


def font(family, weight, size):
    key = (family, weight, size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(os.path.join(HERE, "fonts", TTF[(family, weight)] + ".ttf"), size)
    return _fonts[key]


def tw(text, family, weight, size, spacing=0.0):
    """Rendered width of text in px (plus letter-spacing per glyph)."""
    return font(family, weight, size).getlength(text) + spacing * len(text)


def wrap(text, family, weight, size, maxw):
    lines, line = [], ""
    for word in text.split():
        trial = (line + " " + word).strip()
        if tw(trial, family, weight, size) <= maxw:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def font_css(used):
    rules = []
    for family, weight in sorted(used):
        data = b64(os.path.join(HERE, "fonts", TTF[(family, weight)] + ".woff2"))
        rules.append("@font-face{font-family:%s;font-weight:%d;src:url(data:font/woff2;base64,%s) format('woff2');}" % (family, weight, data))
    return "".join(rules)


def raster_uri(path, px=128):
    im = Image.open(path).convert("RGB")
    im.thumbnail((px, px), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def svg_uri(path, recolor=None):
    with open(path) as f:
        s = f.read()
    if recolor:
        for a, b in recolor.items():
            s = s.replace(a, b)
    return "data:image/svg+xml;base64," + base64.b64encode(s.encode()).decode()


def icon_path(name):
    """Single-path simple-icons glyph (24x24 viewBox)."""
    with open(os.path.join(HERE, "icons", name + ".svg")) as f:
        return re.search(r'<path d="([^"]+)"', f.read()).group(1)


class Doc:
    def __init__(self, h, title, w=W):
        self.w, self.h, self.title, self.parts, self.used, self.css = w, h, title, [], set(), []

    def add(self, s):
        self.parts.append(s)

    def text(self, x, y, s, size, fill, family="Inter", weight=400, anchor="start", spacing=0.0, cls=""):
        self.used.add((family, weight))
        fam = HEAD if family == "Montserrat" else SANS
        ls = ' letter-spacing="%s"' % spacing if spacing else ""
        c = ' class="%s"' % cls if cls else ""
        self.add('<text x="%.1f" y="%.1f" font-family="%s" font-size="%d" font-weight="%d" fill="%s" text-anchor="%s"%s%s>%s</text>'
                 % (x, y, fam, size, weight, fill, anchor, ls, c, escape(s)))

    def render(self):
        style = font_css(self.used) + "".join(self.css)
        return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" role="img" aria-label="%s">'
                '<title>%s</title><style>%s</style>%s</svg>'
                % (self.w, self.h, self.w, self.h, escape(self.title, {'"': "&quot;"}), escape(self.title), style, "".join(self.parts)))


def card_frame(d, t, h, glow=False):
    d.add('<defs><pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1.2" fill="%s"/></pattern>'
          '<radialGradient id="glow" cx="78%%" cy="45%%" r="55%%"><stop offset="0" stop-color="%s" stop-opacity="0.16"/><stop offset="1" stop-color="%s" stop-opacity="0"/></radialGradient>'
          '<clipPath id="round"><rect x="1" y="1" width="%d" height="%d" rx="18"/></clipPath></defs>'
          % (t["grid"], t["glow"], t["glow"], W - 2, h - 2))
    d.add('<rect x="1" y="1" width="%d" height="%d" rx="18" fill="%s"/>' % (W - 2, h - 2, t["card"]))
    if glow:
        d.add('<g clip-path="url(#round)"><rect width="%d" height="%d" fill="url(#dots)" opacity="0.7"/><rect width="%d" height="%d" fill="url(#glow)"/></g>' % (W, h, W, h))
    d.add('<rect x="1" y="1" width="%d" height="%d" rx="18" fill="none" stroke="%s" stroke-width="1.5"/>' % (W - 2, h - 2, t["border"]))


def chip(d, t, x, y, label, size=20, pad=16, h=40, fill=None, stroke=None, color=None, weight=500):
    w = tw(label, "Inter", weight, size) + pad * 2
    d.add('<rect x="%.1f" y="%.1f" width="%.1f" height="%d" rx="%d" fill="%s" stroke="%s" stroke-width="1.2"/>'
          % (x, y, w, h, h // 2, fill or t["chip"], stroke or t["border"]))
    d.text(x + pad, y + h / 2 + size * 0.36, label, size, color or t["body"], weight=weight)
    return w


def chips_flow(d, t, x, y, labels, maxw, gap=10, row_gap=12, **kw):
    cx, cy, h = x, y, kw.get("h", 40)
    for label in labels:
        w = tw(label, "Inter", kw.get("weight", 500), kw.get("size", 20)) + kw.get("pad", 16) * 2
        if cx + w > x + maxw:
            cx, cy = x, cy + h + row_gap
        chip(d, t, cx, cy, label, **kw)
        cx += w + gap
    return cy + h


def logo_tile(d, t, x, y, s, uri, inset=0.18):
    d.add('<rect x="%.1f" y="%.1f" width="%d" height="%d" rx="%d" fill="%s" stroke="%s" stroke-width="1.2"/>'
          % (x, y, s, s, s * 0.24, t["tile"], t["tile_border"]))
    i = s * inset
    d.add('<image x="%.1f" y="%.1f" width="%.1f" height="%.1f" href="%s" preserveAspectRatio="xMidYMid meet"/>'
          % (x + i, y + i, s - 2 * i, s - 2 * i, uri))


# ---------------------------------------------------------------- header

def header(theme):
    t, h = THEMES[theme], 360
    d = Doc(h, "Youssef Mansour, Senior AI Engineer in Helsinki. I build production LLM agent systems.")
    card_frame(d, t, h, glow=True)
    x = 64
    d.text(x, 104, "SENIOR AI ENGINEER  ·  HELSINKI", 19, t["accent"], weight=600, spacing=3)
    d.text(x, 178, "Youssef Mansour", 64, t["text"], family="Montserrat", weight=700, spacing=-1)
    d.text(x, 232, "I build production LLM agent systems:", 25, t["body"])
    d.text(x, 267, "autonomous AI coworkers that run 24/7.", 25, t["body"])
    # status pill
    label = "Now leading Hoxhunt's internal AI platform"
    pw = tw(label, "Inter", 500, 18) + 58
    d.add('<rect x="%d" y="296" width="%.1f" height="36" rx="18" fill="%s" stroke="%s" stroke-width="1.2"/>' % (x, pw, t["card2"], t["border"]))
    d.add('<circle cx="%d" cy="314" r="5" fill="%s"/><circle class="ping" cx="%d" cy="314" r="5" fill="none" stroke="%s" stroke-width="2"/>' % (x + 22, t["now"], x + 22, t["now"]))
    d.text(x + 38, 320, label, 18, t["body"], weight=500)

    # agent graph: an orchestrator fanning out to the systems it depends on
    cx, cy, rx, ry = 945, 180, 175, 118
    nodes = ["evals", "memory", "tools", "budgets", "approvals", "scheduling"]
    pos = []
    for i, name in enumerate(nodes):
        a = math.radians(-90 + i * 60)
        pos.append((cx + rx * math.cos(a), cy + ry * math.sin(a), name))
    d.css.append(
        "@keyframes flow{to{stroke-dashoffset:-240}}"
        "@keyframes breathe{0%,100%{opacity:.35}50%{opacity:.8}}"
        ".edge{stroke-dasharray:3 7}"
        ".comet{stroke-dasharray:18 222;animation:flow 3.2s linear infinite}"
        "@keyframes ping{0%{transform:scale(1);opacity:.9}80%,100%{transform:scale(2.7);opacity:0}}"
        ".ping{transform-box:fill-box;transform-origin:center;animation:ping 2.4s ease-out infinite}"
        ".halo{animation:breathe 3.2s ease-in-out infinite}"
        "@media (prefers-reduced-motion:reduce){.comet,.ping,.halo{animation:none}.comet{opacity:0}}"
    )
    for i, (nx, ny, name) in enumerate(pos):
        path = "M%.1f %.1f L%.1f %.1f" % (cx, cy, nx, ny)
        d.add('<path class="edge" d="%s" stroke="%s" stroke-width="1.6" fill="none"/>' % (path, t["faint"]))
        d.add('<path class="comet" d="%s" stroke="%s" stroke-width="3" stroke-linecap="round" fill="none" style="animation-delay:-%.2fs"/>'
              % (path, t["accent"], i * 0.53))
    d.add('<circle class="halo" cx="%d" cy="%d" r="54" fill="%s" opacity="0.5"/>' % (cx, cy, t["accent_soft"]))
    d.add('<circle cx="%d" cy="%d" r="40" fill="%s" stroke="%s" stroke-width="2"/>' % (cx, cy, t["card"], t["accent"]))
    # robot glyph from the Me, Myself, and AI icon, scaled into the core node
    d.add('<g transform="translate(%d %d) scale(2.1)" stroke="%s" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" fill="none">'
          '<path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></g>'
          % (cx - 25, cy - 27, t["accent"]))
    for nx, ny, name in pos:
        w = tw(name, "Inter", 500, 17) + 30
        d.add('<rect x="%.1f" y="%.1f" width="%.1f" height="34" rx="17" fill="%s" stroke="%s" stroke-width="1.3"/>' % (nx - w / 2, ny - 17, w, t["card2"], t["border"]))
        d.text(nx, ny + 6, name, 17, t["body"], weight=500, anchor="middle")
    return d.render()


# ---------------------------------------------------------------- buttons

BUTTON_ICONS = {
    # stroke icons in a 24x24 box (lucide-style), plus simple-icons fills
    "globe": ('stroke', '<circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>'),
    "mail": ('stroke', '<rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>'),
    "bot": ('stroke', '<path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/>'),
    "linkedin": ('fill', None),
}


def button(theme, label, icon, primary=False):
    t = THEMES[theme]
    size, h, pad = 17, 44, 18
    w = int(pad + 20 + 10 + tw(label, "Inter", 600, size) + pad)
    d = Doc(h, label, w=w)
    fill = t["accent"] if primary else t["card2"]
    stroke = t["accent"] if primary else t["border"]
    color = "#FFFFFF" if primary else t["text"]
    d.add('<rect x="1" y="1" width="%d" height="%d" rx="%d" fill="%s" stroke="%s" stroke-width="1.3"/>' % (w - 2, h - 2, (h - 2) // 2, fill, stroke))
    kind, body = BUTTON_ICONS[icon]
    tr = "translate(%d %d) scale(0.8333)" % (pad, (h - 20) / 2)
    if kind == "stroke":
        d.add('<g transform="%s" fill="none" stroke="%s" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">%s</g>' % (tr, color, body))
    else:
        d.add('<g transform="%s"><path d="%s" fill="%s"/></g>' % (tr, icon_path(icon), color))
    d.text(pad + 30, h / 2 + size * 0.36, label, size, color, weight=600)
    return d.render()


# ---------------------------------------------------------------- now: Hoxhunt

def hoxhunt(theme):
    t = THEMES[theme]
    pad, inner = 56, W - 112
    desc = wrap("Autonomous AI coworkers that run 24/7 alongside Sales, Support, Marketing, Finance and RevOps, "
                "plus self-serve AI tools for six departments. I designed and built the platform's core systems and own it in production end to end.",
                "Inter", 400, 23, inner)
    systems = ["Evaluations", "Scheduling", "Budget enforcement", "Human-in-the-loop approvals", "Access control", "File versioning"]
    # layout pass to find the height
    y_desc = 224
    y_chips = y_desc + len(desc) * 34 + 22
    d = Doc(0, "Now at Hoxhunt: lead engineer of the internal AI platform")
    end = chips_flow(Doc(0, ""), t, pad, y_chips + 52, systems[3:], inner, size=18, pad=14, gap=8)
    h = end + 96
    d.h = h
    card_frame(d, t, h)
    logo_tile(d, t, pad, 50, 68, raster_uri(os.path.join(LOGOS, "hoxhunt.png")), inset=0.14)
    d.text(pad + 88, 80, "Hoxhunt", 27, t["text"], weight=600)
    d.text(pad + 88, 112, "Senior AI Engineer  ·  Dec 2025 – Present", 19, t["muted"])
    lw = tw("NOW", "Inter", 600, 15, 2) + 50
    d.add('<rect x="%.1f" y="62" width="%.1f" height="34" rx="17" fill="none" stroke="%s" stroke-width="1.3"/>' % (W - pad - lw, lw, t["now"]))
    d.add('<circle cx="%.1f" cy="79" r="5" fill="%s"/><circle class="ping" cx="%.1f" cy="79" r="5" fill="none" stroke="%s" stroke-width="2"/>'
          % (W - pad - lw + 20, t["now"], W - pad - lw + 20, t["now"]))
    d.text(W - pad - lw + 34, 84.5, "NOW", 15, t["now"], weight=600, spacing=2)
    d.css.append("@keyframes ping{0%{transform:scale(1);opacity:.9}80%,100%{transform:scale(2.7);opacity:0}}"
        ".ping{transform-box:fill-box;transform-origin:center;animation:ping 2.4s ease-out infinite}"
                 "@media (prefers-reduced-motion:reduce){.ping{animation:none}}")
    d.text(pad, 176, "Lead engineer of the internal AI platform", 33, t["text"], family="Montserrat", weight=700, spacing=-0.5)
    for i, line in enumerate(desc):
        d.text(pad, y_desc + i * 34, line, 23, t["body"])
    chips_flow(d, t, pad, y_chips, systems[:3], inner, size=18, pad=14, gap=8)
    chips_flow(d, t, pad, y_chips + 52, systems[3:], inner, size=18, pad=14, gap=8)
    d.add('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="1.2"/>' % (pad, end + 30, W - pad, end + 30, t["border"]))
    d.text(pad, end + 66, "INTEGRATIONS", 15, t["muted"], weight=600, spacing=2.5)
    d.text(pad + 150, end + 66, "Salesforce   ·   Slack   ·   NetSuite   ·   Gong   ·   Zendesk", 19, t["body"], weight=500)
    return d.render()


# ---------------------------------------------------------------- side project: Me, Myself, and AI

def mmai(theme):
    t = THEMES[theme]
    pad, inner = 56, W - 112
    d = Doc(0, "Me, Myself, and AI: a personal team of AI agents. 20 agents, 97 tools, 24 tool categories, 3 LLM providers.")
    tag = wrap("A personal team of AI agents that research, remember, and get things done.", "Inter", 400, 23, inner)
    y_tag = 168
    y_tiles = y_tag + len(tag) * 34 + 20
    tile_h = 118
    y_feat = y_tiles + tile_h + 44
    feats = [
        ("Memory", "Four layers, with semantic recall on pgvector"),
        ("Delegation", "A planner fans out to specialists in parallel"),
        ("Budgets", "Per-turn caps against a prepaid ledger"),
        ("Evals", "33-case golden set with a 95% pass gate"),
    ]
    h = y_feat + 2 * 64 + 34
    d.h = h
    card_frame(d, t, h, glow=True)
    icon = svg_uri(MMAI_ICON)
    logo_tile(d, t, pad, 50, 68, icon, inset=0.12)
    d.text(pad + 88, 80, "Me, Myself, and AI", 27, t["text"], weight=600)
    d.text(pad + 88, 112, "memyselfai.io  ↗", 19, t["accent"], weight=500)
    lab = "PRIVATE BETA"
    lw = tw(lab, "Inter", 600, 15, 2) + 32
    d.add('<rect x="%.1f" y="62" width="%.1f" height="34" rx="17" fill="none" stroke="%s" stroke-width="1.3"/>' % (W - pad - lw, lw, t["accent"]))
    d.text(W - pad - lw + 16, 84.5, lab, 15, t["accent"], weight=600, spacing=2)
    for i, line in enumerate(tag):
        d.text(pad, y_tag + i * 34, line, 23, t["body"])
    metrics = [("20", "agents"), ("97", "tools"), ("24", "tool categories"), ("3", "LLM providers")]
    gap = 18
    tw_ = (inner - gap * 3) / 4.0
    for i, (num, label) in enumerate(metrics):
        x = pad + i * (tw_ + gap)
        d.add('<rect x="%.1f" y="%d" width="%.1f" height="%d" rx="14" fill="%s" stroke="%s" stroke-width="1.2"/>' % (x, y_tiles, tw_, tile_h, t["card2"], t["border"]))
        d.text(x + 26, y_tiles + 64, num, 46, t["accent"], family="Montserrat", weight=700)
        d.text(x + 26, y_tiles + 96, label, 19, t["muted"], weight=500)
    colw = (inner - 40) / 2.0
    for i, (k, v) in enumerate(feats):
        x = pad + (i % 2) * (colw + 40)
        y = y_feat + (i // 2) * 64
        d.add('<rect x="%.1f" y="%d" width="4" height="46" rx="2" fill="%s"/>' % (x, y - 6, t["accent"]))
        d.text(x + 20, y + 12, k.upper(), 14, t["muted"], weight=600, spacing=2.2)
        d.text(x + 20, y + 38, v, 20, t["body"], weight=500)
    return d.render()


# ---------------------------------------------------------------- experience timeline

ROLES = [
    ("Hoxhunt", "Senior AI Engineer", "Dec 2025 – Present", "Lead engineer of the internal AI platform: autonomous AI coworkers running 24/7.", ("png", "hoxhunt.png", 0.14)),
    ("Clair", "Founding Engineer", "May 2025 – Dec 2025", "Took an AI-powered demand planning tool from zero to production.", ("svg", "clair.svg", 0.2)),
    ("Wolt", "Senior Software Engineer", "May 2022 – May 2025", "Scaled self-service merchant onboarding to multiple countries.", ("png", "wolt.jpg", 0.0)),
    ("Smartly.io", "Full Stack Developer", "May 2020 – May 2022", "Delivered Google SSO, access control and a global notifications system.", ("svg", "smartly.svg", 0.16)),
    ("Basware", "Software Engineer Intern", "May 2019 – Aug 2019", "Designed and built web mockups in Angular 7 and Angular Material.", ("svg", "basware-mark.svg", 0.08)),
]


def experience(theme):
    t = THEMES[theme]
    pad, row = 56, 104
    h = 44 + row * len(ROLES) + 20
    d = Doc(h, "Experience: Hoxhunt, Clair, Wolt, Smartly.io, Basware")
    card_frame(d, t, h)
    s, lx = 60, pad
    first_y = 44
    d.add('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="2" stroke-dasharray="2 6" stroke-linecap="round"/>'
          % (lx + s / 2, first_y + s, lx + s / 2, first_y + row * (len(ROLES) - 1), t["border"]))
    for i, (org, role, dates, line, (kind, fname, inset)) in enumerate(ROLES):
        y = first_y + i * row
        path = os.path.join(LOGOS, fname)
        uri = raster_uri(path) if kind == "png" else svg_uri(path)
        if fname == "wolt.jpg":
            d.add('<clipPath id="w%d"><rect x="%d" y="%d" width="%d" height="%d" rx="%d"/></clipPath>' % (i, lx, y, s, s, s * 0.24))
            d.add('<image x="%d" y="%d" width="%d" height="%d" href="%s" clip-path="url(#w%d)"/>' % (lx, y, s, s, uri, i))
            d.add('<rect x="%d" y="%d" width="%d" height="%d" rx="%d" fill="none" stroke="%s" stroke-width="1.2"/>' % (lx, y, s, s, s * 0.24, t["tile_border"]))
        else:
            logo_tile(d, t, lx, y, s, uri, inset=inset)
        tx = lx + s + 28
        d.text(tx, y + 24, org, 23, t["text"], weight=600)
        d.text(tx + tw(org, "Inter", 600, 23) + 14, y + 24, role, 20, t["accent"] if i == 0 else t["muted"], weight=500)
        d.text(W - pad, y + 24, dates, 17, t["muted"], anchor="end")
        d.text(tx, y + 56, line, 19, t["body"])
    return d.render()


# ---------------------------------------------------------------- stack

STACK = [
    ("AI & LLMs", [("anthropic", "Anthropic"), ("claude", "Claude Code"), ("openai", "OpenAI"), ("googlegemini", "Gemini"), ("vercel", "AI SDK"), (None, "Tool calling"), (None, "Evals"), (None, "RAG")]),
    ("Product", [("typescript", "TypeScript"), ("react", "React"), ("nextdotjs", "Next.js"), ("python", "Python"), ("fastapi", "FastAPI"), ("nodedotjs", "Node.js"), ("tailwindcss", "Tailwind")]),
    ("Data & platform", [("postgresql", "PostgreSQL"), (None, "pgvector"), ("redis", "Redis"), ("prisma", "Prisma"), ("docker", "Docker"), ("googlecloud", "Google Cloud"), (None, "Inngest")]),
]


def stack(theme):
    t = THEMES[theme]
    pad, ch, size, ipad = 56, 42, 18, 14
    label_h = 34
    rows = []
    for label, items in STACK:
        cx, cy, placed = pad, 0, []
        for icon, name in items:
            w = ipad + (26 if icon else 0) + tw(name, "Inter", 500, size) + ipad
            if cx + w > W - pad:
                cx, cy = pad, cy + ch + 12
            placed.append((cx, cy, w, icon, name))
            cx += w + 10
        rows.append((label, placed, label_h + cy + ch))
    h = 44 + sum(r[2] for r in rows) + 34 * (len(rows) - 1) + 48
    d = Doc(h, "Stack: " + "; ".join("%s: %s" % (l, ", ".join(n for _, n in items)) for l, items in STACK))
    card_frame(d, t, h)
    y0 = 44
    for label, placed, rh in rows:
        d.text(pad, y0 + 18, label.upper(), 14, t["muted"], weight=600, spacing=2.2)
        for x, yy, w, icon, name in placed:
            y = y0 + label_h + yy
            d.add('<rect x="%.1f" y="%.1f" width="%.1f" height="%d" rx="10" fill="%s" stroke="%s" stroke-width="1.2"/>' % (x, y, w, ch, t["card2"], t["border"]))
            tx = x + ipad
            if icon:
                d.add('<g transform="translate(%.1f %.1f) scale(0.75)"><path d="%s" fill="%s"/></g>' % (tx, y + (ch - 18) / 2, icon_path(icon), t["text"]))
                tx += 26
            d.text(tx, y + ch / 2 + size * 0.36, name, size, t["body"], weight=500)
        y0 += rh + 34
    return d.render()


def main():
    fetch_fonts()
    os.makedirs(OUT, exist_ok=True)
    jobs = {"header": header, "now-hoxhunt": hoxhunt, "side-mmai": mmai, "experience": experience, "stack": stack}
    for theme in THEMES:
        for name, fn in jobs.items():
            with open(os.path.join(OUT, "%s-%s.svg" % (name, theme)), "w") as f:
                f.write(fn(theme))
        for name, label, icon, primary in [("btn-website", "youssef.fi", "globe", True), ("btn-linkedin", "LinkedIn", "linkedin", False),
                                           ("btn-email", "Email", "mail", False), ("btn-mmai", "memyselfai.io", "bot", False)]:
            with open(os.path.join(OUT, "%s-%s.svg" % (name, theme)), "w") as f:
                f.write(button(theme, label, icon, primary))
    for f in sorted(os.listdir(OUT)):
        print("%-28s %6.1f KB" % (f, os.path.getsize(os.path.join(OUT, f)) / 1024.0))


if __name__ == "__main__":
    main()
