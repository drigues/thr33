"""Verificação do site estático em public/.

Corre com: python3 tests/check_site.py
Sai com código 1 se alguma regra falhar.
"""
import re
from datetime import date
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent / "public"
SITE = "https://thr33.xyz"

# Pares PT ↔ EN. Cada página tem de existir nas duas línguas e apontar para a outra.
PAGES = [
    ("/", "/en/"),
    ("/sobre/", "/en/about/"),
    ("/servicos/", "/en/services/"),
    ("/produtos/", "/en/products/"),
    ("/contacto/", "/en/contact/"),
    ("/privacidade/", "/en/privacy/"),
    ("/termos/", "/en/terms/"),
    ("/cookies/", "/en/cookies/"),
    ("/produtos/get-it-vac/", "/en/products/get-it-vac/"),
]

LEGAL_FOOTER = {
    "pt-PT": ["THR33XYZ LABS - TECNOLOGIA E CONSULTORIA, UNIPESSOAL LDA", "Sociedade unipessoal por quotas",
              "Beco da Serra, 2, Sobral da Lagoa, 2510-651 Óbidos", "Conservatória do Registo Comercial",
              "519573021", "Capital social 7.660,00 €"],
    "en": ["THR33XYZ LABS - TECNOLOGIA E CONSULTORIA, UNIPESSOAL LDA", "single-member private limited company",
           "Beco da Serra, 2, Sobral da Lagoa, 2510-651 Óbidos", "Commercial Registry",
           "519573021", "Share capital €7,660.00"],
}

# DL 74/2017: acesso ao Livro de Reclamações Eletrónico visível em todas as páginas.
COMPLAINTS_URL = "https://www.livroreclamacoes.pt/Inicio/"
COMPLAINTS_LABEL = {"pt-PT": "Livro de Reclamações", "en": "Complaints Book (Livro de Reclamações)"}

# Redesign (#24, #25): paleta aprovada e papéis que o site.css usa.
TOKENS_CSS = ROOT / "assets" / "css" / "tokens.css"
PALETTE = {
    "--cal": "#F3F0E8", "--tinta": "#121212", "--telha": "#E8552D", "--lagoa": "#2C7564",
    "--atlantico": "#3A3FD9", "--pedra": "#6B675F",
    "--atlantico-claro": "#7679E5", "--pedra-clara": "#89847A", "--lagoa-clara": "#36907B",
}
REQUIRED_TOKENS = [
    "--paper", "--ink", "--muted", "--link", "--focus", "--accent", "--on-accent", "--secondary", "--line", "--surface",
    "--font-sans", "--font-mono", "--text-hero", "--text-h2", "--text-body", "--leading-body", "--text-label",
    "--tracking-hero", "--tracking-label", "--dur-1", "--dur-2", "--dur-3", "--ease-ui", "--ease-reveal",
]
# Componentes (#26): conteúdos num ficheiro por língua, cabeçalho com menu e JS externo.
BASE = ROOT.parent
CONTENT = {"pt": BASE / "src" / "content" / "pt.json", "en": BASE / "src" / "content" / "en.json"}
SITE_JS = "/assets/js/site.js"
# Hero (#27): etiqueta, gradiente-assinatura decorativo e títulos com reveal por linhas.
# Reposicionamento (#52): o posicionamento vai na etiqueta, o h1 diz o que as pessoas fazem.
HERO_LABEL = {"pt-PT": "(Thr33 Labs / ©2026) Estúdio de tecnologia interativa · Óbidos, PT",
              "en": "(Thr33 Labs / ©2026) Interactive technology studio · Óbidos, PT"}
HERO_H1 = {"pt-PT": "Tecnologia que as pessoas tocam e usam", "en": "Technology people touch and use"}
HERO_BLOBS = 3
# Serviços e ícones (#29): sprite Lucide servido pelo site, um ícone por serviço e por passo.
ICONS_SVG = ROOT / "assets" / "icons.svg"
ICONS_LICENCE = ROOT / "assets" / "icons-LICENSE.txt"
HOME_LABELS = {"pt-PT": ["Serviços", "Projetos", "Processo", "Sobre"], "en": ["Services", "Projects", "Process", "About"]}
HOME_ICONS = {"service": 5, "step": 4}
SERVICES_PAGE_ICONS = 5
# Cores por secção (#31): Projetos veste Tinta e o CTA final veste Telha.
SCENES = {"/": ["ink", "telha"], "/servicos/": ["telha"], "/produtos/": ["ink"], "/produtos/get-it-vac/": ["telha"]}
# CTA final e rodapé (#32): "Vamos falar?" em tamanho de hero, email grande e rodapé em duas linhas.
CTA_TITLE = {"pt-PT": "Vamos falar?", "en": "Shall we talk?"}
EMAIL = "hello@thr33.xyz"
PHONE_HREF = "tel:+351936466845"
FOOTER_LINE1 = {"pt-PT": ["/privacidade/", "/termos/", "/cookies/"], "en": ["/en/privacy/", "/en/terms/", "/en/cookies/"]}
# Ficha (#33): fim da página Sobre, chave/valor em mono como créditos, com os dados do rodapé legal.
# (termo, excerto que tem de estar no valor e na linha legal do rodapé; None = só o termo)
FICHA = {
    "pt-PT": [("Firma", "THR33XYZ LABS - TECNOLOGIA E CONSULTORIA, UNIPESSOAL LDA"),
              ("Tipo", "Sociedade unipessoal por quotas"), ("Constituição", None),
              ("Sede", "Beco da Serra, 2, Sobral da Lagoa, 2510-651 Óbidos"), ("NIPC", "519573021"),
              ("D-U-N-S", None), ("Capital social", "7.660,00 €"), ("CAE", None)],
    "en": [("Legal name", "THR33XYZ LABS - TECNOLOGIA E CONSULTORIA, UNIPESSOAL LDA"),
           ("Type", "single-member private limited company"), ("Incorporated", None),
           ("Registered office", "Beco da Serra, 2, Sobral da Lagoa, 2510-651 Óbidos"), ("Tax number (NIPC)", "519573021"),
           ("D-U-N-S", None), ("Share capital", "€7,660.00"), ("Activity codes (CAE)", None)],
}
FICHA_LABEL = {"pt-PT": "(Ficha)", "en": "(Fact sheet)"}
FICHA_EXTRA = {"pt-PT": {"Constituição": "2026", "D-U-N-S": "348597205"}, "en": {"Incorporated": "2026", "D-U-N-S": "348597205"}}
# Marquee (#28): competências em loop na página inicial; a cópia para o loop não é lida duas vezes.
MARQUEE = {
    "pt-PT": ["Consultoria", "Web", "Apps", "UX/UI", "Hardware", "Jogos", "Realidade aumentada", "Laravel"],
    "en": ["Consulting", "Web", "Apps", "UX/UI", "Hardware", "Games", "Augmented reality", "Laravel"],
}
SITE_JS_MAX_GZIP = 8 * 1024    # o site.js comprimido
JS_TOTAL_MAX_GZIP = 70 * 1024  # orçamento total de JS da spec (gzip)

FONTS = {"Space Grotesk": "space-grotesk.woff2", "JetBrains Mono": "jetbrains-mono-regular.woff2"}
FONT_LICENCES = ["OFL.txt", "OFL-JetBrainsMono.txt"]
FONT_PRELOAD = "/assets/fonts/space-grotesk.woff2"
# (frente, fundo, mínimo) avaliados em cada esquema: claro, escuro e secção em Tinta.
CONTRAST_PAIRS = [
    ("--ink", "--paper", 4.5), ("--muted", "--paper", 4.5), ("--link", "--paper", 4.5),
    ("--focus", "--paper", 3), ("--secondary", "--paper", 4.5), ("--on-accent", "--accent", 4.5),
]

