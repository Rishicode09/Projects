// money.js — all money in this app is stored as integer CENTS, never decimals.
// $12.34 is stored as 1234. This avoids floating-point errors like 0.1 + 0.2.
// We only convert back to dollars when displaying.

// Turn a typed dollar string ("12.5") into integer cents (1250).
export function toCents(input) {
  const n = parseFloat(input);
  if (isNaN(n)) return 0;
  return Math.round(n * 100);
}

// Turn integer cents (1250) into a display string ("$12.50").
// Pass a currency symbol to show e.g. "€12.50" or "₹12.50".
export function formatCents(cents, symbol = "$") {
  return `${symbol}${(cents / 100).toFixed(2)}`;
}

// The currencies the user can choose from (symbol used everywhere for display).
export const CURRENCIES = [
  { code: "USD", symbol: "$" },
  { code: "EUR", symbol: "€" },
  { code: "GBP", symbol: "£" },
  { code: "INR", symbol: "₹" },
  { code: "JPY", symbol: "¥" },
];

// Expense categories (the emoji is just a friendly visual label).
export const CATEGORIES = [
  { id: "general", label: "General", emoji: "🧾" },
  { id: "food", label: "Food & Drink", emoji: "🍕" },
  { id: "rent", label: "Rent", emoji: "🏠" },
  { id: "utilities", label: "Utilities", emoji: "💡" },
  { id: "transport", label: "Transport", emoji: "🚕" },
  { id: "fun", label: "Entertainment", emoji: "🎉" },
  { id: "other", label: "Other", emoji: "📦" },
];

export function categoryOf(id) {
  return CATEGORIES.find((c) => c.id === id) || CATEGORIES[0];
}

// Split a total (in cents) across some weights, sharing leftover pennies fairly
// using the "largest remainder" method, so the parts ALWAYS sum exactly to total.
//   splitCents(1000, [1, 1, 1])   -> [334, 333, 333]   (sums to 1000, not 999)
//   splitCents(1000, [50, 30, 20]) -> [500, 300, 200]
export function splitCents(totalCents, weights) {
  const totalWeight = weights.reduce((sum, w) => sum + w, 0);
  if (totalWeight <= 0) return weights.map(() => 0);

  const raw = weights.map((w) => (totalCents * w) / totalWeight);
  const result = raw.map((r) => Math.floor(r));
  let leftover = totalCents - result.reduce((sum, f) => sum + f, 0);

  // Hand the leftover pennies to the entries with the biggest fractional part.
  const order = raw
    .map((r, i) => ({ i, frac: r - Math.floor(r) }))
    .sort((a, b) => b.frac - a.frac);

  for (let k = 0; k < leftover; k++) {
    result[order[k % order.length].i] += 1;
  }
  return result;
}
