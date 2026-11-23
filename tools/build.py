#!/usr/bin/env python3
"""Erzeugt aus src/3d und src/2d: PNGs (64/256 px), Cricut-SVGs (nur Flächen, eine Ebene je Farbe) und docs/uebersicht.png."""
import pathlib, re, sys, io
import cairosvg
from picosvg.svg import SVG
from PIL import Image, ImageDraw, ImageFont

R = pathlib.Path(__file__).resolve().parent.parent
SIZES = (64, 256)

def png(src, out, size):
    out.parent.mkdir(parents=True, exist_ok=True)
    cairosvg.svg2png(url=str(src), write_to=str(out), output_width=size, output_height=size)

def cricut(src, out):
    # Konturen in Flächen umwandeln, Transformationen auflösen, Pfade nach Farbe gruppieren
    pico = SVG.parse(str(src)).topicosvg(allow_text=False)
    paths = re.findall(r'<path[^>]*/>', pico.tostring())
    groups = {}
    for p in paths:
        m = re.search(r'fill="(#[0-9A-Fa-f]{3,6})"', p)
        col = (m.group(1) if m else '#000000').upper()
        p = re.sub(r'\s(fill-opacity|opacity)="[^"]*"', '', p)
        groups.setdefault(col, []).append(p)
    body = ''.join(f'<g id="ebene-{c[1:]}" fill="{c}">' + ''.join(groups[c]) + '</g>' for c in groups)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="100mm" height="100mm">{body}</svg>')

def sheet(names, out):
    cell, cols = 150, 8
    rows = (len(names) + cols - 1) // cols
    img = Image.new('RGB', (cols * cell, rows * (cell * 2 + 24)), '#1c1c1c')
    d = ImageDraw.Draw(img)
    try: font = ImageFont.truetype('DejaVuSans.ttf', 13)
    except OSError: font = ImageFont.load_default()
    for i, n in enumerate(names):
        x, y = (i % cols) * cell, (i // cols) * (cell * 2 + 24)
        for j, style in enumerate(('3d', '2d')):
            f = R / 'src' / style / f'{n}.svg'
            if f.exists():
                im = Image.open(io.BytesIO(cairosvg.svg2png(url=str(f), output_width=cell - 20, output_height=cell - 20))).convert('RGBA')
                img.paste(im, (x + 10, y + 10 + j * cell), im)
        w = d.textlength(n, font=font)
        d.text((x + (cell - w) / 2, y + cell * 2 + 2), n, fill='#bbbbbb', font=font)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)

names = sorted({p.stem for p in (R / 'src').glob('*/*.svg')})
for style in ('3d', '2d'):
    for f in sorted((R / 'src' / style).glob('*.svg')):
        for s in SIZES: png(f, R / 'png' / style / str(s) / f'{f.stem}.png', s)
for f in sorted((R / 'src' / '2d').glob('*.svg')):
    cricut(f, R / 'cricut' / f'{f.stem}.svg')
sheet(names, R / 'docs' / 'uebersicht.png')
print(len(names), 'Symbole gebaut')