FORBIDDEN = re.compile(r"em breve|brevemente|coming soon|lorem ipsum|TODO", re.I)


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.lang = None
        self.title = ""
        self.meta = {}
        self.links = []          # (rel, href, hreflang)
        self.hrefs = []          # (href, target, rel)
        self.srcs = []
        self.h1 = 0
        self.ids = set()
        self.text = []
        self._in_title = False
        self._in_footer = 0
        self.footer_text = []
        self.footer_hrefs = []   # (href, target, rel) dentro de <footer>
        self.skeleton = []       # (tag, class) dentro de <main>: igual em PT e EN
        self.label_nums = []     # texto de .label-num, por ordem
        self.buttons = []        # atributos de cada <button>
        self.scripts = []        # atributos de cada <script>
        self.nav_nums = []       # texto de .nav-num no cabeçalho
        self.h1_attrs = []
        self.hero_gradient = []  # atributos de .hero-gradient
        self.blobs = 0
        self.hero_labels = []    # texto de .label dentro de .hero
        self.scroll_hints = []   # atributos de .hero-scroll
        self._in_hero = 0
        self.marquees = 0
        self.scenes = []         # (data-scene, classes) de cada <section> com cena
        self.icon_uses = []      # (href, aria-hidden do <svg>, focusable)
        self._svg = None
        self.marquee_lists = []  # (aria-hidden, [itens])
        self._in_marquee_list = False
        self.header_hrefs = []
        self._in_main = 0
        self._in_header = 0
        self._capture = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "html":
            self.lang = a.get("lang")
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            key = a.get("name") or a.get("property")
            if key:
                self.meta[key] = a.get("content", "")
        elif tag == "link":
            self.links.append((a.get("rel", ""), a.get("href", ""), a.get("hreflang")))
        elif tag == "a":
            self.hrefs.append((a.get("href", ""), a.get("target"), a.get("rel", "")))
            if self._in_footer:
                self.footer_hrefs.append((a.get("href", ""), a.get("target"), a.get("rel", "")))
        elif tag in ("img", "script"):
            if a.get("src"):
                self.srcs.append(a["src"])
            if tag == "script":
                self.scripts.append(a)
        elif tag == "button":
            self.buttons.append(a)
        elif tag == "h1":
            self.h1 += 1
            self.h1_attrs.append(a)
        elif tag == "footer":
            self._in_footer += 1
        elif tag == "main":
            self._in_main += 1
        elif tag == "header":
            self._in_header += 1
        if self._in_main and tag != "main":
            self.skeleton.append((tag, a.get("class", "")))
        if tag == "a" and self._in_header:
            self.header_hrefs.append(a.get("href", ""))
        classes = a.get("class", "").split()
        if tag == "section" and a.get("data-scene"):
            self.scenes.append((a["data-scene"], classes))
        if tag == "section" and "hero" in classes:
            self._in_hero = 1
        if "hero-gradient" in classes:
            self.hero_gradient.append(a)
        if "blob" in classes:
            self.blobs += 1
        if tag == "svg" and "icon" in classes:
            self._svg = a
        if tag == "use" and self._svg is not None:
            self.icon_uses.append((a.get("href", ""), self._svg.get("aria-hidden"), self._svg.get("focusable")))
        if "marquee" in classes:
            self.marquees += 1
        if "marquee-list" in classes:
            self.marquee_lists.append((a.get("aria-hidden"), []))
            self._in_marquee_list = True
        if tag == "li" and self._in_marquee_list:
            self._capture = self.marquee_lists[-1][1]
            self._capture.append("")
        if "hero-scroll" in classes:
            self.scroll_hints.append(a)
        if "label" in classes and self._in_hero:
            self._capture = self.hero_labels
            self.hero_labels.append("")
        elif "label-num" in classes:
            self._capture = self.label_nums
            self.label_nums.append("")
        elif "nav-num" in classes and self._in_header:
            self._capture = self.nav_nums
            self.nav_nums.append("")

    def handle_endtag(self, tag):
        if tag in ("span", "p", "li"):
            self._capture = None
        if tag == "ul":
            self._in_marquee_list = False
        if tag == "svg":
            self._svg = None
        if tag == "section":
            self._in_hero = 0
        if tag == "main":
            self._in_main -= 1
        elif tag == "header":
            self._in_header -= 1
        if tag == "title":
            self._in_title = False
        elif tag == "footer":
            self._in_footer -= 1

    def handle_data(self, data):
        if self._capture is not None:
            self._capture[-1] = " ".join((self._capture[-1] + data).split())
        if self._in_title:
            self.title += data
        self.text.append(data)
        if self._in_footer:
            self.footer_text.append(data)


def file_for(path):
    path = path.split("#")[0].split("?")[0]
    target = ROOT / path.lstrip("/")
    if path.endswith("/") or path == "":
        target = target / "index.html"
    return target


def parse(path):
    p = Page()
    p.feed(path.read_text(encoding="utf-8"))
    return p


