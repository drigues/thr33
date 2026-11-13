"""Verificação do site estático em public/.

Corre com: python3 tests/check_site.py
Sai com código 1 se alguma regra falhar.
"""
import re
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
HERO_LABEL = "(Thr33 Labs / ©2026) Óbidos, PT"
HERO_BLOBS = 3
SITE_JS_MAX_BYTES = 8192  # orçamento total de JS da spec: 70 KB gzip; o site.js fica muito abaixo

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
        if tag == "section" and "hero" in classes:
            self._in_hero = 1
        if "hero-gradient" in classes:
            self.hero_gradient.append(a)
        if "blob" in classes:
            self.blobs += 1
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
        if tag in ("span", "p"):
            self._capture = None
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
    m = re.search(selector_re + r"\s*\{([^{}]*)\}", css)
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

    schemes = {"claro": light}
    if dark_media:
        schemes["escuro"] = {**light, **css_vars(dark_media.group(1))}
    if ink_section is not None:
        schemes[".theme-ink"] = {**light, **css_vars(ink_section)}
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
    check(sum(1 for s in p.scripts if s.get("src") == SITE_JS) == 1, f"{url}: sem {SITE_JS}")


def check_hero(check, url, p, is_home):
    check(all("data-split" in a for a in p.h1_attrs), f"{url}: o <h1> deve ter data-split (reveal por linhas)")
    if not is_home:
        check(not p.hero_gradient, f"{url}: o gradiente-assinatura é só da página inicial")
        return
    check(p.hero_labels == [HERO_LABEL], f"{url}: etiqueta do hero deve ser '{HERO_LABEL}', é {p.hero_labels}")
    check(len(p.hero_gradient) == 1 and p.hero_gradient[0].get("aria-hidden") == "true",
          f"{url}: falta o .hero-gradient com aria-hidden=true")
    check(p.blobs == HERO_BLOBS, f"{url}: o gradiente deve ter {HERO_BLOBS} manchas, tem {p.blobs}")
    check(len(p.scroll_hints) == 1, f"{url}: falta a indicação ↓ scroll (.hero-scroll)")


def check_motion_css(check):
    css = (ROOT / "assets" / "site.css").read_text(encoding="utf-8")
    reduced = re.search(r"@media\s*\(prefers-reduced-motion:\s*reduce\)\s*\{(.*?)\n\}", css, re.S)
    check(reduced is not None, "site.css: bloco prefers-reduced-motion em falta")
    if reduced:
        for needle in (".blob", ".wi"):
            check(needle in reduced.group(1), f"site.css: prefers-reduced-motion não trata {needle}")
    # Se o JS falhar depois de pôr .js, o título não pode ficar invisível para sempre.
    guard = re.search(r"\.js \[data-split\]:not\(\.split\)\s*\{([^}]*)\}", css)
    check(guard is not None and "animation" in guard.group(1),
          "site.css: falta a salvaguarda .js [data-split]:not(.split) com animation")


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
                ok = sel.startswith(".js ") or sel.startswith("html:not(.js)") or sel.startswith("[hidden]")
                check(ok, f"site.css: '{sel}' esconde conteúdo sem depender de .js")
    js = ROOT / SITE_JS.lstrip("/")
    check(js.exists(), f"{SITE_JS} em falta")
    if js.exists():
        check(js.stat().st_size <= SITE_JS_MAX_BYTES, f"{SITE_JS} tem {js.stat().st_size} bytes (máx. {SITE_JS_MAX_BYTES})")


def main():
    errors = []

    def check(cond, msg):
        if not cond:
            errors.append(msg)

    check_tokens(check)
    check_content(check)
    check_no_js_hiding(check)
    check_motion_css(check)

    titles, descriptions = {}, {}
    pages = {}
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
            sheets = [h for rel, h, _ in p.links if rel == "stylesheet"]
            check(sheets[:2] == ["/assets/css/tokens.css", "/assets/site.css"],
                  f"{url}: tokens.css tem de vir antes do site.css ({sheets})")
            check(any(rel == "preload" and h == FONT_PRELOAD for rel, h, _ in p.links),
                  f"{url}: sem preload de {FONT_PRELOAD}")
            check_header(check, url, p)
            check_labels(check, url, p)
            check_hero(check, url, p, url in ("/", "/en/"))
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

    # 404
    f404 = ROOT / "404.html"
    check(f404.exists(), "404.html em falta")
    if f404.exists():
        p = parse(f404)
        check("noindex" in p.meta.get("robots", ""), "404.html: deve ter robots noindex")
        check(any(h == "/" for h, _, _ in p.hrefs), "404.html: sem link para o início")
        check(any(h == COMPLAINTS_URL for h, _, _ in p.footer_hrefs),
              "404.html: rodapé sem link para o Livro de Reclamações")
        sheets = [h for rel, h, _ in p.links if rel == "stylesheet"]
        check(sheets[:2] == ["/assets/css/tokens.css", "/assets/site.css"],
              f"404.html: tokens.css tem de vir antes do site.css ({sheets})")
        check_header(check, "404.html", p)
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
        for host in ("fonts.googleapis.com", "fonts.gstatic.com", "googletagmanager", "google-analytics", "facebook.net"):
            check(host not in html, f"{f.relative_to(ROOT)}: pedido a terceiros ({host})")
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
