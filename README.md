# thr33

Site institucional da Thr33 Labs em [thr33.xyz](https://thr33.xyz). É HTML estático servido a partir de `public/`.

## Editar

- O conteúdo das páginas está em `src/pages/pt/` e `src/pages/en/`, um ficheiro por página, com o mesmo nome nas duas línguas.
- O cabeçalho, o rodapé e as meta tags estão em `src/layout.html`. Os textos partilhados (menu, rodapé legal) estão em `scripts/build.py`.
- `public/assets/site.css`, `public/404.html` e `public/favicon.svg` editam-se diretamente.

## Gerar e verificar

```bash
python3 scripts/build.py
python3 tests/check_site.py
```

O `build.py` regenera as páginas, o `sitemap.xml` e o `robots.txt` em `public/`. O `check_site.py` confirma o rodapé legal, as meta tags, o hreflang e os links internos, e garante que não há pedidos a terceiros. Não se faz commit com a verificação a falhar.

A imagem de partilha (`public/assets/og-image.png`) gera-se com `swift scripts/og-image.swift`. A configuração do Forge e do Cloudflare está em [docs/deploy.md](docs/deploy.md).