def css_vars(block):
    return dict(re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", block))


def css_block(css, selector_re):
    """Devolve o corpo do primeiro bloco cujo seletor bate com selector_re (sem chavetas aninhadas)."""
    m = re.search(selector_re + r"\s*(?:,[^{}]*)?\{([^{}]*)\}", css)
    return m.group(1) if m else None


def luminance(hex_color):
    h = hex_color.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def resolve(name, scope, depth=0):
    value = scope.get(name, "").strip()
    m = re.fullmatch(r"var\((--[\w-]+)\)", value)
    if m and depth < 10:
        return resolve(m.group(1), scope, depth + 1)
    return value


def check_tokens(check):
    check(TOKENS_CSS.exists(), "assets/css/tokens.css em falta")
    if not TOKENS_CSS.exists():
        return
    css = TOKENS_CSS.read_text(encoding="utf-8")
    root = css_block(css, r"(?<![\w-]):root")
    check(root is not None, "tokens.css: bloco :root em falta")
    if root is None:
        return
    light = css_vars(root)
    for name, hex_color in PALETTE.items():
        check(light.get(name, "").upper() == hex_color, f"tokens.css: {name} deve ser {hex_color}")
    for name in REQUIRED_TOKENS:
        check(name in light, f"tokens.css: token {name} em falta")

    dark_media = re.search(r"@media\s*\(prefers-color-scheme:\s*dark\)\s*\{\s*:root\s*\{([^{}]*)\}", css)
    check(dark_media is not None, "tokens.css: modo escuro (prefers-color-scheme: dark) em falta")
    ink_section = css_block(css, r"\.theme-ink")
    check(ink_section is not None, "tokens.css: classe .theme-ink (secção em Tinta) em falta")

    for scene in ("ink", "telha"):
        check(re.search(rf'html:not\(\.scenes\) \.scene-{scene}\b', css),
              f"tokens.css: falta html:not(.scenes) .scene-{scene} (cor final sem JS e com reduced motion)")

    schemes = {"claro": light}
    if dark_media:
        schemes["escuro"] = {**light, **css_vars(dark_media.group(1))}
    if ink_section is not None:
        schemes[".theme-ink"] = {**light, **css_vars(ink_section)}
    for scene in ("ink", "telha"):
        block = css_block(css, rf'html\.scenes\[data-scene="{scene}"\]')
        check(block is not None, f'tokens.css: falta html.scenes[data-scene="{scene}"]')
        if block is not None:
            schemes[f"cena {scene}"] = {**light, **css_vars(block)}
    for scheme, scope in schemes.items():
        for fg, bg, minimum in CONTRAST_PAIRS:
            a, b = resolve(fg, scope), resolve(bg, scope)
            if not (re.fullmatch(r"#[0-9A-Fa-f]{6}", a) and re.fullmatch(r"#[0-9A-Fa-f]{6}", b)):
                check(False, f"tokens.css ({scheme}): {fg}/{bg} não resolvem para cores hex ({a!r}, {b!r})")
                continue
            ratio = contrast(a, b)
            check(ratio >= minimum, f"tokens.css ({scheme}): {fg} sobre {bg} tem {ratio:.2f}, mínimo {minimum}")

    # Fontes servidas pelo site em WOFF2, com font-display: swap e licença ao lado.
    faces = re.findall(r"@font-face\s*\{([^{}]*)\}", css)
    for family, file in FONTS.items():
        face = next((f for f in faces if re.search(rf"font-family:\s*\"{family}\"", f)), None)
        check(face is not None, f"tokens.css: @font-face de {family} em falta")
        if face:
            check(f'url("/assets/fonts/{file}") format("woff2")' in face, f"tokens.css: {family} deve usar /assets/fonts/{file}")
            check(re.search(r"font-display:\s*swap", face), f"tokens.css: {family} sem font-display: swap")
        check((ROOT / "assets" / "fonts" / file).exists(), f"assets/fonts/{file} em falta")
    for licence in FONT_LICENCES:
        check((ROOT / "assets" / "fonts" / licence).exists(), f"assets/fonts/{licence} em falta (licença OFL)")

    site_css = (ROOT / "assets" / "site.css").read_text(encoding="utf-8")
    check(not re.search(r"\.ttf\b|@font-face", site_css), "site.css: as fontes ficam no tokens.css, em WOFF2")
    loose = re.findall(r"#[0-9A-Fa-f]{3,8}\b|\b(?:rgba?|hsla?)\(", site_css)
    check(not loose, f"site.css: cores soltas {sorted(set(loose))} (usar os tokens)")


def shape(value):
    if isinstance(value, dict):
        return {k: shape(v) for k, v in value.items()}
    if isinstance(value, list):
        return [shape(v) for v in value]
    return type(value).__name__


def check_content(check):
    import json
    data = {}
    for lang, path in CONTENT.items():
        check(path.exists(), f"{path.relative_to(BASE)} em falta")
        if path.exists():
            data[lang] = json.loads(path.read_text(encoding="utf-8"))
    if len(data) == 2:
        check(shape(data["pt"]["pages"]) == shape(data["en"]["pages"]),
              "src/content: pt.json e en.json têm estruturas de páginas diferentes")
    check(not (BASE / "src" / "pages").exists(), "src/pages ainda existe: as páginas vêm de src/content")


def check_header(check, url, p):
    toggles = [b for b in p.buttons if "menu-toggle" in b.get("class", "")]
    check(len(toggles) == 1, f"{url}: deve ter um botão .menu-toggle, tem {len(toggles)}")
    if toggles:
        t = toggles[0]
        check(t.get("type") == "button", f"{url}: .menu-toggle sem type=button")
        check(t.get("aria-expanded") == "false", f"{url}: .menu-toggle deve começar com aria-expanded=false")
        check(t.get("aria-controls") in p.ids, f"{url}: aria-controls do menu não aponta para um id")
        check(t.get("aria-label"), f"{url}: .menu-toggle sem aria-label")
    check(p.nav_nums == ["01", "02", "03", "04", "05"], f"{url}: menu deve numerar 01–05, tem {p.nav_nums}")
    check(sum(1 for s in p.scripts if s.get("src", "").split("?")[0] == SITE_JS) == 1, f"{url}: sem {SITE_JS}")


def check_hero(check, url, p, is_home, lang):
    check(all("data-split" in a for a in p.h1_attrs), f"{url}: o <h1> deve ter data-split (reveal por linhas)")
    if not is_home:
        check(not p.hero_gradient, f"{url}: o gradiente-assinatura é só da página inicial")
        return
    check(p.hero_labels == [HERO_LABEL[lang]], f"{url}: etiqueta do hero deve ser '{HERO_LABEL[lang]}', é {p.hero_labels}")
    check(len(p.hero_gradient) == 1 and p.hero_gradient[0].get("aria-hidden") == "true",
          f"{url}: falta o .hero-gradient com aria-hidden=true")
    check(p.blobs == HERO_BLOBS, f"{url}: o gradiente deve ter {HERO_BLOBS} manchas, tem {p.blobs}")
    check(len(p.scroll_hints) == 1, f"{url}: falta a indicação ↓ scroll (.hero-scroll)")


def check_motion_css(check):
    css = (ROOT / "assets" / "site.css").read_text(encoding="utf-8")
    reduced = re.search(r"@media\s*\(prefers-reduced-motion:\s*reduce\)\s*\{(.*?)\n\}", css, re.S)
    check(reduced is not None, "site.css: bloco prefers-reduced-motion em falta")
    if reduced:
        for needle in (".blob", ".wi", ".marquee-track", ".reveal"):
            check(needle in reduced.group(1), f"site.css: prefers-reduced-motion não trata {needle}")
    # Se o JS falhar depois de pôr .js, o título não pode ficar invisível para sempre.
    body = re.search(r"\nbody\s*\{([^}]*)\}", css)
    check(body is not None and "background-color" in body.group(1) and "transition" in body.group(1),
          "site.css: o body precisa de transition em background-color (mudança de cena)")
    grow = re.search(r"\.more:hover[^{]*\{([^}]*)\}", css)
    check(grow is not None and "background-size: 100%" in grow.group(1), "site.css: falta o sublinhado que cresce em .more:hover")
    check('content: "→"' in css and 'content: "↗"' in css, "site.css: faltam as setas → (links internos) e ↗ (externos)")
    marquee = re.search(r"\.marquee\s*\{([^}]*)\}", css)
    check(marquee is not None and "overflow: hidden" in marquee.group(1), "site.css: .marquee sem overflow: hidden")
    guard = re.search(r"\.js \[data-split\]:not\(\.split\)\s*\{([^}]*)\}", css)
    check(guard is not None and "animation" in guard.group(1),
          "site.css: falta a salvaguarda .js [data-split]:not(.split) com animation")


def check_marquee(check, url, p, lang, is_home):
    if not is_home:
        check(p.marquees == 0, f"{url}: o marquee é só da página inicial")
        return
    check(p.marquees == 1, f"{url}: falta o .marquee")
    check(len(p.marquee_lists) == 2, f"{url}: o marquee deve ter 2 listas (original e cópia), tem {len(p.marquee_lists)}")
    if len(p.marquee_lists) == 2:
        (hidden_a, items_a), (hidden_b, items_b) = p.marquee_lists
        check(hidden_a is None, f"{url}: a primeira lista do marquee tem de ser lida")
        check(hidden_b == "true", f"{url}: a cópia do marquee tem de ter aria-hidden=true")
        check(items_a == MARQUEE[lang] and items_b == MARQUEE[lang], f"{url}: itens do marquee {items_a}")


def icon_symbols():
    if not ICONS_SVG.exists():
        return {}
    svg = ICONS_SVG.read_text(encoding="utf-8")
    return {m.group(1): m.group(2) for m in re.finditer(r'<symbol id="([\w-]+)"[^>]*>(.*?)</symbol>', svg, re.S)}


def check_icons(check):
    check(ICONS_SVG.exists(), "assets/icons.svg em falta (sprite dos ícones)")
    check(ICONS_LICENCE.exists(), "assets/icons-LICENSE.txt em falta (licença ISC do Lucide)")
    # O <use> não herda os atributos do <svg> raiz do sprite: cada <symbol> leva os seus.
    if ICONS_SVG.exists():
        for m in re.finditer(r"<symbol ([^>]*)>", ICONS_SVG.read_text(encoding="utf-8")):
            check('fill="none"' in m.group(1) and 'stroke="currentColor"' in m.group(1),
                  f"icons.svg: <symbol {m.group(1)[:30]}…> sem fill=none e stroke=currentColor")
    for name, body in icon_symbols().items():
        shapes = re.findall(r"<(path|circle|rect|line|polyline|polygon|ellipse)\b([^>]*)>", body)
        check(shapes and all('pathLength="1"' in attrs for _, attrs in shapes),
              f"icons.svg: #{name} precisa de pathLength=\"1\" em cada forma (traço animado)")


def check_page_icons(check, url, p, html, is_home, is_services):
    symbols = icon_symbols()
    for href, hidden, focusable in p.icon_uses:
        check(href.split("?")[0].split("#")[0] == "/assets/icons.svg" and href.split("#")[1] in symbols, f"{url}: ícone inexistente {href}")
        check(hidden == "true" and focusable == "false", f"{url}: ícone {href} sem aria-hidden=true e focusable=false")
    count = lambda cls: len(re.findall(rf'<li class="card {cls}">\s*<span class="card-icon"', html))
    if is_home:
        check(count("card-service") == HOME_ICONS["service"], f"{url}: os {HOME_ICONS['service']} cartões de serviço precisam de ícone")
        check(count("card-step") == HOME_ICONS["step"], f"{url}: os 4 passos precisam de ícone")
    if is_services:
        n = len(re.findall(r'<section class="service"[^>]*>\s*<div class="service-head">\s*<span class="card-icon"', html))
        check(n == SERVICES_PAGE_ICONS, f"{url}: cada serviço precisa de ícone ({n} de {SERVICES_PAGE_ICONS})")


def section_labels(html):
    return re.findall(r'<p class="label"><span class="label-num">\(\d+\)</span> ([^<]+)</p>', html)


def check_scenes(check, url, p):
    base = url.replace("/en", "", 1) if url.startswith("/en/") else url
    base = {"/about/": "/sobre/", "/services/": "/servicos/", "/products/": "/produtos/", "/contact/": "/contacto/",
            "/privacy/": "/privacidade/", "/terms/": "/termos/",
            "/products/get-it-vac/": "/produtos/get-it-vac/"}.get(base, base)
    expected = SCENES.get(base, [])
    check([sc for sc, _ in p.scenes] == expected, f"{url}: cenas {[sc for sc, _ in p.scenes]}, esperado {expected}")
    for scene, classes in p.scenes:
        check(f"scene-{scene}" in classes, f"{url}: secção data-scene={scene} sem a classe scene-{scene}")


def check_cta(check, url, html, lang, has_cta):
    """CTA final: título em tamanho de hero com escala no scroll e email grande e clicável."""
    m = re.search(r'<section class="band scene-telha"[^>]*>(.*?)</section>', html, re.S)
    if not has_cta:
        return
    check(m is not None, f"{url}: falta o CTA final (secção scene-telha)")
    if m is None:
        return
    cta = m.group(1)
    title = re.search(r'<h2 class="cta-title"[^>]*>(.*?)</h2>', cta, re.S)
    check(title is not None and title.group(1).strip() == CTA_TITLE[lang],
          f"{url}: o CTA final deve ter <h2 class=\"cta-title\">{CTA_TITLE[lang]}</h2>")
    check(title is not None and "data-cta-scale" in title.group(0), f"{url}: o título do CTA precisa de data-cta-scale")
    check(re.search(rf'<a class="cta-email" href="mailto:{EMAIL}">{EMAIL}</a>', cta),
          f"{url}: o CTA final precisa do email {EMAIL} grande e clicável (a.cta-email)")


def check_footer(check, url, html, lang):
    """Rodapé legal sucinto em duas linhas (art. 171.º CSC), sem nada escondido."""
    m = re.search(r'<footer class="site-footer">(.*?)</footer>', html, re.S)
    check(m is not None, f"{url}: rodapé em falta")
    if m is None:
        return
    footer = m.group(1)
    line1 = re.search(r'<ul class="footer-line">(.*?)</ul>', footer, re.S)
    legal = re.findall(r'<p class="legal">(.*?)</p>', footer, re.S)
    check(line1 is not None, f"{url}: falta a linha 1 do rodapé (ul.footer-line)")
    check(len(legal) == 1, f"{url}: o rodapé deve ter uma só linha legal (p.legal), tem {len(legal)}")
    check("footer-grid" not in footer, f"{url}: o rodapé passa a duas linhas, sem .footer-grid")
    if line1 is None or len(legal) != 1:
        return
    check(footer.index('class="footer-line"') < footer.index('class="legal"'), f"{url}: a linha 1 vem antes da linha legal")
    hrefs = re.findall(r'href="([^"]+)"', line1.group(1))
    expected = [f"mailto:{EMAIL}", PHONE_HREF] + FOOTER_LINE1[lang] + [COMPLAINTS_URL]
    check(hrefs == expected, f"{url}: linha 1 do rodapé com {hrefs}, esperado {expected}")
    check(f"© {date.today().year} Thr33 Labs" in line1.group(1), f"{url}: linha 1 sem '© {date.today().year} Thr33 Labs'")
    check(len(re.findall(r'href="', footer)) == len(expected), f"{url}: o rodapé só leva as ligações da linha 1")
    text = " ".join(re.sub(r"<[^>]+>", " ", legal[0]).split())
    for needle in LEGAL_FOOTER[lang]:
        check(needle in text, f"{url}: linha legal sem '{needle}'")


def check_ficha(check, url, html, lang, is_about):
    blocks = re.findall(r'<dl class="ficha">(.*?)</dl>', html, re.S)
    if not is_about:
        check(not blocks, f"{url}: a (Ficha) é só da página Sobre")
        return
    check(len(blocks) == 1, f"{url}: falta o bloco (Ficha) em <dl class=\"ficha\">")
    if len(blocks) != 1:
        return
    main = html[html.index("<main"):html.index("</main>")]
    last = main[main.rindex("<section"):]
    check('<dl class="ficha">' in last, f"{url}: a (Ficha) tem de ser a última secção")
    check(f'<p class="label">{FICHA_LABEL[lang]}</p>' in last, f"{url}: a Ficha leva a etiqueta {FICHA_LABEL[lang]}")
    rows = re.findall(r"<div><dt>(.*?)</dt><dd>(.*?)</dd></div>", blocks[0], re.S)
    terms = [t for t, _ in rows]
    expected = [t for t, _ in FICHA[lang]]
    check(terms == expected, f"{url}: Ficha com {terms}, esperado {expected}")
    values = dict(rows)
    legal = re.search(r'<p class="legal">(.*?)</p>', html, re.S)
    legal_text = legal.group(1) if legal else ""
    for term, needle in FICHA[lang]:
        if needle and term in values:
            check(needle.lower() in values[term].lower(), f"{url}: Ficha '{term}' devia conter '{needle}'")
            check(needle.lower() in legal_text.lower(), f"{url}: rodapé legal sem '{needle}' (Ficha e rodapé têm de bater certo)")
    for term, value in FICHA_EXTRA[lang].items():
        check(values.get(term) == value, f"{url}: Ficha '{term}' devia ser {value}")


# WCAG 2.5.3 (nome no rótulo): o link de língua mostra "EN"/"PT", por isso o nome acessível
# tem de começar por esse texto. Sem aria-label; o nome completo vai num span .sr-only.
LANG_LINK = {"pt-PT": ("EN", "English"), "en": ("PT", "Português")}


def check_lang_link(check, url, html, lang):
    m = re.search(r'<a class="lang"([^>]*)>(.*?)</a>', html, re.S)
    check(m is not None, f"{url}: link de língua em falta")
    if m is None:
        return
    short, full = LANG_LINK[lang]
    check("aria-label" not in m.group(1), f"{url}: o link de língua não leva aria-label (nome tem de conter '{short}')")
    inner = m.group(2)
    check(re.search(rf'>{short}<span class="sr-only"> {full}</span>$', inner) is not None,
          f"{url}: link de língua deve ser '{short}' + <span class=\"sr-only\"> {full}</span>")


# Versão nos URLs (cache do Cloudflare e dos browsers): cada ficheiro que muda entre deploys é
# referido com ?v=<8 primeiros hex do sha256 do conteúdo>. Um deploy novo muda o URL.
VERSIONED = ["/assets/css/tokens.css", "/assets/site.css", "/assets/js/site.js", "/assets/js/consent.js",
             "/assets/icons.svg"]


def check_versions(check, name, html):
    import hashlib
    for path in VERSIONED:
        f = ROOT / path.lstrip("/")
        if not f.exists():
            continue
        want = hashlib.sha256(f.read_bytes()).hexdigest()[:8]
        refs = re.findall(rf'(?:href|src)="{re.escape(path)}([^"#]*)', html)
        for query in refs:
            check(query == f"?v={want}", f"{name}: {path}{query} devia ser {path}?v={want}")


def check_footer_css(check):
    css = (ROOT / "assets" / "site.css").read_text(encoding="utf-8")
    legal = re.search(r"\n\.legal\s*\{([^}]*)\}", css)
    check(legal is not None, "site.css: regra .legal em falta")
    if legal:
        body = legal.group(1)
        check("var(--font-mono)" in body, "site.css: .legal em JetBrains Mono (var(--font-mono))")
        check("color: var(--muted)" in body, "site.css: .legal em Pedra (var(--muted)), contraste AA verificado nos tokens")
        size = re.search(r"font-size:\s*([\d.]+)rem", body)
        check(size is not None and 0.6875 <= float(size.group(1)) <= 0.75, "site.css: .legal entre 11 e 12 px")
    line1 = re.search(r"\n\.footer-line\s*\{([^}]*)\}", css)
    check(line1 is not None and "--font-mono" not in line1.group(1), "site.css: .footer-line em Space Grotesk")
    title = re.search(r"\n\.cta-title\s*\{([^}]*)\}", css)
    check(title is not None and "var(--text-hero)" in title.group(1), "site.css: .cta-title em tamanho de hero")
    ficha = re.search(r"\n\.ficha\s*\{([^}]*)\}", css)
    check(ficha is not None and "var(--font-mono)" in ficha.group(1), "site.css: .ficha em JetBrains Mono")
    row = re.search(r"\n\.ficha div\s*\{([^}]*)\}", css)
    check(row is not None and "grid-template-columns" not in row.group(1), "site.css: .ficha numa coluna em mobile")
    check(re.search(r"@media \(min-width: [\d.]+rem\) \{[^@]*?\.ficha div\s*\{[^}]*grid-template-columns", css),
          "site.css: .ficha em duas colunas a partir de um min-width")
    js = (ROOT / SITE_JS.lstrip("/")).read_text(encoding="utf-8")
    check("data-cta-scale" in js, "site.js: falta a escala do CTA final (data-cta-scale)")


def check_labels(check, url, p):
    expected = [f"({i:02d})" for i in range(1, len(p.label_nums) + 1)]
    check(p.label_nums == expected, f"{url}: etiquetas fora de ordem {p.label_nums}")


def check_no_js_hiding(check):
    css = (ROOT / "assets" / "site.css").read_text(encoding="utf-8")
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        if re.search(r"display:\s*none|visibility:\s*hidden", body):
            for sel in selectors.split(","):
                sel = sel.strip()
                # Esconder uma cópia com aria-hidden="true" (o marquee) não tira conteúdo a ninguém.
                ok = (sel.startswith(".js ") or sel.startswith("html:not(.js)") or sel.startswith("[hidden]")
                      or sel.endswith('[aria-hidden="true"]'))
                check(ok, f"site.css: '{sel}' esconde conteúdo sem depender de .js")
    js = ROOT / SITE_JS.lstrip("/")
    check(js.exists(), f"{SITE_JS} em falta")
    if js.exists():
        import gzip
        size = len(gzip.compress(js.read_bytes()))
        check(size <= SITE_JS_MAX_GZIP, f"{SITE_JS} tem {size} bytes gzip (máx. {SITE_JS_MAX_GZIP})")
        total = sum(len(gzip.compress(f.read_bytes())) for f in ROOT.rglob("*.js"))
        check(total <= JS_TOTAL_MAX_GZIP, f"JS total {total} bytes gzip (máx. {JS_TOTAL_MAX_GZIP})")


# Fecho do redesign (#35): reduced motion, foco, imagens e CSP.
# Funções do site.js que mexem em movimento: todas têm de respeitar prefers-reduced-motion.
MOTION_FUNCTIONS = ["followPointer", "marqueeScroll", "countLabels", "revealGroups", "colourScenes",
                    "magneticButtons", "ctaScale"]


def js_function(js, name):
    m = re.search(rf"function {name}\(.*?\n\}}", js, re.S)
    return m.group(0) if m else None


def check_finish(check):
    css = (ROOT / "assets" / "site.css").read_text(encoding="utf-8")
    plain = re.sub(r"/\*.*?\*/", "", css, flags=re.S)

    # Reduced motion: uma regra universal corta animações e transições de tudo, incluindo o que
    # vier depois; e o scroll suave, se existir, desliga-se.
    reduced = re.search(r"@media\s*\(prefers-reduced-motion:\s*reduce\)\s*\{(.*?)\n\}", plain, re.S)
    block = reduced.group(1) if reduced else ""
    universal = re.search(r"\*,\s*\*::before,\s*\*::after\s*\{([^}]*)\}", block)
    check(universal is not None and "animation: none !important" in universal.group(1)
          and "transition: none !important" in universal.group(1),
          "site.css: reduced motion precisa de *, *::before, *::after { animation: none !important; transition: none !important }")
    check(".cta-title" in block, "site.css: prefers-reduced-motion não trata .cta-title")
    sr = re.search(r"\n\.sr-only\s*\{([^}]*)\}", plain)
    check(sr is not None and "clip" in sr.group(1) and "position: absolute" in sr.group(1),
          "site.css: falta .sr-only (texto só para leitores de ecrã)")
    # Marquee parado: as competências quebram em linhas e a cópia sai, para nada ficar cortado.
    track = re.search(r"\.marquee-track\s*\{([^}]*)\}", block)
    check(track is not None and "flex-wrap: wrap" in track.group(1) and "width: auto" in track.group(1),
          "site.css: em reduced motion o .marquee-track quebra em linhas (flex-wrap: wrap; width: auto)")
    copy = re.search(r'\.marquee-list\[aria-hidden="true"\]\s*\{([^}]*)\}', block)
    check(copy is not None and "display: none" in copy.group(1),
          "site.css: em reduced motion a cópia do marquee (aria-hidden) sai")
    if "scroll-behavior: smooth" in plain:
        check("scroll-behavior: auto" in block, "site.css: scroll suave sem ser desligado em reduced motion")

    # Foco do teclado sempre visível, em --focus (Atlântico; Tinta na cena Telha).
    focus = re.search(r"(?<![\w-]):focus-visible\s*\{([^}]*)\}", plain)
    check(focus is not None and "outline: 2px solid var(--focus)" in focus.group(1),
          "site.css: :focus-visible com outline: 2px solid var(--focus)")
    for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", plain):
        if re.search(r"outline:\s*(none|0)\b", body):
            check("box-shadow" in body or "border" in body,
                  f"site.css: '{selectors.strip()}' tira o outline sem alternativa visível")

    js = (ROOT / SITE_JS.lstrip("/")).read_text(encoding="utf-8")
    for name in MOTION_FUNCTIONS:
        body = js_function(js, name)
        check(body is not None, f"site.js: função {name} em falta")
        if body is not None:
            check("reducedMotion" in body, f"site.js: {name} não respeita prefers-reduced-motion")
    check(not re.search(r"\beval\(|new Function\(|innerHTML\s*=", js), "site.js: eval, new Function ou innerHTML")
    # Quem chega com Tab a um grupo ainda por revelar tem de ver logo o que tem foco.
    reveal = js_function(js, "revealGroups") or ""
    check("focusin" in reveal, "site.js: revealGroups tem de revelar o grupo logo no focusin")

    # CSP sem unsafe-inline nem unsafe-eval; o HTML já é verificado sem inline.
    deploy = (BASE / "docs" / "deploy.md").read_text(encoding="utf-8")
    csp = re.search(r'Content-Security-Policy "([^"]+)"', deploy)
    check(csp is not None and "script-src 'self'" in csp.group(1) and "unsafe-" not in csp.group(1),
          "docs/deploy.md: CSP com script-src 'self' e sem unsafe-inline/unsafe-eval")

    for f in sorted(ROOT.rglob("*.html")):
        html = f.read_text(encoding="utf-8")
        name = f.relative_to(ROOT)
        for tag in re.findall(r"<img\b[^>]*>", html):
            check(re.search(r'\salt="', tag), f"{name}: <img> sem alt ({tag[:60]})")
            check(re.search(r'\swidth="\d+"', tag) and re.search(r'\sheight="\d+"', tag),
                  f"{name}: <img> sem width e height ({tag[:60]})")
        for value in re.findall(r'tabindex="(-?\d+)"', html):
            check(int(value) <= 0, f"{name}: tabindex={value} quebra a ordem de tabulação")


# Ajustes de novembro 2026: hero em 3 linhas no desktop, "Ver mais" nos cartões e nome do Vizia.
HERO_DESKTOP_MAX = "8rem"
MORE_TEXT = {"pt-PT": "Ver mais", "en": "See more"}
VIZIA = "Vizia - Arquitetura em AR"

# Google Analytics 4 só depois de consentimento (RGPD + Lei 41/2004, art. 5.º).
GA_ID = "G-JCJZ754SWW"
CONSENT_JS = "/assets/js/consent.js"
CONSENT_COOKIE = "thr33_consent"
COOKIE_PAGE = {"pt-PT": "/cookies/", "en": "/en/cookies/"}
CONSENT_TEXT = {
    "pt-PT": ("Aceitar cookies de análise", "Recusar cookies de análise", "Preferências de cookies"),
    "en": ("Accept analytics cookies", "Reject analytics cookies", "Cookie settings"),
}


def check_cookie_banner_css(check):
    """Desktop: banner no canto inferior direito; mobile: largura toda, em baixo."""
    css = (ROOT / "assets" / "site.css").read_text(encoding="utf-8")
    m = re.search(r"@media \(min-width: 48rem\) \{\s*\.cookie-banner\s*\{([^}]*)\}", css)
    body = m.group(1) if m else ""
    check("left: auto" in body and "right: 1.5rem" in body and "margin-inline: 0" in body,
          "site.css: no desktop (min-width: 48rem) o .cookie-banner fica no canto inferior direito")
    ghost = re.search(r"\.cookie-banner \.btn-ghost\s*\{([^}]*)\}", css)
    check(ghost is not None and "background: transparent" in ghost.group(1),
          "site.css: o botão secundário do banner (<button>.btn-ghost) precisa de background: transparent")


def check_hero_desktop(check):
    css = (ROOT / "assets" / "site.css").read_text(encoding="utf-8")
    m = re.search(r"@media \(min-width: 64rem\) \{[^@]*?\.hero h1\s*\{([^}]*)\}", css)
    check(m is not None and f"min(var(--text-hero), {HERO_DESKTOP_MAX})" in m.group(1),
          f"site.css: no desktop (min-width: 64rem) o .hero h1 fica em min(var(--text-hero), {HERO_DESKTOP_MAX}), 3 linhas")


def check_more_links(check, url, html, lang):
    """Links dos cartões: "Ver mais" numa linha; o destino vai num .sr-only (WCAG 2.4.4 e 2.5.3)."""
    for inner in re.findall(r'<a class="more"[^>]*>(.*?)</a>', html, re.S):
        ok = re.fullmatch(rf'{MORE_TEXT[lang]}<span class="sr-only"> [^<]+</span>', inner)
        check(ok is not None, f"{url}: link .more deve ser '{MORE_TEXT[lang]}' + .sr-only, é '{inner}'")


def check_vizia(check, url, html):
    main = html[html.index("<main"):html.index("</main>")]
    text = re.sub(r'[\w-]+="[^"]*"', "", main)
    text = re.sub(r"vizia\.thr33\.xyz", "", text)
    check(not re.search(r"\bvizia\b", text), f"{url}: 'vizia' em minúsculas; o nome é '{VIZIA}'")
    if url in ("/produtos/", "/en/products/", "/", "/en/"):
        check(re.search(rf'class="product-name">{re.escape(VIZIA)}</h[23]>', main), f"{url}: o produto chama-se '{VIZIA}'")


def check_consent_html(check, url, html, lang):
    """Banner de cookies em todas as páginas: escondido sem JS, aceitar e recusar com o mesmo peso."""
    accept, reject, settings = CONSENT_TEXT[lang]
    scripts = re.findall(rf'<script src="{re.escape(CONSENT_JS)}[^"]*"([^>]*)></script>', html)
    check(len(scripts) == 1 and "defer" in scripts[0], f"{url}: falta <script src=\"{CONSENT_JS}\" defer>")
    banner = re.search(r'<div class="cookie-banner" id="cookie-banner"([^>]*)>(.*?)\n  </div>', html, re.S)
    check(banner is not None, f"{url}: falta o banner de cookies (div.cookie-banner#cookie-banner)")
    if banner:
        attrs, inner = banner.groups()
        check(" hidden" in attrs, f"{url}: o banner começa com hidden (sem JS não há GA nem banner)")
        check('role="region"' in attrs and "aria-labelledby=" in attrs, f"{url}: banner sem role=region e aria-labelledby")
        check(re.search(rf'<button class="btn btn-primary" type="button" data-consent="granted">{accept}</button>', inner),
              f"{url}: banner sem botão '{accept}'")
        check(re.search(rf'<button class="btn btn-ghost" type="button" data-consent="denied">{reject}</button>', inner),
              f"{url}: banner sem botão secundário '{reject}' (btn-ghost, na mesma camada que aceitar)")
        check(f'href="{COOKIE_PAGE[lang]}"' in inner, f"{url}: banner sem link para {COOKIE_PAGE[lang]}")
        footer_end = html.index("</footer>")
        check(html.index('id="cookie-banner"') > footer_end, f"{url}: o banner vem depois do rodapé")
    footer = re.search(r'<footer class="site-footer">(.*?)</footer>', html, re.S)
    check(footer is not None and re.search(
        rf'<li hidden><button class="footer-button" type="button" data-consent-open>{settings}</button></li>', footer.group(1)),
        f"{url}: rodapé sem botão '{settings}' (data-consent-open, li hidden sem JS)")


def check_consent_js(check):
    f = ROOT / CONSENT_JS.lstrip("/")
    check(f.exists(), f"{CONSENT_JS} em falta")
    if not f.exists():
        return
    js = f.read_text(encoding="utf-8")
    check(GA_ID in js, f"{CONSENT_JS}: sem o ID {GA_ID}")
    check(CONSENT_COOKIE in js and "SameSite=Lax" in js and "max-age=" in js,
          f"{CONSENT_JS}: a escolha guarda-se no cookie {CONSENT_COOKIE} (max-age, SameSite=Lax)")
    check("localStorage" not in js, f"{CONSENT_JS}: consentimento em cookie, não em localStorage")
    default = js.find('gtag("consent", "default"')
    load = js.find("googletagmanager.com/gtag/js")
    check(default != -1 and "analytics_storage: \"denied\"" in js, f"{CONSENT_JS}: Consent Mode v2 com tudo denied por defeito")
    check(load > default != -1, f"{CONSENT_JS}: o gtag.js só se pede depois do consent default")
    load_fn = re.search(r"function loadAnalytics\(\) \{.*?\n  \}", js, re.S)
    check(load_fn is not None and "googletagmanager.com/gtag/js" in load_fn.group(0),
          f"{CONSENT_JS}: o gtag.js só carrega dentro de loadAnalytics()")
    calls = re.findall(r"(?<!function )loadAnalytics\(\)", js)
    check(len(calls) == 2, f"{CONSENT_JS}: loadAnalytics() só se chama com consentimento (cookie granted ou aceitar)")
    check("_ga" in js, f"{CONSENT_JS}: ao recusar apagam-se os cookies _ga")
    check(not re.search(r"\beval\(|new Function\(|innerHTML\s*=", js), f"{CONSENT_JS}: eval, new Function ou innerHTML")
    check("ad_storage: \"denied\"" in js and "ad_storage: \"granted\"" not in js,
          f"{CONSENT_JS}: sem publicidade: ad_storage fica sempre denied")


def check_cookie_policy(check, pages_raw):
    for lang, (privacy, cookies) in {"pt-PT": ("/privacidade/", "/cookies/"), "en": ("/en/privacy/", "/en/cookies/")}.items():
        raw = pages_raw.get(privacy, "")
        check("Google Analytics" in raw, f"{privacy}: a política de privacidade tem de referir o Google Analytics")
        check("não usa cookies" not in raw and "does not use cookies" not in raw,
              f"{privacy}: ainda diz que o site não usa cookies")
        check(f'href="{cookies}"' in raw[raw.index("<main"):], f"{privacy}: sem link para {cookies}")
        pol = pages_raw.get(cookies, "")
        for needle in ("_ga", CONSENT_COOKIE, "Google Ireland", f'data-consent-open'):
            check(needle in pol, f"{cookies}: falta '{needle}'")
    deploy = (BASE / "docs" / "deploy.md").read_text(encoding="utf-8")
    csp = re.search(r'Content-Security-Policy "([^"]+)"', deploy)
    value = csp.group(1) if csp else ""
    check("script-src 'self' https://www.googletagmanager.com" in value,
          "docs/deploy.md: CSP tem de permitir https://www.googletagmanager.com em script-src")
    check("connect-src 'self' https://*.google-analytics.com https://*.analytics.google.com" in value,
          "docs/deploy.md: CSP tem de permitir o GA em connect-src")


# Reposicionamento (#52): estúdio de tecnologia interativa, sem tamanho da equipa, AR em vez de 3D
# e cinco serviços. Vendemos software e serviços, nunca equipamentos.
POSITIONING = {"pt-PT": "estúdio de tecnologia interativa", "en": "interactive technology studio"}
SUPPORT_LINE = {"pt-PT": "Hardware, software e realidade aumentada para experiências que as pessoas tocam e usam.",
                "en": "Hardware, software and augmented reality for experiences people touch and use."}
FOUNDER = {"pt-PT": "Fundada por Thiago Oliveira, engenheiro de software com mais de 10 anos de experiência.",
           "en": "Founded by Thiago Oliveira, Software Engineer with over 10 years of experience."}
RETIRED_COPY = re.compile(
    r"produto digital em|estúdio de produto digital|estúdio independente de produto digital|digital product studio"
    r"|estúdio pequeno|small studio|quem fundou|sem intermediários|its founder|the founder|no middlemen"
    r"|modelos 3D|3D models|venda de equipamentos|vendemos equipamentos|sell(?:ing)? (?:equipment|hardware|devices)",
    re.I)
SERVICE_IDS = {"pt-PT": ["consultoria", "produto-digital", "hardware", "jogos", "realidade-aumentada"],
               "en": ["consulting", "digital-product", "hardware", "games", "augmented-reality"]}


def page_text(html):
    """Texto visível do <main> e da <head> (title e meta), sem etiquetas."""
    head = html[:html.index("<body")] if "<body" in html else ""
    main = html[html.index("<main"):html.index("</main>")] if "<main" in html else ""
    metas = " ".join(re.findall(r'<meta [^>]*content="([^"]*)"', head))
    title = re.search(r"<title>(.*?)</title>", head, re.S)
    text = re.sub(r"<[^>]+>", " ", main)
    return " ".join(f"{title.group(1) if title else ''} {metas} {text}".split())


def check_positioning(check, url, html, lang, is_home, is_about, is_services):
    text = page_text(html)
    m = RETIRED_COPY.search(text)
    check(not m, f"{url}: copy antiga '{m.group(0) if m else ''}' (#52)")
    check("linkedin" not in html.lower(), f"{url}: sem LinkedIn (#52)")
    alt = re.search(r'<meta property="og:image:alt" content="([^"]*)"', html)
    check(alt is not None and POSITIONING[lang] in alt.group(1).lower(),
          f"{url}: og:image:alt sem '{POSITIONING[lang]}'")
    founder_here = "Thiago Oliveira" in text
    check(founder_here == is_about, f"{url}: o fundador só aparece no Sobre (#52)")
    if is_about:
        main = html[html.index("<main"):html.index("</main>")]
        check(f"<p>{FOUNDER[lang]}</p>" in main, f"{url}: falta a menção curta ao fundador '{FOUNDER[lang]}'")
        check(not re.search(r"<img|<picture", main), f"{url}: o fundador não leva foto")
    if is_home:
        title = re.search(r"<title>(.*?)</title>", html, re.S).group(1)
        desc = re.search(r'<meta name="description" content="([^"]*)"', html).group(1)
        check(POSITIONING[lang] in title.lower(), f"{url}: <title> sem '{POSITIONING[lang]}'")
        check(POSITIONING[lang].split()[-1] in desc.lower() or POSITIONING[lang] in desc.lower(),
              f"{url}: meta description sem o posicionamento novo")
        h1 = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S).group(1)
        check(" ".join(re.sub(r"<[^>]+>", "", h1).split()) == HERO_H1[lang], f"{url}: o h1 do hero deve ser '{HERO_H1[lang]}'")
        lead = re.search(r'<section class="hero">.*?<p class="lead">(.*?)</p>', html, re.S)
        check(lead is not None and lead.group(1).startswith(SUPPORT_LINE[lang]),
              f"{url}: o lead do hero começa pela linha de apoio '{SUPPORT_LINE[lang]}'")
        check('<ul class="grid grid-5" data-reveal>' in html, f"{url}: os 5 serviços vão numa .grid-5")
    if is_services:
        ids = re.findall(r'<section class="service" id="([^"]+)"', html)
        check(ids == SERVICE_IDS[lang], f"{url}: serviços {ids}, esperado {SERVICE_IDS[lang]}")


