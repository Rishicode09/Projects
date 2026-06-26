# 🏠 Household Expense Splitter

A simple app to split shared household expenses fairly. Add your flatmates,
log who paid for what, and the app works out **who owes whom**.

Built with **Next.js**, **React**, and **Tailwind CSS**. Data is kept in
memory only (no database yet) — refreshing the page resets everything.

## Run it locally

```bash
cd expense-splitter
npm install      # one time only — downloads the libraries
npm run dev      # start the app
```

Then open http://localhost:3000 in your browser.

## Where things live

| File | What it does |
|------|--------------|
| `app/page.js` | The whole app — people, expenses, and the summary |
| `lib/settle.js` | The "who owes whom" math, as one clear function |
| `app/layout.js` | Page wrapper (tab title, background) |
| Config files | `package.json`, `tailwind.config.js`, etc. — plumbing |
