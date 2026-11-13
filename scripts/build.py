"""Gera o site estático em public/ a partir de src/.

Corre com: python3 scripts/build.py

- src/content/<pt|en>.json: todos os textos de cada língua (menu, rodapé, páginas, 404).
  Os textos são HTML de confiança: podem ter <a>, <strong>, <span class="accent">, <br>.
- src/layout.html: esqueleto da página; o resto sai dos componentes abaixo.

Cada página é uma cabeça (hero ou page) seguida de secções. Cada secção tem um "type"
(cards, ticks, project, steps, services, split, facts, prose, text, cta) e, se tiver
"label", leva uma etiqueta numerada (01), (02)… pela ordem em que aparece.
"""
import json
import re
from datetime import date
from html import escape
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SRC = BASE / "src"
OUT = BASE / "public"
SITE = "https://thr33.xyz"

# nome da página → (URL PT, URL EN)
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
COMPLAINTS_URL = "https://www.livroreclamacoes.pt/Inicio/"
EMAIL = "hello@thr33.xyz"


# O <use> não herda os atributos do <svg> raiz do sprite: vão em cada <symbol>.
ICON_PAINT = 'fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"'
ICON_SHAPES = re.compile(r"<(path|circle|rect|line|polyline|polygon|ellipse)\b([^>]*?)\s*/>")


def write_icons():
    """Sprite com os ícones Lucide (ISC) de src/icons/: um <symbol> por ficheiro, traço 1.5 px.

    Cada forma leva pathLength="1" para o traço se poder desenhar com stroke-dashoffset.
    """
    symbols = []
    for f in sorted((SRC / "icons").glob("*.svg")):
        svg = f.read_text(encoding="utf-8")
        view_box = re.search(r'viewBox="([^"]+)"', svg).group(1)
        shapes = "".join(f'<{tag}{attrs} pathLength="1"/>' for tag, attrs in ICON_SHAPES.findall(svg))
        symbols.append(f'<symbol id="{f.stem}" viewBox="{view_box}" {ICON_PAINT}>{shapes}</symbol>')
    sprite = '<svg xmlns="http://www.w3.org/2000/svg">\n' + "\n".join(symbols) + "\n</svg>\n"
    (OUT / "assets" / "icons.svg").write_text(sprite, encoding="utf-8")
    licence = (SRC / "icons" / "LICENSE-lucide.txt").read_text(encoding="utf-8")
    (OUT / "assets" / "icons-LICENSE.txt").write_text(licence, encoding="utf-8")


def icon(name):
    """Ícone decorativo do sprite, dentro de um círculo na cor da secção."""
    return (f'<span class="card-icon" aria-hidden="true"><svg class="icon" width="24" height="24" '
            f'aria-hidden="true" focusable="false"><use href="/assets/icons.svg#{name}"></use></svg></span>')


def load_content(lang):
    return json.loads((SRC / "content" / f"{lang}.json").read_text(encoding="utf-8"))


def url_for(lang, name):
    return ROUTES[name][0 if lang == "pt" else 1]


def attr(value):
    return escape(value, quote=True)


# ---------------------------------------------------------------- componentes

def label(text=None, num=None, page=False):
    """Etiqueta em mono: (01) Serviços numa secção, (Serviços) na cabeça de página."""
    if page:
        return f'<p class="label">({text})</p>'
    num_html = f'<span class="label-num">({num:02d})</span>'
    return f'<p class="label">{num_html} {text}</p>' if text else f'<p class="label">{num_html}</p>'


def button(action):
    external = ' target="_blank" rel="noopener noreferrer"' if action.get("external") else ""
    return f'<a class="btn btn-{action["style"]}" href="{attr(action["href"])}"{external}>{action["text"]}</a>'


def actions(items):
    if not items:
        return ""
    return '<div class="actions">\n          ' + "\n          ".join(button(a) for a in items) + "\n        </div>"


def ticks(items):
    lis = "\n          ".join(f"<li>{i}</li>" for i in items)
    return f'<ul class="ticks">\n          {lis}\n        </ul>'


def card(item, num=None):
    parts = [f'<h3>{item["title"]}</h3>']
    if "icon" in item:
        parts = [icon(item["icon"]), f'<span class="num">{num:02d}</span>'] + parts
    if "text" in item:
        parts.append(f'<p>{item["text"]}</p>')
    if "address" in item:
        parts.append(f'<address class="dim">{item["address"]}</address>')
    if "link" in item:
        parts.append(f'<a class="more" href="{attr(item["link"]["href"])}">{item["link"]["text"]}</a>')
    cls = "card card-service" if "icon" in item else "card"
    return f'<li class="{cls}">\n            ' + "\n            ".join(parts) + "\n          </li>"


