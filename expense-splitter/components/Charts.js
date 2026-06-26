"use client";

import { motion } from "framer-motion";
import { formatCents, categoryOf } from "@/lib/money";

// A single animated horizontal bar. width animates (transform-friendly) for smoothness.
function Bar({ label, valueCents, maxCents, symbol, color }) {
  const pct = maxCents > 0 ? Math.round((valueCents / maxCents) * 100) : 0;
  return (
    <div className="text-sm">
      <div className="mb-1 flex justify-between">
        <span className="text-slate-600 dark:text-slate-300">{label}</span>
        <span className="font-medium text-slate-900 dark:text-slate-100">
          {formatCents(valueCents, symbol)}
        </span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-700">
        <motion.div
          className={`h-full rounded-full ${color}`}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ type: "spring", stiffness: 120, damping: 20 }}
        />
      </div>
    </div>
  );
}

// Insights — two simple charts: who paid the most, and spend by category.
export function Charts({ people, expenses, symbol }) {
  if (expenses.length === 0) {
    return (
      <p className="text-sm text-slate-400">Log some expenses to see spending insights.</p>
    );
  }

  // Total each person has PAID (laid out), regardless of what they owe.
  const paidByPerson = people
    .map((name) => ({
      name,
      cents: expenses.filter((e) => e.paidBy === name).reduce((s, e) => s + e.amount, 0),
    }))
    .filter((p) => p.cents > 0)
    .sort((a, b) => b.cents - a.cents);

  // Total spend grouped by category.
  const byCategory = {};
  expenses.forEach((e) => {
    const c = categoryOf(e.category).id;
    byCategory[c] = (byCategory[c] || 0) + e.amount;
  });
  const categoryRows = Object.keys(byCategory)
    .map((id) => ({ id, cents: byCategory[id] }))
    .sort((a, b) => b.cents - a.cents);

  const maxPaid = Math.max(...paidByPerson.map((p) => p.cents), 1);
  const maxCat = Math.max(...categoryRows.map((c) => c.cents), 1);

  return (
    <div className="grid gap-6 sm:grid-cols-2">
      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
          Paid by person
        </p>
        <div className="space-y-3">
          {paidByPerson.map((p) => (
            <Bar key={p.name} label={p.name} valueCents={p.cents} maxCents={maxPaid} symbol={symbol} color="bg-slate-800 dark:bg-slate-300" />
          ))}
        </div>
      </div>

      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
          Spend by category
        </p>
        <div className="space-y-3">
          {categoryRows.map((c) => {
            const cat = categoryOf(c.id);
            return (
              <Bar key={c.id} label={`${cat.emoji} ${cat.label}`} valueCents={c.cents} maxCents={maxCat} symbol={symbol} color="bg-indigo-500" />
            );
          })}
        </div>
      </div>
    </div>
  );
}
