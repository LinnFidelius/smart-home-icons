#!/usr/bin/env python3
"""Erzeugt aus src (Symbole): PNGs (64/256 px), Varianten ohne Hintergrund (frei/), Cricut-SVGs (nur Flächen,
eine Ebene je Farbe), docs/uebersicht.png, sowie aus src/mono die Pfade für Home Assistant (smart-home-icons.js,
dist/mono-paths.json). Aus icons/src (Icons, vereinfachter Stil): PNGs mit und ohne Sockel, Cricut, docs/icons.png."""
import pathlib, re, sys, io, json
import cairosvg
from picosvg.svg import SVG
from PIL import Image, ImageDraw, ImageFont

R = pathlib.Path(__file__).resolve().parent.parent
SIZES = (64, 256)

def frei(svg, style):
    """Variante ohne Hintergrund: 2D ohne Sockel, 3D ohne Bodenplatte (und ohne Tafel, falls noch vorhanden)."""
    if style == '2d':
        return re.sub(r'<rect x="16" y="1(50|64)"[^>]*/>', '', svg, count=2)
    polys = re.findall(r'<polygon[^>]*/>', svg)
    for p in polys[:3]: svg = svg.replace(p, '', 1)
    rest = polys[3:6]
    if len(rest) == 3 and all(f'fill="{c}"' in p for p, c in zip(rest, ('#FFFFFF', '#C9CCD3', '#F7F7F7'))):
        for p in rest: svg = svg.replace(p, '', 1)
    return svg

def png(src, out, size):
    out.parent.mkdir(parents=True, exist_ok=True)
    cairosvg.svg2png(url=str(src), write_to=str(out), output_width=size, output_height=size)

def cricut(src, out):
    # Konturen in Flächen umwandeln, Transformationen auflösen, Pfade nach Farbe gruppieren
    pico = SVG.parse(str(src)).topicosvg(allow_text=False)
    paths = re.findall(r'<path[^>]*/>', pico.tostring())
    groups, last = {}, {}
    for i, p in enumerate(paths):
        m = re.search(r'fill="(#[0-9A-Fa-f]{3,6})"', p)
        col = (m.group(1) if m else '#000000').upper()
        p = re.sub(r'\s(fill-opacity|opacity)="[^"]*"', '', p)
        groups.setdefault(col, []).append(p); last[col] = i
    # Ebenen nach dem letzten Vorkommen ordnen, damit obenliegende Details (z. B. Leisten auf weißen Flächen) oben bleiben
    body = ''.join(f'<g id="ebene-{c[1:]}" fill="{c}">' + ''.join(groups[c]) + '</g>' for c in sorted(groups, key=last.get))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="100mm" height="100mm">{body}</svg>')