def cards(section):
    items = "\n          ".join(card(i, n) for n, i in enumerate(section["items"], 1))
    reveal = " data-reveal" if any("icon" in i for i in section["items"]) else ""
    return f'<ul class="grid grid-{section["columns"]}"{reveal}>\n          {items}\n        </ul>'


def steps(section):
    items = "\n          ".join(
        f'<li class="card card-step">\n            {icon(i["icon"])}\n            <span class="num">{n:02d}</span>'
        f'<h3>{i["title"]}</h3><p>{i["text"]}</p>\n          </li>'
        for n, i in enumerate(section["items"], 1)
    )
    return f'<ol class="grid grid-4" role="list" data-reveal>\n          {items}\n        </ol>'


def facts(section):
    rows = "\n          ".join(f'<div><dt>{i["term"]}</dt><dd>{i["value"]}</dd></div>' for i in section["items"])
    html = f'<dl class="facts">\n          {rows}\n        </dl>'
    if "note" in section:
        html += f'\n        <p class="note">{section["note"]}</p>'
    return html


def project(section):
    """Linha de projeto: nome grande, descrição, ações e (opcional) lista de pontos."""
    left = [
        f'<p class="examples-title">{section["eyebrow"]}</p>',
        f'<h2 id="{section["id"]}" class="product-name">{section["h2"]}</h2>',
        f'<p class="dim">{section["text"]}</p>',
    ]
    if "ticks" in section:
        left.append(actions(section["actions"]))
        right = ticks(section["ticks"])
    else:
        right = actions(section["actions"])
    return ('<div class="product">\n        <div>\n          ' + "\n          ".join(left)
            + "\n        </div>\n        " + right + "\n      </div>")


def heading(section):
    return f'<h2 id="{section["id"]}">{section["h2"]}</h2>'


SCENES = {"project": "ink", "cta": "telha"}


def band(section, num, body):
    """Secção padrão: etiqueta numerada (se houver), título e corpo.

    Projetos veste Tinta e o CTA veste Telha (#31): classe scene-* para a cor sem JS e
    data-scene para o site.js mudar a cor da página inteira.
    """
    lab = label(section["label"], num) if num else ""
    inner = "\n        ".join(x for x in (lab, body) if x)
    scene = SCENES.get(section["type"])
    attrs = f'class="band scene-{scene}" data-scene="{scene}"' if scene else 'class="band"'
    return (f'    <section {attrs} aria-labelledby="{section["id"]}">\n'
            f'      <div class="wrap">\n        {inner}\n      </div>\n    </section>')


def services(section, counter):
    out = []
    for item in section["items"]:
        num = next(counter)
        examples = ticks(item["examples"])
        out.append(
            f'      <section class="service" id="{item["id"]}" aria-labelledby="{item["heading_id"]}" data-reveal>\n'
            f'        <div class="service-head">\n          {icon(item["icon"])}\n          {label(num=num)}\n        </div>\n'
            f'        <div class="service-grid">\n'
            f'          <div>\n            <h2 id="{item["heading_id"]}">{item["h2"]}</h2>\n'
            f'            <p>{item["text"]}</p>\n          </div>\n'
            f'          <div>\n            <p class="examples-title">{item["examples_title"]}</p>\n'
            f'            {examples}\n          </div>\n'
            f'        </div>\n      </section>'
        )
    return '    <div class="wrap">\n' + "\n\n".join(out) + "\n    </div>"


def prose(section):
    out = []
    for b in section["blocks"]:
        if "updated" in b:
            out.append(f'<p class="updated">{b["updated"]}</p>')
        elif "h2" in b:
            out.append(f'<h2 id="{b["id"]}">{b["h2"]}</h2>' if b.get("id") else f'<h2>{b["h2"]}</h2>')
        elif "h3" in b:
            out.append(f'<h3>{b["h3"]}</h3>')
        elif "p" in b:
            out.append(f'<p>{b["p"]}</p>')
        elif "ul" in b:
            out.append("<ul>\n        " + "\n        ".join(f"<li>{li}</li>" for li in b["ul"]) + "\n      </ul>")
    return '    <div class="wrap prose">\n      ' + "\n\n      ".join(out) + "\n    </div>"


