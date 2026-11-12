"""Gera o site estático em public/ a partir de src/.

Corre com: python3 scripts/build.py
Cada página em src/pages/<pt|en>/<nome>.html começa com um cabeçalho:

    <!--
    title: Título da página
    description: Descrição para pesquisa e partilha
    -->

O resto do ficheiro é o conteúdo de <main>.
"""
import re
from datetime import date
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SRC = BASE / "src"
OUT = BASE / "public"
SITE = "https://thr33.xyz"

# nome do ficheiro → (URL PT, URL EN)
ROUTES = {
    "inicio": ("/", "/en/"),
    "sobre": ("/sobre/", "/en/about/"),
    "servicos": ("/servicos/", "/en/services/"),
    "produtos": ("/produtos/", "/en/products/"),
    "contacto": ("/contacto/", "/en/contact/"),
    "privacidade": ("/privacidade/", "/en/privacy/"),
    "termos": ("/termos/", "/en/terms/"),
}

NAV = ["servicos", "produtos", "sobre", "contacto"]

LANGS = {
    "pt": {
        "html_lang": "pt-PT",
        "og_locale": "pt_PT",
        "og_image_alt": "Thr33 Labs, estúdio de produto digital",
        "other_label": "EN",
        "other_name": "English",
        "nav_label": "Navegação principal",
        "skip": "Saltar para o conteúdo",
        "nav": {"servicos": "Serviços", "produtos": "Produtos", "sobre": "Sobre", "contacto": "Contacto",
                "privacidade": "Privacidade", "termos": "Termos de utilização", "inicio": "Início"},
        "tagline": "Estúdio de produto digital em Óbidos, Portugal.",
        "footer_nav": "Ligações do rodapé",
        "contact_heading": "Contacto",
        "pages_heading": "Páginas",
        "legal": ("THR33XYZ LABS - TECNOLOGIA E CONSULTORIA, UNIPESSOAL LDA · Sociedade unipessoal por quotas · "
                  "Sede: Beco da Serra, 2, Sobral da Lagoa, 2510-651 Óbidos · Conservatória do Registo Comercial (RNPC) · "
                  "Matrícula e NIPC 519573021 · Capital social 7.660,00 €"),
    },
    "en": {
        "html_lang": "en",
        "og_locale": "en_GB",
        "og_image_alt": "Thr33 Labs, digital product studio",
        "other_label": "PT",
        "other_name": "Português",
        "nav_label": "Main navigation",
        "skip": "Skip to content",
        "nav": {"servicos": "Services", "produtos": "Products", "sobre": "About", "contacto": "Contact",
                "privacidade": "Privacy", "termos": "Terms of use", "inicio": "Home"},
        "tagline": "Digital product studio in Óbidos, Portugal.",
        "footer_nav": "Footer links",
        "contact_heading": "Contact",
        "pages_heading": "Pages",
        "legal": ("THR33XYZ LABS - TECNOLOGIA E CONSULTORIA, UNIPESSOAL LDA · A single-member private limited company "
                  "(sociedade unipessoal por quotas) · Registered office: Beco da Serra, 2, Sobral da Lagoa, 2510-651 Óbidos, Portugal · "
                  "Portuguese Commercial Registry (RNPC) · Registration and tax number (NIPC) 519573021 · Share capital €7,660.00"),
    },
}

HEADER_RE = re.compile(r"\A<!--\s*\n(.*?)\n-->\s*\n", re.S)


def read_page(lang, name):
    raw = (SRC / "pages" / lang / f"{name}.html").read_text(encoding="utf-8")
    m = HEADER_RE.match(raw)
    if not m:
        raise SystemExit(f"src/pages/{lang}/{name}.html: falta o cabeçalho com title e description")
    meta = dict(line.split(": ", 1) for line in m.group(1).strip().splitlines())
    return meta, raw[m.end():]


def url_for(lang, name):
    return ROUTES[name][0 if lang == "pt" else 1]


def render_nav(lang, current):
    t = LANGS[lang]
    items = []
    for name in NAV:
        aria = ' aria-current="page"' if name == current else ""
        items.append(f'<li><a href="{url_for(lang, name)}"{aria}>{t["nav"][name]}</a></li>')
    return "\n          ".join(items)


def render(lang, name, layout):
    t = LANGS[lang]
    other = "en" if lang == "pt" else "pt"
    meta, body = read_page(lang, name)
    url = url_for(lang, name)
    pt_url, en_url = ROUTES[name]
    footer_links = "\n            ".join(
        f'<li><a href="{url_for(lang, n)}">{t["nav"][n]}</a></li>' for n in NAV + ["privacidade", "termos"]
    )
    values = {
        "html_lang": t["html_lang"],
        "title": meta["title"],
        "description": meta["description"],
        "canonical": SITE + url,
        "alt_pt": SITE + pt_url,
        "alt_en": SITE + en_url,
        "og_locale": t["og_locale"],
        "og_locale_alt": LANGS[other]["og_locale"],
        "og_image_alt": t["og_image_alt"],
        "skip": t["skip"],
        "home": url_for(lang, "inicio"),
        "nav_label": t["nav_label"],
        "nav": render_nav(lang, name),
        "other_url": url_for(other, name),
        "other_label": t["other_label"],
        "other_name": t["other_name"],
        "other_lang": LANGS[other]["html_lang"],
        "main": body.rstrip(),
        "tagline": t["tagline"],
        "footer_nav": t["footer_nav"],
        "pages_heading": t["pages_heading"],
        "footer_links": footer_links,
        "contact_heading": t["contact_heading"],
        "legal": t["legal"],
        "year": str(date.today().year),
    }
    html = layout
    for key, value in values.items():
        html = html.replace("{{" + key + "}}", value)
    leftover = re.findall(r"\{\{\w+\}\}", html)
    if leftover:
        raise SystemExit(f"{lang}/{name}: marcadores por preencher {leftover}")
    target = OUT / url.lstrip("/") / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8")
    return url


def write_sitemap(urls):
    entries = []
    for pt_url, en_url in ROUTES.values():
        for url in (pt_url, en_url):
            entries.append(
                "  <url>\n"
                f"    <loc>{SITE}{url}</loc>\n"
                f'    <xhtml:link rel="alternate" hreflang="pt-PT" href="{SITE}{pt_url}"/>\n'
                f'    <xhtml:link rel="alternate" hreflang="en" href="{SITE}{en_url}"/>\n'
                f'    <xhtml:link rel="alternate" hreflang="x-default" href="{SITE}{pt_url}"/>\n'
                "  </url>"
            )
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        + "\n".join(entries)
        + "\n</urlset>\n",
        encoding="utf-8",
    )


def main():
    layout = (SRC / "layout.html").read_text(encoding="utf-8")
    urls = [render(lang, name, layout) for lang in ("pt", "en") for name in ROUTES]
    write_sitemap(urls)
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n", encoding="utf-8")
    print(f"{len(urls)} páginas geradas em public/")


if __name__ == "__main__":
    main()
