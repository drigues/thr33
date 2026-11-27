"""Ilustrações dos projetos (#59), feitas com os assets dos próprios projetos.

Corre com: python3 scripts/art.py   e depois  python3 scripts/images.py  e  python3 scripts/build.py

Fontes em src/art/ (descarregadas e otimizadas uma vez, servidas pelo site, sem pedidos externos):
- vizia/sala.svg, vizia/icon.svg: a sala com o sofá em realidade aumentada e o ícone, de vizia.thr33.xyz.
- get-it-vac/logo.svg: o logótipo em pixel, de vac.navego.pt.
- get-it-vac/sprites.json: os sprites do jogo (navegadores no Vac, Madame, Bit, obstáculos, casario de Lisboa).
- get-it-vac/cartaz.json: o cartaz do jogo, célula a célula (160 × 144), nas 10 cores da paleta.

Gera:
- src/art/cartoes/<projeto>.svg: a ilustração dos cartões de projeto (Início e Projetos), que o build.py põe inline
  no cartão. As peças vão em grupos (<g class="art-...">) para o site.css as animar (#63): recortadas das fontes,
  sem arte nova.
- src/images/get-it-vac/<nome>.svg e .png: as imagens da página Get It Vac. O PNG é a imagem-mestre que o
  images.py converte em AVIF e WebP; a proporção é a do #53, para o #54 trocar pelas fotografias finais.
"""
import json
import random
import re
import subprocess
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
ART = BASE / "src" / "art"
CARDS = ART / "cartoes"
IMAGES = BASE / "src" / "images" / "get-it-vac"

SPRITES = json.loads((ART / "get-it-vac" / "sprites.json").read_text(encoding="utf-8"))
P = SPRITES["palette"]
KEY = {"n": P["night"], "b": P["tile"], "s": P["sand"], "y": P["yellow"], "c": P["cyan"], "t": P["terracotta"],
       "a": P["caramel"], "k": P["ink"], "m": P["madame"], "u": P["mustard"]}
CARTAZ = json.loads((ART / "get-it-vac" / "cartaz.json").read_text(encoding="utf-8"))
CARTAZ_TEXT = range(26, 41)  # linhas da legenda pequena do cartaz: ilegíveis em células de 7 px, ficam em Noite


def num(v):
    return ("%.2f" % v).rstrip("0").rstrip(".")


class Pixels:
    """Retângulos por cor, juntos num <path> por cor e por camada (como o logótipo do jogo). Cada sprite e cada
    grelha vai numa camada nova, por cima das anteriores. Cores em dithering (duas cores em xadrez, como o
    casario) usam um <pattern> de 2 × 2."""

    def __init__(self):
        self.layers = [{}]
        self.patterns = {}

    def layer(self):
        if self.layers[-1]:
            self.layers.append({})

    def rect(self, x, y, w, h, color):
        if isinstance(color, (list, tuple)):
            pid = "d" + "".join(c.lstrip("#") for c in color).lower()
            self.patterns[pid] = color
            color = f"url(#{pid})"
        self.layers[-1].setdefault(color, []).append(f"M{num(x)} {num(y)}h{num(w)}v{num(h)}h-{num(w)}z")

    def sprite(self, frame, x, y, scale=1, colors=None):
        self.layer()
        for rx, ry, rw, rh, c in frame["rects"]:
            self.rect(x + rx * scale, y + ry * scale, rw * scale, rh * scale, (colors or {}).get(c, c))

    def grid(self, rows, x, y, scale=1, skip=()):
        self.layer()
        for j, row in enumerate(rows):
            i = 0
            while i < len(row):
                end = i + 1
                while end < len(row) and row[end] == row[i]:
                    end += 1
                if row[i] != "." and j not in skip:
                    self.rect(x + i * scale, y + j * scale, (end - i) * scale, scale, KEY[row[i]])
                i = end

    def defs(self):
        defs = "".join(f'<pattern id="{pid}" width="2" height="2" patternUnits="userSpaceOnUse">'
                       f'<rect width="2" height="2" fill="{a}"/><path fill="{b}" d="M1 0h1v1h-1zM0 1h1v1h-1z"/></pattern>'
                       for pid, (a, b) in self.patterns.items())
        return f"<defs>{defs}</defs>" if defs else ""

    def body(self):
        return "".join(f'<path fill="{c}" d="{"".join(d)}"/>' for layer in self.layers for c, d in layer.items())

    def svg(self):
        return self.defs() + self.body()


