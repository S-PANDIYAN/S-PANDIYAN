#!/usr/bin/env python3
"""Generate the animated 'RAG Pipeline' hero SVG (dark + light) for the profile README.

Pipeline (correct RAG steps):
  Query -> 1 Query Embedding -> 2 Similarity Search (pgvector) ->
  3 Top-K Retrieved Chunks -> 4 Prompt Construction (query + context) ->
  5 LLM Generation -> Final Answer

The answer panel streams Pandiyan's profile; his portrait renders as
terminal ASCII art (pure SVG text — every run pinned to an explicit x,
because browsers collapse whitespace in SVG text).
"""

from pathlib import Path

W, H = 900, 570
PHOTO_SRC = Path(r"C:\Users\Pandiyan\OneDrive\Pictures\Screenshots\Screenshot 2026-07-19 114934.png")
CROP_BOX = (58, 28, 198, 168)       # passport-style head-and-shoulders square

# ASCII portrait grid (right column of the answer panel)
COLS, ROWS = 110, 64
RAMP = "·░▒▓█"   # · ░ ▒ ▓ █  solid shade blocks — read as pixels
BG_CUTOFF = 240               # only near-white is blanked; face stays continuous
ELLIPSE = (0.5, 0.47, 0.45, 0.55)   # cx, cy, rx, ry — mask out busy background
EDGE_R, EDGE_D = 0.8, 90      # near ellipse edge, drop light cells (bg falloff)
PX0, PY0 = 636, 278           # portrait top-left
PFS, PLH = 3.35, 3.45         # portrait font size / line height

THEMES = {
    "dark": dict(
        bg1="#0a0e1a", bg2="#0f1424", grid="#172037",
        edge="#263550", panel="#0d1326", panel_stroke="#1e2b4a",
        flow="#22d3ee", node="#0f1730", accent="#a78bfa",
        text="#e6e9f2", sub="#22d3ee", muted="#7d889e", chip="#101a33",
        g1="#a78bfa", g2="#22d3ee", ok="#27c93f",
        shadow="#000000", shadow_op="0.45",
        pal=["#0d4254", "#11607a", "#0e86a0", "#16abc4", "#3fc9e0", "#7adef0", "#aeeffb", "#e6fdff"],  # portrait tone ramp
    ),
    "light": dict(
        bg1="#ffffff", bg2="#eef2fb", grid="#e4e9f5",
        edge="#cdd6e8", panel="#f7f9fe", panel_stroke="#dbe3f2",
        flow="#0891b2", node="#ffffff", accent="#7c3aed",
        text="#1f2937", sub="#0891b2", muted="#64748b", chip="#eef2fb",
        g1="#7c3aed", g2="#0891b2", ok="#16a34a",
        shadow="#64748b", shadow_op="0.30",
        pal=["#cfe2ea", "#a6c9d6", "#79a9bc", "#4a92ab", "#20789a", "#0e5f7c", "#0a4257", "#072b3a"],  # light: dense = darkest
    ),
}

QUERY = '"who is Pandiyan S?"'
SKILLS_ROW1 = ["Python", "PyTorch", "TensorFlow", "scikit-learn"]
SKILLS_ROW2 = ["FastAPI", "PostgreSQL", "LangChain", "Docker"]
MOTTO = '"Learn relentlessly. Build fearlessly. Ship something that matters."'
LINKS = "in/pandiyan-s-947239293 · leetcode/Pandiyan_ML · pandiyanshanmugam3105@gmail.com"

PY = 150  # pipeline row centre

# connector path data
_PATHS = {
    "c0": f"M120,68 L120,{PY-26}",        # query -> embed
    "c1": f"M146,{PY} L205,{PY}",         # embed -> similarity search
    "c2": f"M305,{PY} L352,{PY}",         # search -> top-k
    "c3": f"M428,{PY} L462,{PY}",         # top-k -> prompt
    "c4": f"M558,{PY} L595,{PY}",         # prompt -> llm
    "c5": f"M705,{PY} L785,{PY}",         # llm -> answer
    "c6": f"M815,{PY+30} L815,230",       # answer -> panel
}