def check_grid5_css(check):
    """5 cartões sem buracos: 1 coluna em mobile, 2+2+1 (o último a toda a largura) e 3+2 no desktop."""
    css = (ROOT / "assets" / "site.css").read_text(encoding="utf-8")
    tablet = re.search(r"@media \(min-width: 40rem\) \{[^@]*?\.grid-5 > :last-child\s*\{[^}]*grid-column: 1 / -1", css)
    check(tablet is not None, "site.css: a 40rem o último cartão da .grid-5 ocupa a linha toda")
    desktop = re.search(r"@media \(min-width: 60rem\) \{\n(.*?)\n\}", css, re.S)
    body = desktop.group(1) if desktop else ""
    check("grid-template-columns: repeat(6, 1fr)" in body and "span 2" in body and "span 3" in body,
          "site.css: a 60rem a .grid-5 usa 6 colunas, 3 cartões em cima (span 2) e 2 em baixo (span 3)")


# Caso de estudo Get It Vac (#53): página nova, cartões em Projetos e no Início, imagens AVIF/WebP (#34).
GET_IT_VAC = {"pt-PT": "/produtos/get-it-vac/", "en": "/en/products/get-it-vac/"}
PRODUCTS = {"pt-PT": "/produtos/", "en": "/en/products/"}
CONTACT = {"pt-PT": "/contacto/", "en": "/en/contact/"}
# Igual em PT e EN. "unofficial stand": nada sugere ligação oficial ao Web Summit.
GET_IT_VAC_TAG = "Caso de estudo · Web Summit Lisboa 2026 (unofficial stand)"
# Botão "Jogar": muda para /home quando a landing estiver no ar (#54), aqui e nos conteúdos.
GET_IT_VAC_PLAY = "https://vac.navego.pt"
GET_IT_VAC_BUTTONS = {"pt-PT": ("Jogar o Get It Vac", "Quer um jogo para o seu evento?"),
                      "en": ("Play Get It Vac", "Want a game for your event?")}