class Sprites:
    """Uma ilustração feita de peças (#63): cada peça é um <g class="art-..."> com os seus píxeis, para o
    site.css a animar sozinha. Os padrões de dithering são partilhados por todas as peças."""

    def __init__(self):
        self.patterns = {}
        self.parts = []

    def piece(self, cls):
        px = Pixels()
        px.patterns = self.patterns
        self.parts.append((cls, px))
        return px

    def svg(self):
        return Pixels.defs(self) + "".join(f'<g class="{cls}">{px.body()}</g>' for cls, px in self.parts)


def svg(width, height, body, crisp=True):
    mode = ' shape-rendering="crispEdges"' if crisp else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" '
            f'height="{height}"{mode}>{body}</svg>\n')


def inner(path):
    s = (ART / path).read_text(encoding="utf-8")
    view = [float(v) for v in re.search(r'viewBox="([^"]+)"', s).group(1).split()]
    return view, re.search(r"<svg[^>]*>(.*)</svg>", s, re.S).group(1)


def place(path, x, y, width):
    """Um SVG de src/art/ dentro de outro, com a largura pedida e a proporção dele."""
    (vx, vy, vw, vh), body = inner(path)
    k = width / vw
    return f'<g transform="translate({num(x)} {num(y)}) scale({num(k)}) translate({num(-vx)} {num(-vy)})">{body}</g>'


def city_tile(px, x, ground, chapter):
    city = SPRITES["city"]
    colors = SPRITES["cityColors"][chapter]
    for rx, ry, rw, rh, role in city["rects"]:
        px.rect(x + rx, ground - city["height"] + ry, rw, rh, colors[role])


def stars(px, width, height, count, seed):
    rnd = random.Random(seed)
    for _ in range(count):
        x, y = rnd.randrange(1, width - 1), rnd.randrange(1, height - 1)
        color = rnd.choice([P["sand"], P["sand"], P["yellow"], P["cyan"]])
        if rnd.random() < 0.2:  # estrela em cruz, como no cartaz
            px.rect(x - 1, y, 3, 1, color)
            px.rect(x, y - 1, 1, 3, color)
        else:
            px.rect(x, y, 1, 1, color)


def vac_only(frame):
    """Só o Vac (as 5 linhas de baixo e o contorno), sem o navegador."""
    top = frame["height"] - 7
    return {"width": frame["width"], "height": 7,
            "rects": [[x, y - top, w, h, c] for x, y, w, h, c in frame["rects"] if y >= top]}


NAV = SPRITES["navigators"]


# ---------------------------------------------------------------- cartões de projeto (16:10)

def sala_pieces():
    """A sala do Vizia (src/art/vizia/sala.svg) recortada nas peças que a compõem, pela ordem do ficheiro:
    sala (paredes, chão, janela e luz), e dentro do grupo com traço: sofá (6 caixas), candeeiro (pé e
    abajur) e planta (vaso e folhas)."""
    (vx, vy, vw, vh), body = inner("vizia/sala.svg")
    stroke = re.search(r"<g ([^>]*)>(.*)</g>", body, re.S)
    room, objects = body[:stroke.start()], re.findall(r"<polygon [^>]*/>", stroke.group(2))
    if len(objects) != 30:
        raise SystemExit(f"src/art/vizia/sala.svg mudou: esperava 30 polígonos no grupo dos objetos, tem {len(objects)}")
    attrs = stroke.group(1)
    return room, attrs, {"sofa": objects[:18], "candeeiro": objects[18:24], "planta": objects[24:30]}


