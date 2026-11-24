#!/usr/bin/env python3
"""Erzeugt aus src: PNGs (64/256 px), Cricut-SVGs (nur Flächen, eine Ebene je Farbe), docs/uebersicht.png,
sowie aus src/mono die Pfade für Home Assistant (smart-home-icons.js, dist/mono-paths.json)."""
import pathlib, re, sys, io, json
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
    img = Image.new('RGB', (cols * cell, rows * (cell * 2 + 84)), '#1c1c1c')
    d = ImageDraw.Draw(img)
    try: font = ImageFont.truetype('DejaVuSans.ttf', 13)
    except OSError: font = ImageFont.load_default()
    for i, n in enumerate(names):
        x, y = (i % cols) * cell, (i // cols) * (cell * 2 + 84)
        for j, style in enumerate(('3d', '2d')):
            f = R / 'src' / style / f'{n}.svg'
            if f.exists():
                im = Image.open(io.BytesIO(cairosvg.svg2png(url=str(f), output_width=cell - 20, output_height=cell - 20))).convert('RGBA')
                img.paste(im, (x + 10, y + 10 + j * cell), im)
        f = R / 'src' / 'mono' / f'{n}.svg'
        if f.exists():
            im = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=f.read_text().replace('currentColor', '#E1E1E1').encode(), output_width=48, output_height=48))).convert('RGBA')
            img.paste(im, (x + (cell - 48) // 2, y + cell * 2 + 6), im)
        w = d.textlength(n, font=font)
        d.text((x + (cell - w) / 2, y + cell * 2 + 62), n, fill='#bbbbbb', font=font)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)

def mono_path(src):
    # Linien in Flächen umwandeln und zu einem Pfad zusammenfassen (Format der HA-Icons)
    s = src.read_text().replace('currentColor', '#000000')
    s = re.sub(r'(<svg[^>]*?) (fill="none" stroke=[^>]*)>', r'\1><g \2>', s).replace('</svg>', '</g></svg>')
    return ' '.join(re.findall(r' d="([^"]+)"', SVG.fromstring(s).topicosvg().tostring()))

names = sorted({p.stem for p in (R / 'src').glob('*/*.svg')})
for style in ('3d', '2d'):
    for f in sorted((R / 'src' / style).glob('*.svg')):
        for s in SIZES: png(f, R / 'png' / style / str(s) / f'{f.stem}.png', s)
for f in sorted((R / 'src' / '2d').glob('*.svg')):
    cricut(f, R / 'cricut' / f'{f.stem}.svg')
sheet(names, R / 'docs' / 'uebersicht.png')
mono = {f.stem: mono_path(f) for f in sorted((R / 'src' / 'mono').glob('*.svg'))}
(R / 'dist').mkdir(exist_ok=True)
(R / 'dist' / 'mono-paths.json').write_text(json.dumps(mono, separators=(',', ':')))
for f in sorted((R / 'src' / 'mono').glob('*.svg')):
    for s_ in SIZES:
        out = R / 'png' / 'mono' / str(s_) / f'{f.stem}.png'; out.parent.mkdir(parents=True, exist_ok=True)
        cairosvg.svg2png(bytestring=f.read_text().replace('currentColor', '#000000').encode(), write_to=str(out), output_width=s_, output_height=s_)
js = ('// Smart-Home-Icons für Home Assistant – automatisch erzeugt von tools/build.py\n'
      '// Verwendung in jedem Symbolfeld: shi:<name>, z. B. shi:waermepumpe\n'
      'const SHI_ICONS = ' + json.dumps(mono, separators=(',', ':')) + ';\n'
      'window.customIcons = window.customIcons || {};\n'
      'window.customIcons.shi = {\n'
      '  getIcon: async (name) => ({ path: SHI_ICONS[name] || \'\' }),\n'
      '  getIconList: async () => Object.keys(SHI_ICONS).map((name) => ({ name })),\n'
      '};\n'
      'console.info(\'%c SMART-HOME-ICONS %c \' + Object.keys(SHI_ICONS).length + \' Symbole (shi:) \', \'background:#5B9BD5;color:#000;font-weight:bold\', \'background:#C6E0B4;color:#000\');\n')
(R / 'smart-home-icons.js').write_text(js)
print(len(names), 'Symbole gebaut')