def section_html(section, counter):
    kind = section["type"]
    if kind == "services":
        return services(section, counter)
    if kind == "prose":
        return prose(section)
    num = next(counter) if section.get("label") else None
    if kind == "project":
        return band(section, num, project(section))
    if kind == "split":
        paras = "\n            ".join(f"<p>{p}</p>" for p in section["paragraphs"])
        body = (f'<div class="service-grid">\n          {heading(section)}\n'
                f'          <div class="prose">\n            {paras}\n          </div>\n        </div>')
        return band(section, num, body)
    body = {
        "cards": lambda s: heading(s) + "\n        " + cards(s),
        "steps": lambda s: heading(s) + "\n        " + steps(s),
        "ticks": lambda s: heading(s) + "\n        " + ticks(s["items"]),
        "facts": lambda s: heading(s) + "\n        " + facts(s),
        "text": lambda s: "\n        ".join(x for x in (heading(s), intro(s), actions(s["actions"])) if x),
        "cta": cta,
    }[kind](section)
    return band(section, num, body)


def cta(section):
    """CTA final (#32): título em tamanho de hero (o site.js escala-o de 0.8 a 1 no scroll) e email grande."""
    title = f'<h2 class="cta-title" id="{section["id"]}" data-cta-scale>{section["h2"]}</h2>'
    email = f'<p class="cta-mail"><a class="cta-email" href="mailto:{EMAIL}">{EMAIL}</a></p>'
    return "\n        ".join(x for x in (title, intro(section), email, actions(section["actions"])) if x)


def intro(section):
    return f'<p class="band-intro">{section["text"]}</p>' if section.get("text") else ""


HERO_GRADIENT = ('<div class="hero-gradient" aria-hidden="true">'
                 '<span class="blob blob-telha"></span><span class="blob blob-lagoa"></span>'
                 '<span class="blob blob-atlantico"></span></div>')


def page_head(head):
    """Cabeça da página. O hero (página inicial) leva o gradiente-assinatura e a indicação de scroll.

    O <h1> leva data-split: o site.js parte-o em linhas para o reveal; sem JS fica como está.
    """
    is_hero = head["kind"] == "hero"
    lab = label(head["label"], page=True)
    if head.get("label_after"):
        lab = lab.replace("</p>", f' {head["label_after"]}</p>')
    parts = [lab, f'<h1 data-split>{head["h1"]}</h1>', f'<p class="lead">{head["lead"]}</p>']
    if head.get("actions"):
        parts.append(actions(head["actions"]))
    if head.get("scroll_hint"):
        parts.append(f'<p class="hero-scroll" aria-hidden="true">{head["scroll_hint"]}</p>')
    cls = "hero" if is_hero else "page-head"
    gradient = f"\n      {HERO_GRADIENT}" if is_hero else ""
    return (f'    <section class="{cls}">{gradient}\n      <div class="wrap">\n        '
            + "\n        ".join(parts) + "\n      </div>\n    </section>")


def counter_from(start=1):
    n = start
    while True:
        yield n
        n += 1


def marquee(data):
    """Competências em loop. A segunda lista só existe para o loop: aria-hidden, não é lida."""
    lis = "".join(f"<li>{i}</li>" for i in data["items"])
    return (f'    <div class="marquee" data-marquee>\n'
            f'      <div class="marquee-track">\n'
            f'        <ul class="marquee-list" aria-label="{attr(data["label"])}">{lis}</ul>\n'
            f'        <ul class="marquee-list" aria-hidden="true">{lis}</ul>\n'
            f'      </div>\n    </div>')


def main_html(page):
    counter = counter_from()
    blocks = [page_head(page["head"])]
    if "marquee" in page:
        blocks.append(marquee(page["marquee"]))
    blocks += [section_html(s, counter) for s in page["sections"]]
    return "\n\n".join(blocks)


def site_header(site, lang, current, other_url, other_lang):
    """Cabeçalho: marca à esquerda, menu numerado (01–05) com a língua no fim."""
    items = []
    for n, name in enumerate(NAV, 1):
        aria = ' aria-current="page"' if name == current else ""
        items.append(f'<li><a href="{url_for(lang, name)}"{aria}><span class="nav-num" aria-hidden="true">{n:02d}</span>'
                     f'{site["nav"][name]}</a></li>')
    items.append(f'<li><a class="lang" href="{other_url}" hreflang="{other_lang}" lang="{other_lang}" '
                 f'aria-label="{site["other_name"]}"><span class="nav-num" aria-hidden="true">05</span>'
                 f'{site["other_label"]}</a></li>')
    lis = "\n          ".join(items)
    return f'''  <header class="site-header" data-header>
    <div class="wrap header-inner">
      <a class="wordmark" href="{url_for(lang, "inicio")}">Thr33 Labs</a>
      <button class="menu-toggle" type="button" aria-expanded="false" aria-controls="menu" aria-label="{site["menu_open"]}" data-label-open="{site["menu_open"]}" data-label-close="{site["menu_close"]}">
        <span class="menu-toggle-icon" aria-hidden="true"></span>
        <span class="menu-toggle-text">{site["menu_label"]}</span>
      </button>
      <nav class="menu" id="menu" aria-label="{site["nav_label"]}">
        <ul>
          {lis}
        </ul>
      </nav>
    </div>
  </header>'''