GET_IT_VAC_OG = "/assets/og-get-it-vac.png"
GET_IT_VAC_NUMBERS = ["122", "67", "18", "13", "19", "80 s"]
# Fica de fora: o repositório e planos futuros.
GET_IT_VAC_OUT = re.compile(r"github|repositório|repository|roadmap|planos futuros|future plans|\boficial\b|\bofficial\b", re.I)
IMG_DIR = "/assets/img/"


def image_size(path):
    """Largura e altura de um WebP (VP8, VP8L, VP8X) ou AVIF (caixa ispe), sem bibliotecas."""
    data = path.read_bytes()
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        chunk = data[12:16]
        if chunk == b"VP8X":
            return 1 + int.from_bytes(data[24:27], "little"), 1 + int.from_bytes(data[27:30], "little")
        if chunk == b"VP8 ":
            return int.from_bytes(data[26:28], "little") & 0x3FFF, int.from_bytes(data[28:30], "little") & 0x3FFF
        if chunk == b"VP8L":
            b = int.from_bytes(data[21:25], "little")
            return 1 + (b & 0x3FFF), 1 + ((b >> 14) & 0x3FFF)
    i = data.find(b"ispe")
    if i != -1:
        return int.from_bytes(data[i + 8:i + 12], "big"), int.from_bytes(data[i + 12:i + 16], "big")
    return None