def sofa_shadow(sofa):
    """A sombra do sofá no chão: a pegada da base (os vértices de baixo das caixas), um pouco maior."""
    pts = [tuple(map(float, xy.split(","))) for poly in sofa for xy in re.search(r'points="([^"]+)"', poly).group(1).split()]
    left = min(pts, key=lambda p: p[0])
    right = max(pts, key=lambda p: p[0])
    bottom = max(pts, key=lambda p: p[1])
    back = (left[0] + right[0] - bottom[0], left[1] + right[1] - bottom[1])  # 4.º canto do paralelogramo
    cx, cy = (left[0] + right[0]) / 2, (left[1] + right[1]) / 2
    grow = [(cx + (x - cx) * 1.08, cy + (y - cy) * 1.08 + 2) for x, y in (left, bottom, right, back)]
    points = " ".join(f"{num(x)},{num(y)}" for x, y in grow)
    return f'<polygon points="{points}" fill="#785834" fill-opacity="0.28"/>'


def card_vizia():
    """A sala do Vizia com o sofá em AR, enquadrada a 16:10, com o ícone e cantos de visor em azul Vizia.
    Peças: sala, sombra, sofá, candeeiro, planta, cantos (um <g> cada) e ícone."""
    w, h = 320, 200
    room, attrs, objects = sala_pieces()
    move = 'transform="translate(-14 -146)"'
    parts = [("art-sala", f"<g {move}>{room}</g>"),
             ("art-sombra", f"<g {move}>{sofa_shadow(objects['sofa'])}</g>")]
    for name in ("planta", "candeeiro", "sofa"):
        parts.append((f"art-{name}", f'<g {move} {attrs}>{"".join(objects[name])}</g>'))
    corner = 18
    marks = "".join(
        f'<path d="M{x} {y + dy * corner}V{y}H{x + dx * corner}"/>'
        for x, y, dx, dy in ((14, 14, 1, 1), (w - 14, 14, -1, 1), (14, h - 14, 1, -1), (w - 14, h - 14, -1, -1)))
    parts.append(("art-cantos", f'<g fill="none" stroke="#2563EB" stroke-width="3" stroke-linecap="round">{marks}</g>'))
    parts.append(("art-icone", place("vizia/icon.svg", 26, h - 54, 28)))
    return svg(w, h, "".join(f'<g class="{cls}">{body}</g>' for cls, body in parts), crisp=False)


def card_get_it_vac():
    """O Get It Vac em sprites do jogo (16:10, 160 × 100): a noite, o casario de Alfama e o chão do cartaz, o
    logótipo de vac.navego.pt, o Zé e a Inês nos robôs, o Bit e a Madame, e 3 estrelas em cruz que piscam."""
    w, h, floor = 160, 100, 80
    art = Sprites()
    sky = art.piece("art-casario")
    sky.rect(0, 0, w, h, P["night"])
    city_tile(sky, 0, floor, "alfama")
    ground(sky, floor, w)
    stars(art.piece("art-estrelas"), w, 44, 30, seed=7)
    for x, y, color in ((9, 27, P["sand"]), (148, 30, P["yellow"]), (100, 24, P["cyan"])):
        twinkle = art.piece("art-estrela")
        twinkle.rect(x - 1, y, 3, 1, color)
        twinkle.rect(x, y - 1, 1, 3, color)
    art.piece("art-personagem").sprite(SPRITES["bit"][1], 8, floor - 12)
    art.piece("art-vac").sprite(NAV["ze"][1], 28, floor - 33)
    art.piece("art-vac").sprite(NAV["ines"][0], 66, floor - 33)
    art.piece("art-madame").sprite(SPRITES["madame"][0], 122, floor - 36)
    logo = place("get-it-vac/logo.svg", 16, 7, 128)
    return svg(w, h, art.svg() + f'<g class="art-logo">{logo}</g>')