def site_footer(site, lang):
    """Rodapé legal sucinto em duas linhas (#32). O art. 171.º do CSC pede os dados indicados
    claramente: baixa-se o peso visual da linha 2, não se esconde nada."""
    items = [
        f"© {date.today().year} Thr33 Labs",
        f'<a href="mailto:{EMAIL}">{EMAIL}</a>',
        '<a href="tel:+351936466845">+351 936 466 845</a>',
        f'<a href="{url_for(lang, "privacidade")}">{site["nav"]["privacidade"]}</a>',
        f'<a href="{url_for(lang, "termos")}">{site["nav"]["termos"]}</a>',
        f'<a href="{COMPLAINTS_URL}" target="_blank" rel="noopener noreferrer">{site["complaints"]}</a>',
    ]
    line1 = "\n        ".join(f"<li>{i}</li>" for i in items)
    return f'''  <footer class="site-footer">
    <div class="wrap">
      <ul class="footer-line">
        {line1}
      </ul>
      <p class="legal">{site["legal"]}</p>
    </div>
  </footer>'''


def head_meta(site, other_site, page, url, pt_url, en_url):
    title = attr(page["title"])
    description = attr(page["description"])
    return f'''  <meta name="description" content="{description}">
  <link rel="canonical" href="{SITE + url}">
  <link rel="alternate" hreflang="pt-PT" href="{SITE + pt_url}">
  <link rel="alternate" hreflang="en" href="{SITE + en_url}">
  <link rel="alternate" hreflang="x-default" href="{SITE + pt_url}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Thr33 Labs">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{description}">
  <meta property="og:url" content="{SITE + url}">
  <meta property="og:locale" content="{site["og_locale"]}">
  <meta property="og:locale:alternate" content="{other_site["og_locale"]}">
  <meta property="og:image" content="{SITE}/assets/og-image.png">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:image:alt" content="{attr(site["og_image_alt"])}">
  <meta name="twitter:card" content="summary_large_image">'''


def fill(layout, values):
    html = layout
    for key, value in values.items():
        html = html.replace("{{" + key + "}}", value)
    leftover = re.findall(r"\{\{\w+\}\}", html)
    if leftover:
        raise SystemExit(f"marcadores por preencher {leftover}")
    return html


def write(url, html):
    target = OUT / url.lstrip("/") / "index.html" if url.endswith("/") else OUT / url.lstrip("/")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8")


def render(lang, name, layout, content):
    site, other = content[lang]["site"], content["en" if lang == "pt" else "pt"]["site"]
    other_lang = "en" if lang == "pt" else "pt"
    page = content[lang]["pages"][name]
    url = url_for(lang, name)
    pt_url, en_url = ROUTES[name]
    html = fill(layout, {
        "html_lang": site["html_lang"],
        "title": escape(page["title"], quote=False),
        "head_meta": head_meta(site, other, page, url, pt_url, en_url),
        "skip": site["skip"],
        "header": site_header(site, lang, name, url_for(other_lang, name), other["html_lang"]),
        "main": main_html(page),
        "footer": site_footer(site, lang),
    })
    write(url, html)
    return url


def render_404(layout, content):
    """404 em PT com um bloco em EN (lang="en"), servido pelo nginx em qualquer caminho."""
    site, en = content["pt"]["site"], content["en"]
    nf = content["pt"]["notfound"]
    en_band = (f'    <section class="band" lang="en">\n      <div class="wrap">\n'
               f'        <h2>{en["notfound"]["h2"]}</h2>\n'
               f'        <p class="band-intro">{en["notfound"]["text"]}</p>\n'
               f'        {actions([en["notfound"]["action"]])}\n      </div>\n    </section>')
    html = fill(layout, {
        "html_lang": site["html_lang"],
        "title": escape(nf["title"], quote=False),
        "head_meta": '  <meta name="robots" content="noindex">',
        "skip": site["skip"],
        "header": site_header(site, "pt", None, "/en/", en["site"]["html_lang"]),
        "main": page_head(nf["head"]) + "\n\n" + en_band,
        "footer": site_footer(site, "pt"),
    })
    (OUT / "404.html").write_text(html, encoding="utf-8")


def write_sitemap():
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
    content = {lang: load_content(lang) for lang in ("pt", "en")}
    urls = [render(lang, name, layout, content) for lang in ("pt", "en") for name in ROUTES]
    render_404(layout, content)
    write_icons()
    write_sitemap()
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n", encoding="utf-8")
    print(f"{len(urls)} páginas e a 404 geradas em public/")


if __name__ == "__main__":
    main()