def check_pictures(check, url, html, hero_first):
    """Cada <picture>: AVIF e WebP com 3 larguras que existem, img com alt, width, height e lazy (menos o hero).

    Nenhuma largura passa o dobro do maior tamanho em rem do sizes (ecrãs 2x)."""
    pics = re.findall(r"<picture\b[^>]*>(.*?)</picture>", html, re.S)
    for n, pic in enumerate(pics):
        sources = re.findall(r'<source type="([^"]+)" srcset="([^"]+)" sizes="([^"]+)">', pic)
        check([t for t, _, _ in sources] == ["image/avif", "image/webp"], f"{url}: <picture> {n + 1} sem AVIF e WebP, por esta ordem")
        img = re.search(r"<img\b([^>]*)>", pic)
        check(img is not None, f"{url}: <picture> {n + 1} sem <img>")
        if not sources or img is None:
            continue
        attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', img.group(1)))
        check(attrs.get("alt", "").strip(), f"{url}: <img> {n + 1} sem alt")
        w, h = int(attrs.get("width", 0)), int(attrs.get("height", 0))
        check(w and h, f"{url}: <img> {n + 1} sem width e height")
        check(attrs.get("src", "").startswith(IMG_DIR) and attrs["src"].endswith(".webp"),
              f"{url}: <img> {n + 1} com src fora de {IMG_DIR} ou sem WebP")
        if n == 0 and hero_first:
            check("loading" not in attrs and attrs.get("fetchpriority") == "high",
                  f"{url}: a imagem do hero carrega logo (sem lazy, fetchpriority=high)")
        else:
            check(attrs.get("loading") == "lazy" and attrs.get("decoding") == "async",
                  f"{url}: <img> {n + 1} precisa de loading=lazy e decoding=async")
        for kind, srcset, sizes in sources:
            ext = {"image/avif": ".avif", "image/webp": ".webp"}.get(kind, "?")
            entries = [e.strip().rsplit(" ", 1) for e in srcset.split(",")]
            check(len(entries) == 3, f"{url}: srcset {kind} com {len(entries)} larguras (devem ser 3)")
            cap = max((float(x) for x in re.findall(r"([\d.]+)rem\)?(?:,|$)", sizes)), default=0) * 16 * 2
            for src, desc in entries:
                f = file_for(src)
                check(src.startswith(IMG_DIR) and src.endswith(ext) and f.exists(), f"{url}: imagem em falta {src}")
                if not f.exists() or not desc.endswith("w"):
                    continue
                size = image_size(f)
                check(size is not None and size[0] == int(desc[:-1]), f"{url}: {src} não tem {desc} de largura ({size})")
                if size and w and h:
                    check(abs(size[1] - round(size[0] * h / w)) <= 1, f"{url}: {src} com proporção diferente de {w}x{h}")
                check(cap and int(desc[:-1]) <= cap, f"{url}: {src} maior do que o dobro do tamanho mostrado ({sizes})")


