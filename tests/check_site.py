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
        elif tag in ("img", "script"):
            if a.get("src"):
                self.srcs.append(a["src"])
        elif tag == "h1":
            self.h1 += 1
        elif tag == "footer":
            self._in_footer += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "footer":
            self._in_footer -= 1

    def handle_data(self, data):
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


def main():
    errors = []

    def check(cond, msg):
        if not cond:
            errors.append(msg)

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
            links = {(rel, hl): href for rel, href, hl in p.links}
            check(links.get(("canonical", None)) == SITE + url, f"{url}: canonical deve ser {SITE + url}")
            check(links.get(("alternate", "pt-PT")) == SITE + pt, f"{url}: hreflang pt-PT em falta")
            check(links.get(("alternate", "en")) == SITE + en, f"{url}: hreflang en em falta")
            check(links.get(("alternate", "x-default")) == SITE + pt, f"{url}: hreflang x-default em falta")
            check(any(rel == "icon" and (ROOT / h.lstrip("/")).exists() for rel, h, _ in p.links),
                  f"{url}: favicon em falta")
            check(any(h == other for h, _, _ in p.hrefs), f"{url}: sem link para a outra língua ({other})")
            footer = " ".join(" ".join(p.footer_text).split())
            for needle in LEGAL_FOOTER[lang]:
                check(needle in footer, f"{url}: rodapé sem '{needle}'")
            privacy, terms = ("/privacidade/", "/termos/") if lang == "pt-PT" else ("/en/privacy/", "/en/terms/")
            check(any(h == privacy for h, _, _ in p.hrefs), f"{url}: sem link para {privacy}")
            check(any(h == terms for h, _, _ in p.hrefs), f"{url}: sem link para {terms}")
            body = " ".join(p.text)
            m = FORBIDDEN.search(body)
            check(not m, f"{url}: texto proibido '{m.group(0) if m else ''}'")
            titles.setdefault(p.title.strip(), []).append(url)
            descriptions.setdefault(p.meta.get("description"), []).append(url)

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
