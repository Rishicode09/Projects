# TypeRush accounts backend (Cloudflare Pages Functions + D1)

Accounts use **email + password** with progress synced to a **Cloudflare D1**
database. Passwords are hashed with PBKDF2 (Web Crypto); sessions are HMAC-signed
tokens. The API lives in `functions/api/[[path]].js` and is served at `/api/*`
by **Cloudflare Pages Functions** — so it only runs on the **Pages** deployment
(not the standalone Worker). Use your Pages site as the canonical URL.

Until the two bindings below exist, `/api/*` returns `503` and the game runs in
**offline/local** mode (the "Continue offline" option still works) — so the site
never breaks while you set this up.

## One-time setup (Cloudflare dashboard)

1. **Create the database**
   Dashboard → **Storage & Databases → D1 → Create database** → name it
   `typerush-db`.

2. **Bind it to the Pages project**
   Your Pages project → **Settings → Functions → D1 database bindings → Add** →
   - Variable name: `DB`
   - Database: `typerush-db`
   Add it for **Production** (and **Preview** too if you want it on PR preview URLs).

3. **Add the auth secret**
   Same project → **Settings → Environment variables** → add a **Production**
   variable:
   - Name: `AUTH_SECRET`
   - Value: a long random string (e.g. run `openssl rand -hex 32`)
   Mark it encrypted/secret. (Add to Preview too if testing on preview URLs.)

4. **Redeploy** (push any commit, or use "Retry deployment"). The table is
   created automatically on the first API request.

## Verify

```bash
# Should return JSON, not 503, once DB + AUTH_SECRET are set:
curl -s -X POST https://<your-site>/api/signup \
  -H 'content-type: application/json' \
  -d '{"email":"you@example.com","password":"hunter2"}'
```

Then in the app: **Sign up** with an email + password, earn some XP, log in on
another device, and your progress (XP, levels, bests, Story-Mode rank) follows you.

## Notes

- Bindings are per-environment. The PR **preview** deployments won't have the
  binding unless you also add it for Preview; easiest is to test on Production.
- No third-party services are used; everything stays in your Cloudflare account.
- Stored data is minimal: email, a salted password hash, and the progress blob.
