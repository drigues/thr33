"""Converte as imagens-mestre de src/images/ em AVIF e WebP para public/assets/img/ (#34, #53).

Corre com: python3 scripts/images.py   (precisa de sips, cwebp e avifenc: brew install webp libavif)

- src/images/images.json: por imagem, as 3 larguras do srcset e o atributo sizes.
- src/images/<nome>.png ou .jpg: a imagem-mestre, com a largura maior do srcset.
- Gera public/assets/img/<nome>-<largura>.avif e .webp. O build.py lê as mesmas larguras
  e a proporção da mestre para escrever o <picture>, com width e height.

Para trocar uma imagem provisória pela final (#54): pôr a mestre com o mesmo nome e a mesma
proporção, correr este script e depois o build.py e o check_site.py.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SRC = BASE / "src" / "images"
OUT = BASE / "public" / "assets" / "img"


def master(name):
    for ext in (".png", ".jpg", ".jpeg"):
        f = SRC / f"{name}{ext}"
        if f.exists():
            return f
    raise SystemExit(f"imagem-mestre em falta: src/images/{name}.png")


def pixel_width(path):
    out = subprocess.run(["sips", "-g", "pixelWidth", str(path)], capture_output=True, text=True, check=True).stdout
    return int(out.split()[-1])


def main():
    config = json.loads((SRC / "images.json").read_text(encoding="utf-8"))
    for name, spec in config.items():
        src = master(name)
        widths = spec["widths"]
        if pixel_width(src) != max(widths):
            raise SystemExit(f"{src.name}: a mestre tem de ter {max(widths)} px de largura (a maior do srcset)")
        target = OUT / Path(name).parent
        target.mkdir(parents=True, exist_ok=True)
        stem = Path(name).name
        with tempfile.TemporaryDirectory() as tmp:
            for w in widths:
                png = Path(tmp) / f"{stem}-{w}.png"
                subprocess.run(["sips", "--resampleWidth", str(w), str(src), "--out", str(png)],
                               check=True, capture_output=True)
                subprocess.run(["cwebp", "-quiet", "-q", "80", "-metadata", "none", str(png),
                                "-o", str(target / f"{stem}-{w}.webp")], check=True)
                subprocess.run(["avifenc", "-q", "60", "-s", "6", "--ignore-exif", "--ignore-xmp", str(png),
                                str(target / f"{stem}-{w}.avif")], check=True, capture_output=True)
        print(f"{name}: {', '.join(map(str, widths))} px em AVIF e WebP")


if __name__ == "__main__":
    sys.exit(main())