# ---------------------------------------------------------------- imagens da página Get It Vac

def ground(px, y, width):
    """Chão às cores dos 4 bairros, tirado do cartaz (linha Tinta e blocos com pedras)."""
    rows = CARTAZ["rows"][120:144]
    for x in range(0, width, 160):
        px.grid([r[: width - x] for r in rows], x, y)


def hero():
    """Ecrã do jogo (16:9): o Zé no Vac a correr pelo casario de Alfama e da Baixa, atrás da Madame."""
    w, h, floor = 208, 117, 94
    px = Pixels()
    px.rect(0, 0, w, h, P["night"])
    stars(px, w, 40, 46, seed=5)
    city_tile(px, 0, floor, "alfama")
    city_tile(px, 160, floor, "baixa")
    ground(px, floor, w)
    px.sprite(SPRITES["bit"][1], 20, floor - 12)
    px.sprite(NAV["ze"][1], 40, floor - 33)
    px.sprite({"rects": SPRITES["obstacles"]["barrel"]}, 104, floor - 18)
    px.sprite(SPRITES["madame"][0], 160, floor - 36)
    return w, h, px.svg() + place("get-it-vac/logo.svg", 8, 7, 96)


def comando():
    """O comando (4:3): o Vac aberto, com a placa do microcontrolador, o joystick e o cabo."""
    w, h = 124, 93
    px = Pixels()
    px.rect(0, 0, w, h, P["night"])
    stars(px, w, 30, 18, seed=9)
    px.rect(0, 70, w, 23, (P["tile"], P["night"]))
    px.sprite(vac_only(NAV["capitao"][0]), 14, 52, scale=3)  # o Vac, 3 vezes maior
    # Placa: Tinta, com pinos areia, chip ciano e LED amarelo
    px.layer()
    px.rect(28, 30, 30, 18, P["ink"])
    px.layer()
    for i in range(6):
        px.rect(31 + i * 4, 28, 2, 2, P["sand"])
        px.rect(31 + i * 4, 48, 2, 2, P["sand"])
    px.rect(36, 35, 12, 8, P["cyan"])
    px.rect(52, 33, 3, 3, P["yellow"])
    # Cabo ciano da placa ao joystick
    px.rect(58, 39, 22, 2, P["cyan"])
    px.rect(78, 39, 2, 16, P["cyan"])
    # Joystick: base Tinta, haste areia, bola terracota
    px.layer()
    px.rect(84, 56, 26, 10, P["ink"])
    px.layer()
    px.rect(86, 58, 22, 6, P["mustard"])
    px.rect(95, 38, 4, 18, P["sand"])
    px.rect(91, 30, 12, 10, P["terracotta"])
    px.rect(93, 31, 4, 3, P["sand"])
    return w, h, px.svg()


def qr(px, x, y, size, seed):
    """Um código em blocos ao estilo QR (só ilustração: três quadrados de canto e módulos ao acaso)."""
    rnd = random.Random(seed)
    px.layer()
    px.rect(x - 2, y - 2, size + 4, size + 4, P["sand"])
    px.layer()
    for j in range(size):
        for i in range(size):
            corner = (i < 7 and j < 7) or (i >= size - 7 and j < 7) or (i < 7 and j >= size - 7)
            if not corner and rnd.random() < 0.45:
                px.rect(x + i, y + j, 1, 1, P["ink"])
    for cx, cy in ((x, y), (x + size - 7, y), (x, y + size - 7)):
        px.layer()
        px.rect(cx, cy, 7, 7, P["ink"])
        px.layer()
        px.rect(cx + 1, cy + 1, 5, 5, P["sand"])
        px.layer()
        px.rect(cx + 2, cy + 2, 3, 3, P["ink"])