def sheet(names, out, styles=('3d', '2d'), base=None, mono=True):
    base = base or (R / 'src')
    cell, cols = 150, 8
    rows = (len(names) + cols - 1) // cols
    img = Image.new('RGB', (cols * cell, rows * (cell * 2 + 84)), '#1c1c1c')
    d = ImageDraw.Draw(img)
    try: font = ImageFont.truetype('DejaVuSans.ttf', 13)
    except OSError: font = ImageFont.load_default()
    for i, n in enumerate(names):
        x, y = (i % cols) * cell, (i // cols) * (cell * 2 + 84)
        for j, style in enumerate(styles):
            f = base / style / f'{n}.svg'
            if f.exists():
                im = Image.open(io.BytesIO(cairosvg.svg2png(url=str(f), output_width=cell - 20, output_height=cell - 20))).convert('RGBA')
                img.paste(im, (x + 10, y + 10 + j * cell), im)
        f = R / 'src' / 'mono' / f'{n}.svg'
        if mono and f.exists():
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
    s = re.sub(r'<(path|rect|circle)(?![^>]*fill=)', r'<\1 fill="none"', s)
    return ' '.join(re.findall(r' d="([^"]+)"', SVG.fromstring(s).topicosvg().tostring()))

names = sorted({p.stem for p in (R / 'src').glob('*/*.svg')})
for style in ('3d', '2d'):
    for f in sorted((R / 'src' / style).glob('*.svg')):
        for s in SIZES: png(f, R / 'png' / style / str(s) / f'{f.stem}.png', s)
        fr = R / 'frei' / style / f'{f.stem}.svg'; fr.parent.mkdir(parents=True, exist_ok=True)
        fr.write_text(frei(f.read_text(), style))
        for s in SIZES: png(fr, R / 'png' / f'{style}-frei' / str(s) / f'{f.stem}.png', s)
# Icons (vereinfachter Stil): 2D mit Sockel, ohne Sockel, Cricut, App-Icon-Quelle 1024 px auf Weiß
I = R / 'icons'
for f in sorted((I / 'src').glob('*.svg')):
    fr = I / 'frei' / f'{f.stem}.svg'; fr.parent.mkdir(parents=True, exist_ok=True)
    fr.write_text(frei(f.read_text(), '2d'))
    for s in SIZES:
        png(f, I / 'png' / '2d' / str(s) / f'{f.stem}.png', s)
        png(fr, I / 'png' / '2d-frei' / str(s) / f'{f.stem}.png', s)
    weiss = f.read_text().replace('viewBox="0 0 200 200">', 'viewBox="0 0 200 200"><rect width="200" height="200" fill="#FFFFFF"/>', 1)
    out = I / 'png' / 'app' / f'{f.stem}-1024.png'; out.parent.mkdir(parents=True, exist_ok=True)
    cairosvg.svg2png(bytestring=weiss.encode(), write_to=str(out), output_width=1024, output_height=1024)
    cricut(f, I / 'cricut' / f'{f.stem}.svg')
for f in sorted((R / 'src' / '2d').glob('*.svg')):
    cricut(f, R / 'cricut' / f'{f.stem}.svg')
sheet(names, R / 'docs' / 'uebersicht.png')
sheet(sorted(p.stem for p in (I / 'src').glob('*.svg')), R / 'docs' / 'icons.png', styles=('src', 'frei'), base=I, mono=False)
mono = {f.stem: mono_path(f) for f in sorted((R / 'src' / 'mono').glob('*.svg'))}
(R / 'dist').mkdir(exist_ok=True)
(R / 'dist' / 'mono-paths.json').write_text(json.dumps(mono, separators=(',', ':')))
for f in sorted((R / 'src' / 'mono').glob('*.svg')):
    for s_ in SIZES:
        out = R / 'png' / 'mono' / str(s_) / f'{f.stem}.png'; out.parent.mkdir(parents=True, exist_ok=True)
        cairosvg.svg2png(bytestring=f.read_text().replace('currentColor', '#000000').encode(), write_to=str(out), output_width=s_, output_height=s_)
VERSION = (R / 'VERSION').read_text().strip()
js = ('// Smart-Home-Icons für Home Assistant – automatisch erzeugt von tools/build.py\n'
      f'const SHI_VERSION = \'{VERSION}\';\n'
      '// Verwendung in jedem Symbolfeld: shi:<name>, z. B. shi:waermepumpe\n'
      'const SHI_ICONS = ' + json.dumps(mono, separators=(',', ':')) + ';\n'
      'window.customIcons = window.customIcons || {};\n'
      'window.customIcons.shi = {\n'
      '  getIcon: async (name) => ({ path: SHI_ICONS[name] || \'\' }),\n'
      '  getIconList: async () => Object.keys(SHI_ICONS).map((name) => ({ name })),\n'
      '};\n'
      'console.info(\'%c SMART-HOME-ICONS %c \' + SHI_VERSION + \' · \' + Object.keys(SHI_ICONS).length + \' Symbole (shi:) \', \'background:#5B9BD5;color:#000;font-weight:bold\', \'background:#C6E0B4;color:#000\');\n')
(R / 'smart-home-icons.js').write_text(js)
print(len(names), 'Symbole gebaut')