def check_get_it_vac(check, url, html, lang, page):
    main = html[html.index("<main"):html.index("</main>")]
    case, products = GET_IT_VAC[lang], PRODUCTS[lang]
    home = "/" if lang == "pt-PT" else "/en/"
    if url in (case, products, home):
        # A parte noutra língua leva lang (WCAG 3.1.2): o texto visível é igual em PT e EN.
        other = '<span lang="en">unofficial stand</span>' if lang == "pt-PT" else '<span lang="pt-PT">Caso de estudo</span>'
        check(GET_IT_VAC_TAG in re.sub(r"<[^>]+>", "", main), f"{url}: falta a etiqueta '{GET_IT_VAC_TAG}'")
        check(other in main, f"{url}: a etiqueta precisa de {other}")
    if url in (products, home):
        check(f'href="{case}"' in main, f"{url}: falta o cartão com link para {case}")
        cards = re.findall(r'<li class="card card-project">(.*?)</li>\n', main, re.S)
        check(len(cards) == 2 and VIZIA in cards[0] and "Get It Vac" in cards[1],
              f"{url}: Vizia e depois Get It Vac, lado a lado em cartões .card-project")
        check_pictures(check, url, main, False)
    if url != case:
        return
    play, event = GET_IT_VAC_BUTTONS[lang]
    check(re.search(rf'<a class="btn btn-primary" href="{re.escape(GET_IT_VAC_PLAY)}" target="_blank" rel="noopener noreferrer">{play}</a>', main),
          f"{url}: falta o botão '{play}' para {GET_IT_VAC_PLAY}")
    check(f'href="{CONTACT[lang]}">{event}</a>' in main, f"{url}: falta o botão '{event}' para {CONTACT[lang]}")
    check(re.search(rf'<a href="{products}"[^>]*aria-current="true"', html), f"{url}: Projetos marcado como secção atual no menu")
    crumb = re.search(r'<nav class="breadcrumb" aria-label="[^"]+">(.*?)</nav>', main, re.S)
    check(crumb is not None and f'href="{products}"' in crumb.group(1) and 'aria-current="page"' in crumb.group(1),
          f"{url}: falta o breadcrumb com link para {products} e a página atual")
    text = " ".join(re.sub(r"<[^>]+>", " ", main.replace("(unofficial stand)", "")).split())
    m = GET_IT_VAC_OUT.search(text)
    check(not m, f"{url}: '{m.group(0) if m else ''}' fica de fora da página")
    for number in GET_IT_VAC_NUMBERS:
        check(number in text, f"{url}: falta o resultado '{number}'")
    check(page.meta.get("og:image") == SITE + GET_IT_VAC_OG, f"{url}: og:image deve ser {GET_IT_VAC_OG}")
    check(len(re.findall(r"<picture\b", main)) == 5, f"{url}: hero, comando, multijogador, selfie e cartaz (5 imagens)")
    check_pictures(check, url, main, True)


def check_privacy_links(check, pages_raw):
    for privacy in ("/privacidade/", "/en/privacy/"):
        raw = pages_raw.get(privacy, "")
        others = re.search(r'id="(?:outros-sites|other-sites)">.*?</h2>\s*<p>(.*?)</p>', raw, re.S)
        check(others is not None and f'href="{GET_IT_VAC_PLAY}"' in others.group(1) and "Get It Vac" in others.group(1),
              f"{privacy}: o Get It Vac tem de estar em 'Outros sites'")


