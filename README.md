# thr33

Site institucional da Thr33 Labs em [thr33.xyz](https://thr33.xyz). É HTML estático servido a partir de `public/`.

## Editar

- Todos os textos estão em `src/content/pt.json` e `src/content/en.json`, um ficheiro por língua: menu, rodapé, páginas e 404. Os dois ficheiros têm a mesma estrutura, e os textos podem levar HTML simples (links, `<strong>`, `<br>`).
- Cada página é uma cabeça seguida de secções com um `type` (`cards`, `ticks`, `projects`, `steps`, `services`, `split`, `facts`, `ficha`, `features`, `stats`, `prose`, `text`, `cta`). As secções com `label` levam uma etiqueta numerada (01), (02)… O HTML de cada tipo, o cabeçalho e o rodapé são componentes em `scripts/build.py`. O esqueleto da página está em `src/layout.html`.
- As imagens são `<picture>` com AVIF e WebP em 3 larguras. As imagens-mestre estão em `src/images/` (PNG com a largura maior) e as larguras e o `sizes` em `src/images/images.json`. Depois de trocar uma mestre, corre-se `python3 scripts/images.py` (precisa de `cwebp` e `avifenc`) e o `build.py`. O `alt` fica nos conteúdos.
- A pixel art (as imagens da página Get It Vac, com `"pixel_art": true` no `images.json`) vai só em WebP sem perdas. O `images.py` desenha cada largura a partir do SVG, sem reamostrar a mestre, e cada largura tem de ser um múltiplo inteiro da grelha de píxeis: a largura do SVG ou o `pixel_grid`, se o desenho usa meios píxeis. Por isso pode ter 2 larguras em vez de 3. Outras larguras desfocam os píxeis.
- As ilustrações dos projetos saem de `python3 scripts/art.py`, a partir dos assets em `src/art/` (o SVG da sala e o ícone do vizia.thr33.xyz, o logótipo do vac.navego.pt, e os sprites e o cartaz do jogo em JSON). Gera os SVG dos cartões de projeto em `public/assets/img/projetos/` e as imagens-mestre da página Get It Vac (SVG e PNG, com `swift scripts/raster.swift`); depois corre-se o `images.py` e o `build.py`. Os cartões de projeto (Vizia e Get It Vac) são um só componente, com a lista `projects` em cada ficheiro de conteúdos.
- `public/assets/site.css`, `public/assets/js/site.js` e `public/favicon.svg` editam-se diretamente. A `404.html` é gerada.
- O HTML refere o `tokens.css`, o `site.css`, o `site.js` e o `icons.svg` com `?v=` e o início do hash do conteúdo, que o `build.py` calcula. Depois de editar um destes ficheiros, corre-se o `build.py` para a versão mudar: é isso que faz o Cloudflare e os browsers irem buscar o ficheiro novo depois do deploy. O `check_site.py` falha se a versão estiver desatualizada.
- Os ícones são do Lucide (licença ISC, `lucide-static@0.460.0`) e estão em `src/icons/`. O `build.py` junta-os em `public/assets/icons.svg`. Para acrescentar um ícone, copia-se o `.svg` do Lucide para `src/icons/` e usa-se o nome do ficheiro no campo `icon` do conteúdo.
- O Google Analytics 4 (`G-JCJZ754SWW`) está em `public/assets/js/consent.js` e só carrega depois de o visitante aceitar no banner de cookies. A escolha fica no cookie `thr33_consent` durante 6 meses, e pode ser mudada em «Preferências de cookies», no rodapé. Os textos do banner estão em `site.cookie_banner` e a política em `pages.cookies`.
- O JavaScript é só melhoria progressiva: põe a classe `.js` no `<html>`, abre o menu mobile e esconde o cabeçalho ao descer. Sem JS nada fica escondido, e o `check_site.py` confirma-o.
- Cores, fontes e movimento estão em `public/assets/css/tokens.css`. O `site.css` só usa esses tokens, e o `check_site.py` confirma a paleta e o contraste AA em claro, escuro e `.theme-ink`.

## Gerar e verificar

```bash
python3 scripts/build.py
python3 tests/check_site.py
```

O `build.py` regenera as páginas, o `sitemap.xml` e o `robots.txt` em `public/`. O `check_site.py` confirma o rodapé legal, as meta tags, o hreflang e os links internos, e garante que o HTML não faz pedidos a terceiros (o GA só existe no `consent.js`, depois do consentimento). Não se faz commit com a verificação a falhar.

A imagem de partilha (`public/assets/og-image.png`) gera-se com `swift scripts/og-image.swift`. A configuração do Forge e do Cloudflare está em [docs/deploy.md](docs/deploy.md).