def multijogador():
    """Multijogador (4:3): três telemóveis, um navegador em cada, ao lado do código de entrada."""
    w, h = 124, 93
    px = Pixels()
    px.rect(0, 0, w, h, (P["tile"], P["night"]))
    for n, who in enumerate(("ze", "ines", "capitao")):
        x, y = 4 + n * 28, 18 + (n % 2) * 6
        px.layer()
        px.rect(x, y, 26, 50, P["ink"])
        px.layer()
        px.rect(x + 2, y + 4, 22, 40, P["night"])
        px.rect(x + 10, y + 46, 6, 2, P["sand"])
        px.rect(x + 2, y + 36, 22, 8, (P["sand"], P["night"]))
        px.sprite(NAV[who][n % 2], x - 2, y + 6)
    qr(px, 93, 32, 25, seed=3)
    return w, h, px.svg()


AZULEJO = [  # um azulejo de 10 × 10, azul sobre areia
    "bbbbbbbbbb",
    "bssssssssb",
    "bsbsssbsbs",
    "bssbbbbssb",
    "bssbsbbssb",
    "bssbbsbssb",
    "bssbbbbssb",
    "bsbsssbsbs",
    "bssssssssb",
    "bbbbbbbbbb",
]


def selfie():
    """Selfie (4:5): a Inês, com a moldura de azulejo azul e branco da versão para telemóvel."""
    w, h = 120, 150
    px = Pixels()
    px.rect(0, 0, w, h, P["night"])
    stars(px, w, 70, 22, seed=11)
    px.rect(0, 112, w, 38, (P["sand"], P["night"]))
    px.sprite(NAV["ines"][0], 21, 41, scale=3)
    for x in range(0, w, 10):
        for y in range(0, h, 10):
            if x < 10 or x >= w - 10 or y < 10 or y >= h - 10:
                px.grid(AZULEJO, x, y)
    return w, h, px.svg()


def cartaz_ar():
    """Cartaz com AR (4:5): o telemóvel apontado ao cartaz e o Capitão no Vac em realidade aumentada por cima."""
    w, h = 120, 150
    px = Pixels()
    px.rect(0, 0, w, h, (P["madame"], P["night"]))
    px.layer()
    px.rect(12, 8, 96, 136, P["ink"])                     # telemóvel
    px.layer()
    px.rect(16, 18, 88, 116, P["night"])                  # ecrã
    px.rect(54, 12, 12, 2, P["sand"])
    px.grid(CARTAZ["rows"], 20, 62, scale=0.5, skip=CARTAZ_TEXT)  # o cartaz no ecrã
    px.layer()
    px.rect(20, 62, 80, 1, P["cyan"])
    px.rect(20, 133, 80, 1, P["cyan"])
    px.rect(20, 62, 1, 72, P["cyan"])
    px.rect(99, 62, 1, 72, P["cyan"])
    px.rect(38, 54, 44, 3, (P["cyan"], P["night"]))       # sombra do modelo em AR
    px.sprite(NAV["capitao"][1], 34, 4, scale=2)
    return w, h, px.svg()


PAGE = {"hero": (hero, 10), "comando": (comando, 8), "multijogador": (multijogador, 8),
        "selfie": (selfie, 4), "cartaz-ar": (cartaz_ar, 4)}


def main():
    CARDS.mkdir(parents=True, exist_ok=True)
    (CARDS / "vizia.svg").write_text(card_vizia(), encoding="utf-8")  # o build.py põe-nos inline nos cartões
    (CARDS / "get-it-vac.svg").write_text(card_get_it_vac(), encoding="utf-8")
    jobs = []
    for name, (draw, scale) in PAGE.items():
        w, h, body = draw()
        src = IMAGES / f"{name}.svg"
        src.write_text(svg(w, h, body), encoding="utf-8")
        jobs += [str(src), str(IMAGES / f"{name}.png"), str(w * scale), str(h * scale)]
    subprocess.run(["swift", str(BASE / "scripts" / "raster.swift"), *jobs], check=True)
    for f in sorted(CARDS.glob("*.svg")) + sorted(IMAGES.glob("*.svg")):
        print(f"{f.relative_to(BASE)}: {f.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
