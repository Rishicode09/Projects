# 🛡️ Warranty Vault

Cross-platform mobile app that turns receipts into tracked warranties, return
windows, and protection insights. Snap a receipt → AI extracts the details →
Warranty Vault reminds you before anything expires and helps you file claims.

Built with **React Native (Expo) + TypeScript + Supabase**.

---

## Features

| Area | What it does |
| --- | --- |
| **Auth** | Email/password sign-up, login, password reset, persistent sessions |
| **Receipt upload** | Photos, screenshots, or PDFs stored in private Supabase Storage |
| **AI processing** | Pluggable OCR service extracts retailer, date, items, prices, total, warranty |
| **Products** | Full CRUD with strong validation |
| **Dashboard** | Active warranties, expiring-soon, protected value, savings, recent additions |
| **Notifications** | Local reminders 30d / 7d before warranty expiry, 1d before return deadline |
| **Claim assistant** | Generates copy/shareable warranty-claim letters |
| **Settings** | Notification prefs, dark mode, privacy controls, premium placeholder |

## Tech stack

- **Expo + React Native** (iOS, Android, Web)
- **TypeScript** in `strict` mode (+ `noUncheckedIndexedAccess`)
- **Supabase** — Auth, Postgres (with RLS), Storage, Edge Functions
- **Zustand** for state, **Zod** for validation
- **NativeWind** (Tailwind) for styling with dark mode
- **React Navigation** (stack + bottom tabs)
- **Jest** + Testing Library

## Architecture

The codebase is **feature-based** with clean layering. Dependencies point
inward: UI → hooks → stores → repositories/services → lib.

```
src/
├── app/              # navigation + providers (composition root)
├── components/       # shared UI primitives + ErrorBoundary
├── features/         # auth, receipts, products, dashboard, claims, settings
│   └── <feature>/    #   screens/ · hooks/ · store/ · services/ · components/
├── repositories/     # data access (Supabase + offline cache)  ← Repository pattern
├── services/         # OCR, storage, notifications, claims      ← Service layer
├── schemas/          # Zod schemas (validate all external input)
├── lib/              # supabase client, theme, date/format utils, Result type
└── types/            # domain models
```

### Key decisions

- **OCR is an interface, not an implementation.** `OcrService` is an
  abstraction with a `MockOcrService` (deterministic, offline — used in dev &
  tests) and a `SupabaseOcrService` (calls the `process-receipt` Edge Function).
  `createOcrService()` picks one via env. Swapping to an on-device model later
  touches one file. The AI provider key lives **server-side only**.

- **Repository pattern + offline-first.** Repositories own all Supabase access
  and a thin AsyncStorage cache. Reads fall back to cache when the network
  fails; writes invalidate it. The rest of the app never imports `supabase`
  for data.

- **Validate at the boundary.** Every piece of external input — auth forms,
  product drafts, and especially AI/OCR output — is parsed with Zod before the
  app trusts it. AI output is untrusted by default.

- **`Result<T, E>` over throwing.** Services and repositories return an explicit
  `Result` so callers handle failure deliberately; only render-time crashes hit
  the `ErrorBoundary`.

- **Pure cores, thin shells.** Stat computation, notification planning, claim
  templates, and date math are pure functions, so the meaningful logic is unit
  tested without a device or backend.

- **Security via RLS.** Postgres Row Level Security and Storage policies scope
  every row/file to its owner (`auth.uid()`); the anon key is safe on the client.

## Quick start

```bash
cd WarrantyVault
npm install
cp .env.example .env          # works out-of-the-box with OCR_PROVIDER=mock
npm test                      # run the suite
npm start                     # launch Expo
```

Full instructions (Supabase setup, Edge Function deploy, seeding) live in
[`docs/SETUP.md`](./docs/SETUP.md).

## Testing

- **Unit:** OCR mock, notification planner, claim generator, dashboard stats,
  date utils — `src/**/__tests__`.
- **Integration:** the receipt → product → dashboard flow —
  `__tests__/integration/receiptFlow.test.ts`.

```bash
npm test            # all tests
npm run test:ci     # with coverage
```

## Project layout (top level)

```
WarrantyVault/
├── App.tsx, index.ts          # entry point
├── src/                       # application code (see Architecture)
├── supabase/
│   ├── migrations/            # SQL schema + RLS + storage policies
│   ├── functions/             # process-receipt Edge Function
│   └── seed.sql               # sample data
├── __tests__/integration/     # cross-layer tests
├── docs/SETUP.md
└── .env.example
```

## Roadmap / placeholders

- Premium upgrade is a local flag (wire to RevenueCat / Stripe).
- Subscription tracking shares the product model; a dedicated cadence field is
  the natural next step.
- Push (vs. local) notifications via Expo push tokens for cross-device reminders.

---

Built as a production-ready reference architecture. PRs and forks welcome.
