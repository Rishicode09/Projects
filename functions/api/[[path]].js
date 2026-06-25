// TypeRush backend — Cloudflare Pages Functions (catch-all for /api/*).
//
// Account sync with email + password. Passwords are hashed with PBKDF2
// (Web Crypto); sessions are stateless HMAC-signed tokens.
//
// Requires two things configured on the Pages project (Settings → Functions):
//   1. A D1 database bound as  DB
//   2. A secret env var        AUTH_SECRET   (any long random string)
// Until both exist, the endpoints return 503 and the game runs in local mode.

const TOKEN_TTL = 1000 * 60 * 60 * 24 * 30; // 30 days

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { 'content-type': 'application/json; charset=utf-8' },
  });
}
async function readJson(req) { try { return await req.json(); } catch (e) { return {}; } }
const normEmail = e => (e || '').trim().toLowerCase().slice(0, 160);
const validEmail = e => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(e);

const enc = new TextEncoder();
function toHex(buf) { return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, '0')).join(''); }
function fromHex(h) { const a = new Uint8Array(h.length / 2); for (let i = 0; i < a.length; i++) a[i] = parseInt(h.substr(i * 2, 2), 16); return a; }
function b64url(bytes) { return btoa(String.fromCharCode(...bytes)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, ''); }
function b64urlDecode(s) { return atob(s.replace(/-/g, '+').replace(/_/g, '/')); }

async function pbkdf2(password, saltBytes) {
  const key = await crypto.subtle.importKey('raw', enc.encode(password), 'PBKDF2', false, ['deriveBits']);
  const bits = await crypto.subtle.deriveBits(
    { name: 'PBKDF2', salt: saltBytes, iterations: 100000, hash: 'SHA-256' }, key, 256);
  return toHex(bits);
}
async function hashPassword(pw) {
  const salt = crypto.getRandomValues(new Uint8Array(16));
  return { salt: toHex(salt), hash: await pbkdf2(pw, salt) };
}
async function verifyPassword(pw, saltHex, hashHex) {
  const h = await pbkdf2(pw, fromHex(saltHex));
  // length-safe constant-ish comparison
  if (h.length !== hashHex.length) return false;
  let diff = 0;
  for (let i = 0; i < h.length; i++) diff |= h.charCodeAt(i) ^ hashHex.charCodeAt(i);
  return diff === 0;
}

async function hmac(data, secret) {
  const key = await crypto.subtle.importKey('raw', enc.encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const sig = await crypto.subtle.sign('HMAC', key, enc.encode(data));
  return b64url(new Uint8Array(sig));
}
async function signToken(email, secret) {
  const payload = b64url(enc.encode(JSON.stringify({ email, exp: Date.now() + TOKEN_TTL })));
  return payload + '.' + await hmac(payload, secret);
}
async function verifyToken(token, secret) {
  if (!token || token.indexOf('.') < 0) return null;
  const [payload, sig] = token.split('.');
  if (await hmac(payload, secret) !== sig) return null;
  try {
    const data = JSON.parse(b64urlDecode(payload));
    if (!data.exp || Date.now() > data.exp) return null;
    return data;
  } catch (e) { return null; }
}

export async function onRequest(context) {
  const { request, env } = context;
  const url = new URL(request.url);
  const path = url.pathname.replace(/\/+$/, '');

  if (!env.DB) return json({ error: 'Backend not configured: no D1 database bound (DB).' }, 503);
  const secret = env.AUTH_SECRET || '';
  if (!secret) return json({ error: 'Backend not configured: no AUTH_SECRET set.' }, 503);

  try {
    await env.DB.prepare(
      `CREATE TABLE IF NOT EXISTS users (
        email TEXT PRIMARY KEY,
        pw_hash TEXT NOT NULL,
        pw_salt TEXT NOT NULL,
        progress TEXT,
        best_wpm INTEGER DEFAULT 0,
        rank TEXT,
        created INTEGER
      )`).run();
  } catch (e) { return json({ error: 'Database initialization failed.' }, 500); }

  const auth = async () => {
    const t = (request.headers.get('Authorization') || '').replace(/^Bearer\s+/i, '');
    return await verifyToken(t, secret);
  };

  // POST /api/signup
  if (request.method === 'POST' && path === '/api/signup') {
    const b = await readJson(request);
    const email = normEmail(b.email), pw = b.password || '';
    if (!validEmail(email)) return json({ error: 'Please enter a valid email.' }, 400);
    if (pw.length < 6) return json({ error: 'Password must be at least 6 characters.' }, 400);
    const exists = await env.DB.prepare('SELECT email FROM users WHERE email=?').bind(email).first();
    if (exists) return json({ error: 'An account with that email already exists.' }, 409);
    const { salt, hash } = await hashPassword(pw);
    await env.DB.prepare('INSERT INTO users (email,pw_hash,pw_salt,progress,best_wpm,rank,created) VALUES (?,?,?,?,?,?,?)')
      .bind(email, hash, salt, null, 0, null, Date.now()).run();
    return json({ token: await signToken(email, secret), email, progress: null });
  }

  // POST /api/login
  if (request.method === 'POST' && path === '/api/login') {
    const b = await readJson(request);
    const email = normEmail(b.email), pw = b.password || '';
    const row = await env.DB.prepare('SELECT * FROM users WHERE email=?').bind(email).first();
    if (!row) return json({ error: 'No account found with that email.' }, 404);
    if (!await verifyPassword(pw, row.pw_salt, row.pw_hash)) return json({ error: 'Incorrect password.' }, 401);
    return json({ token: await signToken(email, secret), email, progress: row.progress ? JSON.parse(row.progress) : null });
  }

  // GET/POST /api/sync (authenticated)
  if (path === '/api/sync') {
    const user = await auth();
    if (!user) return json({ error: 'Not signed in.' }, 401);
    if (request.method === 'GET') {
      const row = await env.DB.prepare('SELECT progress FROM users WHERE email=?').bind(user.email).first();
      return json({ progress: row && row.progress ? JSON.parse(row.progress) : null });
    }
    if (request.method === 'POST') {
      const b = await readJson(request);
      const progress = b.progress || {};
      const best = Number(b.best_wpm) || 0;
      const rank = (b.rank || '').toString().slice(0, 40) || null;
      await env.DB.prepare('UPDATE users SET progress=?, best_wpm=?, rank=? WHERE email=?')
        .bind(JSON.stringify(progress), best, rank, user.email).run();
      return json({ ok: true });
    }
  }

  return json({ error: 'Not found.' }, 404);
}