def ascii_portrait():
    """Photo -> grid of (char, band 0..3); band picks the palette colour.

    Shadow-lifting gamma separates hair / features / skin into distinct
    density levels; an elliptical mask removes the busy background.
    """
    from PIL import Image, ImageOps, ImageFilter
    im = ImageOps.exif_transpose(Image.open(PHOTO_SRC))
    im = im.crop(CROP_BOX).convert("L")
    im = ImageOps.autocontrast(im, cutoff=2)
    im = im.point([int(255 * (i / 255) ** 0.5) for i in range(256)])
    im = im.resize((COLS, ROWS), Image.LANCZOS)
    im = im.filter(ImageFilter.UnsharpMask(radius=1, percent=150, threshold=2))
    px = im.load()
    ecx, ecy, erx, ery = ELLIPSE
    grid = []
    for r in range(ROWS):
        row = []
        for cix in range(COLS):
            nx = (cix / COLS - ecx) / erx
            ny = (r / ROWS - ecy) / ery
            rad = nx * nx + ny * ny
            lum = px[cix, r]
            d = 255 - lum
            # outside ellipse, near-white, or light background near the edge -> blank
            if rad > 1 or lum >= BG_CUTOFF or (rad > EDGE_R * EDGE_R and d < EDGE_D):
                row.append((" ", 0))
                continue
            ch = RAMP[min(len(RAMP) - 1, int(d * len(RAMP) / 256))]
            band = min(7, d * 8 // 256)
            row.append((ch, band))
        grid.append(row)
    # denoise: drop isolated specks (fewer than 2 visible 8-neighbours)
    clean = [row[:] for row in grid]
    for r in range(ROWS):
        for cix in range(COLS):
            if grid[r][cix][0] == " ":
                continue
            n = sum(1 for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                    if (dr or dc) and 0 <= r + dr < ROWS and 0 <= cix + dc < COLS
                    and grid[r + dr][cix + dc][0] != " ")
            if n < 2:
                clean[r][cix] = (" ", 0)
    return clean


PORTRAIT = ascii_portrait()


def row_runs(row):
    """Group a row into (start_col, band, text) runs of non-space chars.

    Browsers collapse whitespace in SVG text (xml:space is ignored by Chrome),
    so every run carries its own explicit x position instead of leading spaces.
    """
    runs = []
    cur_band, start, buf = None, 0, ""
    for i, (ch, b) in enumerate(row):
        if ch == " ":
            if buf:
                runs.append((start, cur_band, buf))
                buf = ""
            cur_band = None
            continue
        if cur_band is None:
            cur_band, start = b, i
        elif b != cur_band:
            runs.append((start, cur_band, buf))
            cur_band, start, buf = b, i, ""
        buf += ch
    if buf:
        runs.append((start, cur_band, buf))
    return runs


def typed(clip_id, x, y, w, begin, dur):
    """A clipPath whose width animates -> typing reveal."""
    return (f'<clipPath id="{clip_id}"><rect x="{x}" y="{y}" width="0" height="34">'
            f'<animate attributeName="width" from="0" to="{w}" begin="{begin}s" dur="{dur}s" fill="freeze"/>'
            f'</rect></clipPath>')


def chips(c, skills, x0, top, begin0):
    out = []
    x = x0
    for i, s in enumerate(skills):
        w = len(s) * 6.8 + 34
        beg = begin0 + i * 0.15
        cy = top + 12
        out.append(
            f'<g opacity="0">'
            f'<animate attributeName="opacity" from="0" to="1" begin="{beg:.2f}s" dur="0.45s" fill="freeze"/>'
            f'<animateTransform attributeName="transform" type="translate" from="0 7" to="0 0" '
            f'begin="{beg:.2f}s" dur="0.45s" fill="freeze"/>'
            f'<rect x="{x:.0f}" y="{top}" width="{w:.0f}" height="24" rx="12" fill="{c["chip"]}" '
            f'stroke="{c["flow"]}" stroke-opacity="0.45"/>'
            f'<circle cx="{x+13:.0f}" cy="{cy}" r="3" fill="{c["flow"]}"/>'
            f'<text x="{x+23:.0f}" y="{cy+4}" class="mono" font-size="11.5" fill="{c["text"]}">{s}</text>'
            f'</g>'
        )
        x += w + 10
    return "".join(out)


def sheen(cx, cy, rx, ry):
    return f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="#ffffff" opacity="0.14"/>'


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def step_label(a, c, x, y, text):
    a(f'<text x="{x}" y="{y}" text-anchor="middle" class="mono" font-size="8.5" '
      f'letter-spacing="0.5" fill="{c["muted"]}">{text}</text>')


def build(theme):
    c = THEMES[theme]
    pal = c["pal"]
    out = []
    a = out.append

    a(f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
      f'width="{W}" height="{H}" viewBox="0 0 {W} {H}" fill="none" role="img" '
      f'aria-label="Pandiyan S - Machine Learning Engineer - RAG pipeline profile">')

    # ---------- defs ----------
    a('<defs>')
    a(f'<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
      f'<stop offset="0" stop-color="{c["bg1"]}"/><stop offset="1" stop-color="{c["bg2"]}"/></linearGradient>')
    a(f'<linearGradient id="border" x1="0" y1="0" x2="1" y2="0">'
      f'<stop offset="0" stop-color="{c["g1"]}"/><stop offset="0.5" stop-color="{c["g2"]}"/>'
      f'<stop offset="1" stop-color="{c["g1"]}"/></linearGradient>')
    a(f'<linearGradient id="name" gradientUnits="userSpaceOnUse" x1="70" y1="0" x2="500" y2="0">'
      f'<stop offset="0" stop-color="{c["g1"]}"/><stop offset="0.5" stop-color="{c["g2"]}"/>'
      f'<stop offset="1" stop-color="{c["g1"]}"/>'
      f'<animateTransform attributeName="gradientTransform" type="translate" from="-430 0" to="430 0" '
      f'dur="4s" repeatCount="indefinite"/></linearGradient>')
    a(f'<radialGradient id="glow" cx="0.5" cy="0.5" r="0.5">'
      f'<stop offset="0" stop-color="{c["flow"]}" stop-opacity="0.8"/>'
      f'<stop offset="1" stop-color="{c["flow"]}" stop-opacity="0"/></radialGradient>')
    a('<filter id="soft" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="3"/></filter>')
    a(f'<filter id="d3" x="-30%" y="-30%" width="160%" height="170%">'
      f'<feDropShadow dx="0" dy="7" stdDeviation="8" flood-color="{c["shadow"]}" flood-opacity="{c["shadow_op"]}"/></filter>')
    a('<style>.mono{font-family:\'JetBrains Mono\',\'Fira Code\',Consolas,Menlo,monospace}'
      '.sans{font-family:\'Segoe UI\',Inter,system-ui,sans-serif}</style>')

    # typing clips
    a(typed("q1", 64, 36, 330, 0.3, 0.9))          # query
    a(typed("a1", 66, 262, 340, 2.0, 0.7))          # name
    a(typed("a2", 66, 300, 480, 2.7, 0.7))          # role
    a(typed("a3", 66, 328, 560, 3.4, 0.7))          # info
    a(typed("a4", 66, 438, 620, 5.6, 0.9))          # motto
    a(typed("a5", 66, 468, 620, 6.4, 0.9))          # links
    a('</defs>')

    # ---------- card ----------
    a(f'<rect x="4" y="4" width="{W-8}" height="{H-8}" rx="20" fill="url(#bg)"/>')
    a(f'<g stroke="{c["grid"]}" stroke-width="1">')
    for gx in range(60, W, 60):
        a(f'<line x1="{gx}" y1="6" x2="{gx}" y2="{H-6}"/>')
    for gy in range(60, H, 60):
        a(f'<line x1="6" y1="{gy}" x2="{W-6}" y2="{gy}"/>')
    a('</g>')
    a(f'<rect x="4" y="4" width="{W-8}" height="{H-8}" rx="20" fill="none" stroke="url(#border)" '
      f'stroke-width="2" stroke-dasharray="14 10" stroke-opacity="0.9">'
      f'<animate attributeName="stroke-dashoffset" from="0" to="-240" dur="6s" repeatCount="indefinite"/></rect>')

    # ---------- query box ----------
    a(f'<rect x="40" y="28" width="380" height="40" rx="20" fill="{c["panel"]}" '
      f'stroke="{c["panel_stroke"]}" stroke-width="1.5" filter="url(#d3)"/>')
    a(f'<text class="mono" font-size="14" clip-path="url(#q1)">'
      f'<tspan x="64" y="53" fill="{c["ok"]}">&#10095; </tspan><tspan fill="{c["text"]}">{QUERY}</tspan></text>')
    a(f'<rect x="382" y="38" width="9" height="20" fill="{c["flow"]}">'
      f'<animate attributeName="opacity" values="1;1;0;0" dur="1s" repeatCount="indefinite"/></rect>')
    a(f'<text x="452" y="53" class="mono" font-size="11" letter-spacing="2" fill="{c["muted"]}">RAG&#160;PIPELINE&#160;/&#160;PROFILE&#160;v2.0</text>')
    a(f'<circle cx="838" cy="48" r="4" fill="{c["ok"]}">'
      f'<animate attributeName="opacity" values="1;0.2;1" dur="1.4s" repeatCount="indefinite"/></circle>')
    a(f'<text x="828" y="53" text-anchor="end" class="mono" font-size="11" fill="{c["muted"]}">online</text>')

    # ---------- pipeline connectors ----------
    a(f'<g stroke="{c["edge"]}" stroke-width="1.6" fill="none">')
    for pid, d in _PATHS.items():
        a(f'<path id="{pid}" d="{d}"/>')
    a('</g>')
    a(f'<g stroke="{c["flow"]}" stroke-width="1.6" fill="none" stroke-opacity="0.55">')
    for pid, dur in (("c0", 1.6), ("c1", 1.3), ("c2", 1.2), ("c3", 1.2), ("c4", 1.2), ("c5", 1.3), ("c6", 1.5)):
        a(f'<path d="{_PATHS[pid]}" stroke-dasharray="3 10">'
          f'<animate attributeName="stroke-dashoffset" from="0" to="-13" dur="{dur}s" repeatCount="indefinite"/></path>')
    a('</g>')
    a(f'<g fill="{c["flow"]}">')
    for pid, dur, beg in (("c0", 1.5, 0.2), ("c1", 1.2, 0.5), ("c2", 1.1, 0.8), ("c3", 1.1, 1.0),
                          ("c4", 1.1, 1.2), ("c5", 1.2, 1.4), ("c6", 1.4, 1.7)):
        a(f'<circle r="3.2"><animateMotion dur="{dur}s" begin="{beg}s" repeatCount="indefinite">'
          f'<mpath xlink:href="#{pid}"/></animateMotion>'
          f'<animate attributeName="opacity" values="0;1;1;0" dur="{dur}s" begin="{beg}s" repeatCount="indefinite"/></circle>')
    a('</g>')

    # ---- 1. QUERY EMBEDDING ----
    a(f'<circle cx="120" cy="{PY}" r="26" fill="{c["node"]}" stroke="{c["flow"]}" stroke-width="2" filter="url(#d3)">'
      f'<animate attributeName="stroke-opacity" values="0.5;1;0.5" dur="2.2s" repeatCount="indefinite"/></circle>')
    a(sheen(112, PY - 10, 10, 6))
    a(f'<text x="120" y="{PY+5}" text-anchor="middle" font-size="15">&#129522;</text>')
    step_label(a, c, 120, PY + 44, "1&#160;&#183;&#160;QUERY")
    step_label(a, c, 120, PY + 55, "EMBEDDING")

    # ---- 2. SIMILARITY SEARCH (pgvector cylinder) ----
    dbx, dbw = 205, 100
    a(f'<g filter="url(#d3)">')
    a(f'<path d="M{dbx},{PY-24} L{dbx},{PY+20} A50,12 0 0 0 {dbx+dbw},{PY+20} L{dbx+dbw},{PY-24}" '
      f'fill="{c["node"]}" stroke="{c["accent"]}" stroke-width="1.8"/>')
    a(f'<ellipse cx="{dbx+dbw/2}" cy="{PY-24}" rx="50" ry="12" fill="{c["node"]}" stroke="{c["accent"]}" stroke-width="1.8"/>')
    a('</g>')
    for i, dy in enumerate((-5, 7)):
        a(f'<path d="M{dbx},{PY+dy} A50,12 0 0 0 {dbx+dbw},{PY+dy}" fill="none" stroke="{c["accent"]}" '
          f'stroke-width="1.2" stroke-opacity="0.6">'
          f'<animate attributeName="stroke-opacity" values="0.25;0.85;0.25" dur="2s" begin="{i*0.7}s" repeatCount="indefinite"/></path>')
    a(f'<text x="{dbx+dbw/2}" y="{PY-20}" text-anchor="middle" class="mono" font-size="9.5" fill="{c["sub"]}">pgvector</text>')
    step_label(a, c, dbx + dbw / 2, PY + 50, "2&#160;&#183;&#160;SIMILARITY")
    step_label(a, c, dbx + dbw / 2, PY + 61, "SEARCH")

    # ---- 3. TOP-K RETRIEVED CHUNKS (stack) ----
    tkx = 390
    for i, (dy, beg) in enumerate(((-18, 0.0), (0, 0.4), (18, 0.8))):
        a(f'<g opacity="0.9">'
          f'<rect x="{tkx-34}" y="{PY+dy-8}" width="60" height="16" rx="4" fill="{c["chip"]}" '
          f'stroke="{c["flow"]}" stroke-opacity="0.7">'
          f'<animate attributeName="stroke-opacity" values="0.4;1;0.4" dur="1.8s" begin="{beg}s" repeatCount="indefinite"/></rect>'
          f'<text x="{tkx-4}" y="{PY+dy+3}" text-anchor="middle" class="mono" font-size="8" fill="{c["sub"]}">chunk&#160;{i+1}</text>'
          f'</g>')
    step_label(a, c, tkx - 4, PY + 44, "3&#160;&#183;&#160;TOP-K")
    step_label(a, c, tkx - 4, PY + 55, "CHUNKS")

    # ---- 4. PROMPT CONSTRUCTION ----
    a(f'<rect x="462" y="{PY-30}" width="96" height="60" rx="12" fill="{c["node"]}" stroke="{c["accent"]}" '
      f'stroke-width="1.8" filter="url(#d3)">'
      f'<animate attributeName="stroke-opacity" values="0.5;1;0.5" dur="2.3s" repeatCount="indefinite"/></rect>')
    a(sheen(488, PY - 18, 16, 5))
    a(f'<text x="510" y="{PY-2}" text-anchor="middle" font-size="14">&#128221;</text>')
    a(f'<text x="510" y="{PY+16}" text-anchor="middle" class="mono" font-size="9" letter-spacing="1" fill="{c["sub"]}">PROMPT</text>')
    step_label(a, c, 510, PY + 50, "4&#160;&#183;&#160;PROMPT&#160;CONSTRUCTION")
    step_label(a, c, 510, PY + 61, "(query&#160;+&#160;context)")

    # ---- 5. LLM ----
    a(f'<rect x="595" y="{PY-38}" width="110" height="76" rx="16" fill="url(#glow)" filter="url(#soft)" opacity="0.5"/>')
    a(f'<rect x="595" y="{PY-32}" width="110" height="64" rx="14" fill="{c["node"]}" stroke="{c["flow"]}" '
      f'stroke-width="2" filter="url(#d3)">'
      f'<animate attributeName="stroke-opacity" values="0.6;1;0.6" dur="2.4s" repeatCount="indefinite"/></rect>')
    a(sheen(625, PY - 20, 18, 5))
    a(f'<text x="650" y="{PY-2}" text-anchor="middle" font-size="18">&#129504;</text>')
    a(f'<text x="650" y="{PY+18}" text-anchor="middle" class="mono" font-size="10" letter-spacing="2" fill="{c["sub"]}">LLM</text>')
    step_label(a, c, 650, PY + 50, "5&#160;&#183;&#160;GENERATION")

    # ---- FINAL ANSWER ----
    a(f'<circle cx="815" cy="{PY}" r="28" fill="{c["node"]}" stroke="{c["ok"]}" stroke-width="2" filter="url(#d3)">'
      f'<animate attributeName="r" values="28;30.5;28" dur="2.2s" repeatCount="indefinite"/></circle>')
    a(sheen(806, PY - 10, 10, 6))
    a(f'<text x="815" y="{PY+5}" text-anchor="middle" font-size="14">&#9889;</text>')
    step_label(a, c, 815, PY + 46, "FINAL&#160;ANSWER")

    # ---------- answer panel ----------
    a(f'<rect x="40" y="230" width="{W-80}" height="300" rx="16" fill="{c["panel"]}" '
      f'stroke="{c["panel_stroke"]}" stroke-width="1.5" filter="url(#d3)"/>')
    a(f'<circle cx="62" cy="248" r="4.5" fill="#ff5f56"/><circle cx="78" cy="248" r="4.5" fill="#ffbd2e"/>'
      f'<circle cx="94" cy="248" r="4.5" fill="{c["ok"]}"/>')
    a(f'<text x="112" y="252" class="mono" font-size="11" fill="{c["muted"]}">generated_profile.md&#160;&#160;&#183;&#160;&#160;streaming&#8230;</text>')

    # streamed profile (left column)
    a(f'<text class="sans" font-size="30" font-weight="800" clip-path="url(#a1)">'
      f'<tspan x="66" y="290" fill="url(#name)">PANDIYAN&#160;S</tspan></text>')
    a(f'<text class="mono" font-size="14" clip-path="url(#a2)">'
      f'<tspan x="66" y="312" fill="{c["sub"]}">Machine Learning Engineer &#183; Generative AI &amp; RAG</tspan></text>')
    a(f'<text class="mono" font-size="12.5" clip-path="url(#a3)">'
      f'<tspan x="66" y="342" fill="{c["muted"]}">&#127891; B.Tech &#183; AI &amp; ML&#160;&#160;&#160;&#128205; India&#160;&#160;&#160;'
      f'&#128301; building RAG &amp; GenAI systems</tspan></text>')

    # skill chips
    a(chips(c, SKILLS_ROW1, 66, 360, 4.1))
    a(chips(c, SKILLS_ROW2, 66, 394, 4.7))

    a(f'<text class="mono" font-size="12" font-style="italic" clip-path="url(#a4)">'
      f'<tspan x="66" y="452" fill="{c["accent"]}">{MOTTO}</tspan></text>')
    a(f'<text class="mono" font-size="11.5" clip-path="url(#a5)">'
      f'<tspan x="66" y="482" fill="{c["muted"]}">{esc(LINKS)}</tspan></text>')

    # ---------- ASCII portrait (right column: the "generated" image) ----------
    cw = PFS * 0.6
    pcx = PX0 + COLS * cw / 2
    a(f'<text x="{pcx:.0f}" y="272" text-anchor="middle" class="mono" font-size="9" '
      f'letter-spacing="2" fill="{c["muted"]}">&#9707; rendering subject&#8230;</text>')
    a(f'<g class="mono" font-size="{PFS}">')
    for r, row in enumerate(PORTRAIT):
        runs = row_runs(row)
        if not runs:
            continue
        y = PY0 + r * PLH
        beg = 2.0 + r * 0.04
        tspans = "".join(
            f'<tspan x="{PX0 + col*cw:.1f}" textLength="{len(t)*cw:.1f}" '
            f'lengthAdjust="spacingAndGlyphs" fill="{pal[b]}">{esc(t)}</tspan>'
            for col, b, t in runs)
        a(f'<text y="{y:.1f}" opacity="0">{tspans}'
          f'<animate attributeName="opacity" from="0" to="1" begin="{beg:.2f}s" dur="0.35s" fill="freeze"/></text>')
    a('</g>')
    # scanline over the portrait
    a(f'<rect x="{PX0}" y="{PY0-6}" width="{COLS*cw:.0f}" height="2.5" rx="1" fill="{c["sub"]}" opacity="0.3">'
      f'<animate attributeName="y" values="{PY0-6};{PY0 + ROWS*PLH:.0f};{PY0-6}" dur="5s" begin="2s" repeatCount="indefinite"/>'
      f'<animate attributeName="opacity" values="0.3;0.1;0.3" dur="5s" begin="2s" repeatCount="indefinite"/></rect>')
    # tag under portrait
    a(f'<g opacity="0"><animate attributeName="opacity" from="0" to="1" begin="3.6s" dur="0.5s" fill="freeze"/>'
      f'<rect x="{pcx-62:.0f}" y="502" width="124" height="22" rx="11" fill="{c["chip"]}" '
      f'stroke="{c["flow"]}" stroke-opacity="0.5"/>'
      f'<circle cx="{pcx-46:.0f}" cy="513" r="3" fill="{c["ok"]}">'
      f'<animate attributeName="opacity" values="1;0.3;1" dur="1.4s" repeatCount="indefinite"/></circle>'
      f'<text x="{pcx+6:.0f}" y="517" text-anchor="middle" class="mono" font-size="10" '
      f'fill="{c["text"]}">pandiyan-net</text></g>')

    # blinking stream cursor
    a(f'<rect x="620" y="470" width="9" height="16" fill="{c["flow"]}">'
      f'<animate attributeName="opacity" values="1;1;0;0" dur="1s" repeatCount="indefinite"/></rect>')

    # ---------- telemetry ----------
    a(f'<text x="40" y="554" class="mono" font-size="11" fill="{c["muted"]}">'
      f'retrieved: <tspan fill="{c["sub"]}">top-k chunks</tspan>&#160;&#160;&#183;&#160;&#160;'
      f'latency: <tspan fill="{c["text"]}">42 ms</tspan>&#160;&#160;&#183;&#160;&#160;'
      f'throughput: <tspan fill="{c["text"]}">87 tok/s</tspan>&#160;&#160;&#183;&#160;&#160;'
      f'context: <tspan fill="{c["sub"]}">grounded &#10003;</tspan></text>')
    a(f'<text x="{W-40}" y="554" text-anchor="end" class="mono" font-size="11" fill="{c["muted"]}">github.com/S-PANDIYAN</text>')

    a('</svg>')
    return "\n".join(out)


for theme in ("dark", "light"):
    svg = build(theme)
    with open(f"{theme}.svg", "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {theme}.svg ({len(svg)} bytes)")
