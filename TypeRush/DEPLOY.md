# Deploying TypeRush securely on Cloudflare Pages

TypeRush is a static site (HTML + CSS + JS + fonts, no backend, no secrets,
no database). State lives only in the visitor's `localStorage`. Cloudflare
Pages gives you free auto-renewing HTTPS, a global CDN, and DDoS protection.

The `_headers` file in this folder applies a strict Content-Security-Policy
(no `unsafe-inline`, no remote origins), HSTS, anti-clickjacking, and a locked
Permissions-Policy. The font is self-hosted (`fonts/`), so the page makes
**zero third-party requests**.

> Important: set the **build output directory to `TypeRush`** so this folder
> becomes the site root and `_headers` takes effect.

---

## Option A — Git-connected deploy (recommended)

Every push auto-deploys; previews are created for branches/PRs.

1. Go to the Cloudflare dashboard → **Workers & Pages** → **Create** →
   **Pages** → **Connect to Git**.
2. Authorize GitHub and pick the **`Rishicode09/Projects`** repository.
3. Configure the build:
   - **Production branch:** `main` (deploy this branch after the PR is merged),
     or pick `claude/confident-keller-yoiwqp` to preview before merging.
   - **Framework preset:** `None`
   - **Build command:** *(leave empty)*
   - **Build output directory:** `TypeRush`
4. Click **Save and Deploy**. You'll get a `https://<project>.pages.dev` URL.

## Option B — Direct upload with Wrangler (no Git)

```bash
npm install -g wrangler
wrangler login
# from the repo root:
wrangler pages deploy TypeRush --project-name typerush
```

---

## Custom domain (optional)

Pages project → **Custom domains** → add your domain. Cloudflare provisions
the TLS certificate automatically. Keep HSTS (already in `_headers`); only add
`preload` once you're sure every subdomain is HTTPS-only.

## Verify the deployment is locked down

```bash
# Headers present?
curl -sSI https://<project>.pages.dev | grep -iE 'content-security-policy|strict-transport|x-frame|x-content-type|referrer-policy|permissions-policy'
```

Then open the site, press F12 → **Console**, and confirm there are **no CSP
violation errors** while playing both modes. The **Network** tab should show
requests only to your own origin (html, css, js, woff2) — nothing to Google.

## Security notes

- **No secrets to leak** — the app is 100% client-side. Nothing sensitive ships.
- **CSP** blocks any injected/remote script or style from executing or loading.
- **`frame-ancestors 'none'` + `X-Frame-Options: DENY`** prevent clickjacking.
- **HSTS** forces HTTPS on repeat visits.
- The only data stored is the player's own scores in their browser's
  `localStorage` — never transmitted anywhere.
