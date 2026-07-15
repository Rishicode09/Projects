# TypeRush

A gamified speed-typing trainer — a static site with no build step. The font is
bundled locally and there are no third-party requests. Progress is saved in your
browser's `localStorage`, with an **optional** email+password account for
cross-device sync (a small Cloudflare Pages Function + D1 — see `BACKEND.md`).

To run locally, just open `TypeRush/index.html` in any browser. To publish it
online securely (Cloudflare Pages, strict CSP, self-hosted font), see
[`DEPLOY.md`](DEPLOY.md).

## Files

| File | Purpose |
|------|---------|
| `index.html` | Markup — three screens (login / menu / game) + shared nav |
| `styles.css` | All styling + local `@font-face` (theming via CSS variables) |
| `app.js` | All game logic (state, both modes, rendering, scoring, accounts) |
| `functions/api/[[path]].js` | Optional accounts backend (Cloudflare Pages Function + D1) — lives at the **repo root**, not in `TypeRush/` |
| `fonts/` | Self-hosted JetBrains Mono (OFL) |
| `_headers` | Cloudflare Pages security headers (CSP, HSTS, etc.) |
| `DEPLOY.md` | Deployment guide |
| `BACKEND.md` | How to enable email+password accounts (D1 + `AUTH_SECRET`) |

## Code map

The source is heavily commented — every file opens with an overview block and each
section is marked with a banner comment, so you can read top-to-bottom or jump to a
part. Where to look:

- **`app.js`** — the bulk. Search for the `// ── NAME ──` banners:
  `STORIES` / `WORD LISTS` (text content) → `STATE` (the one `S` object) →
  persistence → `AUDIO`/`ORBS`/`PARTICLES` (WebAudio + canvas juice) →
  `SCREENS`/`PROFILES`/`ACCOUNTS` (navigation, login, cloud sync) →
  `WORD GENERATION`/`STORY RACES` → `WORD DOM`/`CARET`/`STORY DOM` (rendering +
  gliding cursor) → `GAME FLOW`/`INPUT`/`SUBMIT` (the typing loop) →
  `HUD`/`RESULTS` → `MENU`/`EVENTS`/`INIT` (wiring + startup).
- **`index.html`** — comments mark each region (canvas layers, nav, login, menu,
  game HUD, the Free vs Story typing areas, results, footer).
- **`styles.css`** — a header explains the CSS-variable theming; the tricky rules
  (3-row word window, the two carets, the SVG timer ring, CSP utility classes) are
  commented at their definitions.
- **`functions/api/[[path]].js`** — the accounts API: PBKDF2 password hashing,
  HMAC session tokens, and the `signup` / `login` / `sync` routes.

## Two modes

**⌨️ Free Mode** — Monkeytype-style speed test. Race a stream of words against a
15 / 30 / 60 s clock. Pick a difficulty (Easy / Medium / Hard) and optional
modifiers (numbers, punctuation, strict). Pure speed.

**📖 Story Mode** — TypeRacer-style. Type a real passage of classic literature
that reads as complete, grammatical prose (Three Little Pigs, The Great Gatsby,
Jekyll & Hyde, Alice in Wonderland, Sherlock Holmes). There is no countdown — you
*race to the end* of the passage while the timer counts up, with a live progress
bar. Each replay serves the next excerpt of that story. Errors must be corrected
before you can continue, so what you type always matches the text.

## How to play

1. Double-click `index.html` (or drag it into any browser).
2. Pick **Free Mode** or **Story Mode** and configure it.
3. Click **PLAY** — start typing. The timer starts on your first keystroke.
4. When the run ends, see your WPM, accuracy, consistency, and a WPM-over-time chart.

## Controls

| Key | Action |
|-----|--------|
| `Tab` | Restart immediately (game or results screen) |
| `Enter` | Restart from results screen |
| `Esc` | Back to menu |
| `Space` | Submit current word (Free Mode) |
| `Backspace` | Fix a mistake (both modes) |

## Scoring

- Each correct character = 10 pts × your current combo multiplier.
- **Combo** grows with every correct word, resets on a mistake.
- Multiplier: ×1 base → ×1.5 at 5× → ×2 at 10× → ×3 at 25× → ×4 at 50×.
- **XP** is awarded at the end of each run (score/10 + WPM×2).
- Level up by filling the XP bar — progress is saved between sessions.

## Features

- Live WPM, accuracy, score, and combo during the game.
- Combo streak meter with milestone glow at 10/25/50/100×.
- WPM-over-time chart on the results screen.
- **Trouble keys**: shows which characters you mis-hit most.
- Personal bests saved per Free-Mode duration+difficulty and per story.
- Achievements (First 40 WPM, 100% accuracy, 50× combo, etc.).
- Dark / light theme toggle.
- Optional keypress sounds (WebAudio, fully client-side).
- Works fully offline in local mode; the only optional network use is cloud account sync.
