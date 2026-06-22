# Warranty Vault — Setup Guide

## Prerequisites

- Node.js 18+
- npm or yarn
- [Expo CLI](https://docs.expo.dev/) (`npm i -g expo`) — optional, `npx expo` works too
- A [Supabase](https://supabase.com) project (free tier is fine)
- (Optional) [Supabase CLI](https://supabase.com/docs/guides/cli) for migrations & Edge Functions

## 1. Install dependencies

```bash
cd WarrantyVault
npm install
```

## 2. Configure environment

```bash
cp .env.example .env
```

Fill in:

| Variable | Where to find it |
| --- | --- |
| `EXPO_PUBLIC_SUPABASE_URL` | Supabase dashboard → Project Settings → API → Project URL |
| `EXPO_PUBLIC_SUPABASE_ANON_KEY` | same page → `anon` `public` key |
| `EXPO_PUBLIC_OCR_PROVIDER` | `mock` (default, offline) or `supabase` (uses the Edge Function) |

> The app runs fully with `EXPO_PUBLIC_OCR_PROVIDER=mock` and no AI key — great
> for development and the test suite.

## 3. Set up the database

Using the Supabase CLI:

```bash
supabase link --project-ref <your-ref>
supabase db push          # applies supabase/migrations/*.sql
```

Or paste the contents of `supabase/migrations/0001_init.sql` and
`0002_storage.sql` into the Supabase SQL editor and run them.

### Seed sample data (optional)

Create a user first (Auth dashboard or CLI), then run `supabase/seed.sql`
in the SQL editor — it attaches sample products to the first user.

## 4. (Optional) Deploy the AI receipt function

```bash
supabase functions deploy process-receipt
supabase secrets set OPENAI_API_KEY=sk-...
```

Then set `EXPO_PUBLIC_OCR_PROVIDER=supabase` in `.env`.

## 5. Run the app

```bash
npm start          # then press i / a, or scan the QR with Expo Go
npm run ios
npm run android
```

## 6. Run the checks

```bash
npm run typecheck
npm test
npm run lint
```
