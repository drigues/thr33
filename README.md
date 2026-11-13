# thr33

Site institucional da Thr33 Labs em [thr33.xyz](https://thr33.xyz). É HTML estático servido a partir de `public/`.

## Editar

- Todos os textos estão em `src/content/pt.json` e `src/content/en.json`, um ficheiro por língua: menu, rodapé, páginas e 404. Os dois ficheiros têm a mesma estrutura, e os textos podem levar HTML simples (links, `<strong>`, `<br>`).
- Cada página é uma cabeça seguida de secções com um `type` (`cards`, `ticks`, `project`, `steps`, `services`, `split`, `facts`, `prose`, `text`, `cta`). As secções com `label` levam uma etiqueta numerada (01), (02)… O HTML de cada tipo, o cabeçalho e o rodapé são componentes em `scripts/build.py`. O esqueleto da página está em `src/layout.html`.
- `public/assets/site.css`, `public/assets/js/site.js` e `public/favicon.svg` editam-se diretamente. A `404.html` é gerada.
- Os ícones são do Lucide (licença ISC, `lucide-static@0.460.0`) e estão em `src/icons/`. O `build.py` junta-os em `public/assets/icons.svg`. Para acrescentar um ícone, copia-se o `.svg` do Lucide para `src/icons/` e usa-se o nome do ficheiro no campo `icon` do conteúdo.
- O JavaScript é só melhoria progressiva: põe a classe `.js` no `<html>`, abre o menu mobile e esconde o cabeçalho ao descer. Sem JS nada fica escondido, e o `check_site.py` confirma-o.
- Cores, fontes e movimento estão em `public/assets/css/tokens.css`. O `site.css` só usa esses tokens, e o `check_site.py` confirma a paleta e o contraste AA em claro, escuro e `.theme-ink`.

## Gerar e verificar

```bash
python3 scripts/build.py
python3 tests/check_site.py
```

O `build.py` regenera as páginas, o `sitemap.xml` e o `robots.txt` em `public/`. O `check_site.py` confirma o rodapé legal, as meta tags, o hreflang e os links internos, e garante que não há pedidos a terceiros. Não se faz commit com a verificação a falhar.

A imagem de partilha (`public/assets/og-image.png`) gera-se com `swift scripts/og-image.swift`. A configuração do Forge e do Cloudflare está em [docs/deploy.md](docs/deploy.md).
