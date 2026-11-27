"""Converte as imagens-mestre de src/images/ em AVIF e WebP para public/assets/img/ (#34, #53).

Corre com: python3 scripts/images.py   (precisa de sips, cwebp e avifenc: brew install webp libavif)

- src/images/images.json: por imagem, as 3 larguras do srcset e o atributo sizes.
- src/images/<nome>.png ou .jpg: a imagem-mestre, com a largura maior do srcset.
- Gera public/assets/img/<nome>-<largura>.avif e .webp. O build.py lê as mesmas larguras
  e a proporção da mestre para escrever o <picture>, com width e height.

Pixel art (as ilustrações do scripts/art.py, com "pixel_art": true no images.json): cada largura é desenhada
do SVG com o scripts/raster.swift, sem reamostrar a mestre, e tem de ser um múltiplo inteiro da grelha de
píxeis: a largura do SVG ou, se o desenho usa meios píxeis, o "pixel_grid" (o cartaz-ar desenha o cartaz a
0,5, por isso a grelha é 240 e só cabem 240 e 480 px: a pixel art pode ter 2 larguras em vez de 3).
Reamostrar desfoca os píxeis e as versões pequenas acabavam a pesar mais do que as grandes. Vai só em WebP
sem perdas: poucas cores em blocos ficam com 1 KB ou menos e exatas, e o AVIF sai mais pesado.

Para trocar uma imagem provisória pela final (#54): pôr a mestre com o mesmo nome e a mesma
proporção, tirar o "pixel_art" do images.json e mover o SVG para _PODE-DELETAR/, correr este script
e depois o build.py e o check_site.py.
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SRC = BASE / "src" / "images"
OUT = BASE / "public" / "assets" / "img"
IMAGES_GRID = {}  # "pixel_grid" do images.json, por imagem


def master(name):
    for ext in (".png", ".jpg", ".jpeg"):
        f = SRC / f"{name}{ext}"
        if f.exists():
            return f
    raise SystemExit(f"imagem-mestre em falta: src/images/{name}.png")


def pixel_width(path):
    out = subprocess.run(["sips", "-g", "pixelWidth", str(path)], capture_output=True, text=True, check=True).stdout
    return int(out.split()[-1])


def pixel_art_pngs(name, widths, tmp):
    """Desenha o SVG da pixel art em cada largura (múltiplo inteiro), com o raster.swift. Devolve {largura: png}."""
    svg = SRC / f"{name}.svg"
    vw, vh = (float(v) for v in re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg.read_text(encoding="utf-8")).groups())
    grid = IMAGES_GRID.get(name) or vw
    jobs, pngs = [], {}
    for w in widths:
        if not (w / grid).is_integer():
            raise SystemExit(f"{name}: {w} px não é múltiplo inteiro de {grid:g} px (a grelha de píxeis)")
        pngs[w] = Path(tmp) / f"{Path(name).name}-{w}.png"
        jobs += [str(svg), str(pngs[w]), str(w), str(round(w * vh / vw))]
    subprocess.run(["swift", str(BASE / "scripts" / "raster.swift"), *jobs], check=True, capture_output=True)
    return pngs


def main():
    config = json.loads((SRC / "images.json").read_text(encoding="utf-8"))
    IMAGES_GRID.update({n: s["pixel_grid"] for n, s in config.items() if "pixel_grid" in s})
    for name, spec in config.items():
        src = master(name)
        widths = spec["widths"]
        if pixel_width(src) != max(widths):
            raise SystemExit(f"{src.name}: a mestre tem de ter {max(widths)} px de largura (a maior do srcset)")
        target = OUT / Path(name).parent
        target.mkdir(parents=True, exist_ok=True)
        stem = Path(name).name
        with tempfile.TemporaryDirectory() as tmp:
            pngs = pixel_art_pngs(name, widths, tmp) if spec.get("pixel_art") else {}
            for w in widths:
                png = pngs.get(w) or Path(tmp) / f"{stem}-{w}.png"
                if w not in pngs:
                    subprocess.run(["sips", "--resampleWidth", str(w), str(src), "--out", str(png)],
                                   check=True, capture_output=True)
                if w in pngs:
                    subprocess.run(["cwebp", "-quiet", "-lossless", "-z", "9", "-metadata", "none", str(png),
                                    "-o", str(target / f"{stem}-{w}.webp")], check=True)
                    continue
                subprocess.run(["cwebp", "-quiet", "-q", "80", "-metadata", "none", str(png),
                                "-o", str(target / f"{stem}-{w}.webp")], check=True)
                subprocess.run(["avifenc", "-q", "60", "-s", "6", "--ignore-exif", "--ignore-xmp", str(png),
                                str(target / f"{stem}-{w}.avif")], check=True, capture_output=True)
        kind = "WebP sem perdas (pixel art)" if spec.get("pixel_art") else "AVIF e WebP"
        print(f"{name}: {', '.join(map(str, widths))} px em {kind}")


if __name__ == "__main__":
    sys.exit(main())
