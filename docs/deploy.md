# Deploy do thr33.xyz

O site é estático: o servidor só tem de servir a pasta `public/`. Não há build no servidor, porque o HTML gerado vai no repositório.

## Forge

1. **Site → Settings → Web Directory:** `/public`.
2. **Site → Deployments → Deploy Script:** basta o `git pull`. Apagar as linhas de `composer`, `npm` e `artisan`, se existirem:

   ```bash
   cd $FORGE_SITE_PATH
   git pull origin $FORGE_SITE_BRANCH
   ```

3. **Site → Files → Edit Nginx Configuration:** dentro do bloco `server { ... }` do `thr33.xyz`, trocar o `location /` e o `error_page` do PHP por isto. Não mexer nas linhas de `ssl_*`, que são do Forge:

   ```nginx
   index index.html;
   charset utf-8;

   # Páginas como /sobre/ servem sobre/index.html; o resto dá 404.
   location / {
       try_files $uri $uri/ =404;
   }

   error_page 404 /404.html;
   location = /404.html { internal; }

   # Fontes, CSS e imagens com cache longo.
   location /assets/ {
       expires 30d;
       add_header Cache-Control "public";
       add_header X-Content-Type-Options "nosniff" always;
   }

   # Cabeçalhos de segurança (SEC-1). O site não tem scripts nem pedidos a terceiros.
   add_header X-Frame-Options "SAMEORIGIN" always;
   add_header X-Content-Type-Options "nosniff" always;
   add_header Referrer-Policy "strict-origin-when-cross-origin" always;
   add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
   add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
   add_header Content-Security-Policy "default-src 'self'; img-src 'self' data:; style-src 'self'; font-src 'self'; script-src 'none'; frame-ancestors 'self'; base-uri 'self'; form-action 'none'" always;
   ```

   Se houver um `location ~ \.php$`, pode sair: o site não tem PHP.

## Cloudflare: www → thr33.xyz

O `www.thr33.xyz` está em proxy no Cloudflare, por isso o redirect faz-se lá, antes de chegar ao servidor.

**Rules → Redirect Rules → Create rule**

- Nome: `www para apex`
- Quando: `Hostname` igual a `www.thr33.xyz`
- Então: **Dynamic redirect**, expressão `concat("https://thr33.xyz", http.request.uri.path)`, código **301**, **Preserve query string** activo.

Em **SSL/TLS → Overview**, o modo deve ser **Full (strict)**: o Forge tem certificado Let's Encrypt na origem.

## Verificar depois do deploy

```bash
curl -sI https://www.thr33.xyz/sobre/ | grep -iE '^(HTTP|location)'
curl -sI https://thr33.xyz/nao-existe | head -1
curl -s https://thr33.xyz/nao-existe | grep -o '<title>[^<]*'
curl -sI https://thr33.xyz/ | grep -iE 'content-security|strict-transport|referrer'
```

Resultado esperado: `301` para `https://thr33.xyz/sobre/`, `404` com o título «Página não encontrada · Thr33 Labs», e os três cabeçalhos presentes.