def main():
    errors = []

    def check(cond, msg):
        if not cond:
            errors.append(msg)

    check_tokens(check)
    check_content(check)
    check_no_js_hiding(check)
    check_motion_css(check)
    check_icons(check)
    check_footer_css(check)
    check_finish(check)
    check_hero_desktop(check)
    check_cookie_banner_css(check)
    check_consent_js(check)
    check_grid5_css(check)

    titles, descriptions = {}, {}
    pages, pages_raw = {}, {}
    for pt, en in PAGES:
        for url in (pt, en):
            f = file_for(url)
            check(f.exists(), f"{url}: ficheiro em falta ({f.relative_to(ROOT.parent)})")
            if f.exists():
                pages[url] = parse(f)

    for pt, en in PAGES:
        for url, lang, other in ((pt, "pt-PT", en), (en, "en", pt)):
            p = pages.get(url)
            if not p:
                continue
            check(p.lang == lang, f"{url}: lang deve ser {lang}, é {p.lang}")
            check(p.title.strip(), f"{url}: <title> vazio")
            check(p.meta.get("description"), f"{url}: meta description em falta")
            check(p.h1 == 1, f"{url}: deve ter um <h1>, tem {p.h1}")
            for og in ("og:title", "og:description", "og:url", "og:type", "og:locale", "og:site_name"):
                check(p.meta.get(og), f"{url}: {og} em falta")
            check(p.meta.get("og:url") == SITE + url, f"{url}: og:url deve ser {SITE + url}")
            og_image = p.meta.get("og:image", "")
            check(og_image.startswith(SITE + "/") and file_for(og_image[len(SITE):]).exists(),
                  f"{url}: og:image em falta ou ficheiro inexistente ({og_image})")
            check(p.meta.get("og:image:width") == "1200" and p.meta.get("og:image:height") == "630",
                  f"{url}: og:image deve declarar 1200x630")
            check(p.meta.get("og:image:alt"), f"{url}: og:image:alt em falta")
            check(p.meta.get("twitter:card") == "summary_large_image", f"{url}: twitter:card em falta")
            links = {(rel, hl): href for rel, href, hl in p.links}
            check(links.get(("canonical", None)) == SITE + url, f"{url}: canonical deve ser {SITE + url}")
            check(links.get(("alternate", "pt-PT")) == SITE + pt, f"{url}: hreflang pt-PT em falta")
            check(links.get(("alternate", "en")) == SITE + en, f"{url}: hreflang en em falta")
            check(links.get(("alternate", "x-default")) == SITE + pt, f"{url}: hreflang x-default em falta")
            check(any(rel == "icon" and (ROOT / h.lstrip("/")).exists() for rel, h, _ in p.links),
                  f"{url}: favicon em falta")
            sheets = [h.split("?")[0] for rel, h, _ in p.links if rel == "stylesheet"]
            check(sheets[:2] == ["/assets/css/tokens.css", "/assets/site.css"],
                  f"{url}: tokens.css tem de vir antes do site.css ({sheets})")
            check(any(rel == "preload" and h == FONT_PRELOAD for rel, h, _ in p.links),
                  f"{url}: sem preload de {FONT_PRELOAD}")
            check_header(check, url, p)
            check_labels(check, url, p)
            check_hero(check, url, p, url in ("/", "/en/"), lang)
            check_marquee(check, url, p, lang, url in ("/", "/en/"))
            check_scenes(check, url, p)
            raw = file_for(url).read_text(encoding="utf-8")
            check_cta(check, url, raw, lang, "telha" in [sc for sc, _ in p.scenes])
            check_footer(check, url, raw, lang)
            check_lang_link(check, url, raw, lang)
            check_ficha(check, url, raw, lang, url in ("/sobre/", "/en/about/"))
            if url in ("/", "/en/"):
                check_more_links(check, url, raw, lang)
            check_vizia(check, url, raw)
            check_consent_html(check, url, raw, lang)
            check_positioning(check, url, raw, lang, url in ("/", "/en/"), url in ("/sobre/", "/en/about/"),
                              url in ("/servicos/", "/en/services/"))
            check_get_it_vac(check, url, raw, lang, p)
            pages_raw[url] = raw
            check_page_icons(check, url, p, raw, url in ("/", "/en/"), url in ("/servicos/", "/en/services/"))
            if url in ("/", "/en/"):
                check(section_labels(raw) == HOME_LABELS[lang], f"{url}: etiquetas {section_labels(raw)}, esperado {HOME_LABELS[lang]}")
                about = "/sobre/" if lang == "pt-PT" else "/en/about/"
                main = raw[raw.index("<main"):raw.index("</main>")]
                check(f'href="{about}"' in main, f"{url}: a secção Sobre precisa de ligação para {about} no conteúdo")
            check(any(h == other for h, _, _ in p.hrefs), f"{url}: sem link para a outra língua ({other})")
            footer = " ".join(" ".join(p.footer_text).split())
            for needle in LEGAL_FOOTER[lang]:
                check(needle in footer, f"{url}: rodapé sem '{needle}'")
            check(any(h == COMPLAINTS_URL for h, _, _ in p.footer_hrefs),
                  f"{url}: rodapé sem link para o Livro de Reclamações ({COMPLAINTS_URL})")
            check(COMPLAINTS_LABEL[lang] in footer, f"{url}: rodapé sem '{COMPLAINTS_LABEL[lang]}'")
            privacy, terms = ("/privacidade/", "/termos/") if lang == "pt-PT" else ("/en/privacy/", "/en/terms/")
            check(any(h == privacy for h, _, _ in p.hrefs), f"{url}: sem link para {privacy}")
            check(any(h == terms for h, _, _ in p.hrefs), f"{url}: sem link para {terms}")
            body = " ".join(p.text)
            m = FORBIDDEN.search(body)
            check(not m, f"{url}: texto proibido '{m.group(0) if m else ''}'")
            titles.setdefault(p.title.strip(), []).append(url)
            descriptions.setdefault(p.meta.get("description"), []).append(url)

    for pt, en in PAGES:
        if pt in pages and en in pages:
            check(pages[pt].skeleton == pages[en].skeleton, f"{pt} e {en}: HTML diferente entre PT e EN")

    for t, urls in titles.items():
        check(len(urls) == 1, f"<title> repetido em {urls}")
    for d, urls in descriptions.items():
        check(len(urls) == 1, f"meta description repetida em {urls}")

    check_cookie_policy(check, pages_raw)
    check_privacy_links(check, pages_raw)

    # 404
    f404 = ROOT / "404.html"
    check(f404.exists(), "404.html em falta")
    if f404.exists():
        p = parse(f404)
        check("noindex" in p.meta.get("robots", ""), "404.html: deve ter robots noindex")
        check(any(h == "/" for h, _, _ in p.hrefs), "404.html: sem link para o início")
        check(any(h == COMPLAINTS_URL for h, _, _ in p.footer_hrefs),
              "404.html: rodapé sem link para o Livro de Reclamações")
        sheets = [h.split("?")[0] for rel, h, _ in p.links if rel == "stylesheet"]
        check(sheets[:2] == ["/assets/css/tokens.css", "/assets/site.css"],
              f"404.html: tokens.css tem de vir antes do site.css ({sheets})")
        check_header(check, "404.html", p)
        check_footer(check, "404.html", f404.read_text(encoding="utf-8"), "pt-PT")
        pages["/404.html"] = p

    # Links internos e externos em todas as páginas
    for url, p in pages.items():
        for href, target, rel in p.hrefs:
            u = urlparse(href)
            if u.scheme in ("mailto", "tel"):
                continue
            if u.scheme in ("http", "https"):
                if u.netloc in ("thr33.xyz", "www.thr33.xyz"):
                    check(file_for(u.path or "/").exists(), f"{url}: link interno partido {href}")
                if target == "_blank":
                    check("noopener" in rel and "noreferrer" in rel, f"{url}: {href} sem rel noopener noreferrer")
                continue
            if href.startswith("#"):
                check(href[1:] in p.ids, f"{url}: âncora {href} não existe")
                continue
            check(href.startswith("/"), f"{url}: link relativo {href} (usar caminho absoluto)")
            check(file_for(href).exists(), f"{url}: link interno partido {href}")
            if "#" in href:
                anchor = href.split("#", 1)[1]
                target_page = pages.get(href.split("#")[0])
                check(target_page is None or anchor in target_page.ids, f"{url}: âncora {href} não existe")
        for rel, href, _ in p.links:
            if href.startswith("/"):
                check(file_for(href).exists(), f"{url}: <link> partido {href}")
        for src in p.srcs:
            check(src.startswith("/") and file_for(src).exists(), f"{url}: recurso em falta {src}")

    # Sem pedidos a terceiros (fontes, scripts, analytics)
    for f in ROOT.rglob("*.html"):
        html = f.read_text(encoding="utf-8")
        check_versions(check, str(f.relative_to(ROOT)), html)
        for host in ("fonts.googleapis.com", "fonts.gstatic.com", "googletagmanager", "google-analytics", "facebook.net"):
            check(host not in html, f"{f.relative_to(ROOT)}: pedido a terceiros ({host})")
        check(GA_ID.split("-", 1)[1] not in html, f"{f.relative_to(ROOT)}: o ID do GA não aparece no HTML, só no {CONSENT_JS}")
        # A CSP em docs/deploy.md não permite estilos nem scripts inline.
        for pattern in (r"\sstyle=", r"<style", r"<script(?![^>]*\bsrc=)", r"\son[a-z]+="):
            check(not re.search(pattern, html), f"{f.relative_to(ROOT)}: inline proibido pela CSP ({pattern})")

    # robots.txt e sitemap.xml
    robots = ROOT / "robots.txt"
    check(robots.exists() and f"Sitemap: {SITE}/sitemap.xml" in robots.read_text(), "robots.txt sem Sitemap")
    sitemap = ROOT / "sitemap.xml"
    check(sitemap.exists(), "sitemap.xml em falta")
    if sitemap.exists():
        xml = sitemap.read_text()
        for pt, en in PAGES:
            for url in (pt, en):
                check(f"<loc>{SITE}{url}</loc>" in xml, f"sitemap.xml sem {url}")

    if errors:
        print(f"✗ {len(errors)} problema(s):")
        for e in errors:
            print("  -", e)
        sys.exit(1)
    print(f"✓ {len(pages)} páginas verificadas, sem problemas.")


if __name__ == "__main__":
    main()
