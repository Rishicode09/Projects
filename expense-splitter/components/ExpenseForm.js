"use client";

import { useState, useEffect } from "react";
import { Input, Button } from "@/components/ui";
import { toCents, splitCents, formatCents, CATEGORIES } from "@/lib/money";

// Today's date as a yyyy-mm-dd string (what an <input type="date"> expects).
const todayStr = () => new Date().toISOString().slice(0, 10);

// ExpenseForm — collects (or edits) an expense and computes each person's share
// in CENTS. Hands the result to onAddExpense / onUpdateExpense.
export function ExpenseForm({
  people,
  symbol = "$",
  onAddExpense,
  onSaveTemplate,
  editing,        // an expense being edited, or null
  onUpdateExpense,
  onCancelEdit,
}) {
  const [desc, setDesc] = useState("");
  const [amount, setAmount] = useState(""); // dollar string the user types
  const [paidBy, setPaidBy] = useState("");
  const [category, setCategory] = useState("general");
  const [date, setDate] = useState(todayStr());
  const [mode, setMode] = useState("equal"); // "equal" | "amounts" | "percent"

  // For equal mode we track who's EXCLUDED, so newly added people are
  // automatically included by default.
  const [excluded, setExcluded] = useState(() => new Set());
  const [custom, setCustom] = useState({}); // per-person typed value for amounts/percent
  const [saveAsTemplate, setSaveAsTemplate] = useState(false);
  const [error, setError] = useState("");

  // When we start editing an expense, prefill the form. Any split can be
  // represented as exact amounts, so editing always opens in "amounts" mode.
  useEffect(() => {
    if (!editing) return;
    setDesc(editing.description);
    setAmount((editing.amount / 100).toFixed(2));
    setPaidBy(editing.paidBy);
    setCategory(editing.category || "general");
    setDate((editing.date || new Date().toISOString()).slice(0, 10));
    setMode("amounts");
    const filled = {};
    Object.keys(editing.shares).forEach((n) => {
      filled[n] = (editing.shares[n] / 100).toFixed(2);
    });
    setCustom(filled);
    setExcluded(new Set());
    setSaveAsTemplate(false);
    setError("");
  }, [editing]);

  const amountCents = toCents(amount);

  function toggleIncluded(name) {
    const next = new Set(excluded);
    if (next.has(name)) next.delete(name);
    else next.add(name);
    setExcluded(next);
  }

  function setCustomValue(name, value) {
    setCustom({ ...custom, [name]: value });
  }

  // Work out each person's share in cents. Returns { shares, problem }.
  function computeShares() {
    if (mode === "equal") {
      const names = people.filter((p) => !excluded.has(p));
      if (names.length === 0) return { shares: {}, problem: "Pick at least one person." };
      const parts = splitCents(amountCents, names.map(() => 1));
      const shares = {};
      names.forEach((n, i) => (shares[n] = parts[i]));
      return { shares, problem: "" };
    }

    if (mode === "amounts") {
      const shares = {};
      let sum = 0;
      people.forEach((n) => {
        const c = toCents(custom[n]);
        if (c > 0) shares[n] = c;
        sum += c;
      });
      const off = amountCents - sum;
      if (off !== 0)
        return { shares, problem: `Amounts must total ${formatCents(amountCents, symbol)} (off by ${formatCents(off, symbol)}).` };
      return { shares, problem: "" };
    }

    // percent: use weights so the cents always sum exactly to the amount.
    const names = people.filter((n) => (parseFloat(custom[n]) || 0) > 0);
    const weights = names.map((n) => parseFloat(custom[n]) || 0);
    const sumPct = weights.reduce((s, w) => s + w, 0);
    if (Math.round(sumPct * 100) !== 10000)
      return { shares: {}, problem: `Percentages must total 100% (currently ${sumPct}%).` };
    const parts = splitCents(amountCents, weights);
    const shares = {};
    names.forEach((n, i) => (shares[n] = parts[i]));
    return { shares, problem: "" };
  }

  function handleSubmit() {
    setError("");
    if (desc.trim() === "") return setError("Add a description.");
    if (amountCents <= 0) return setError("Enter an amount greater than 0.");
    if (paidBy === "") return setError("Choose who paid.");

    const { shares, problem } = computeShares();
    if (problem) return setError(problem);

    // Store the date at noon so it never slips to the previous day across time zones.
    const dateISO = new Date(`${date}T12:00:00`).toISOString();
    const data = { description: desc.trim(), amount: amountCents, paidBy, category, date: dateISO, shares };

    if (editing) {
      onUpdateExpense({ ...editing, ...data });
    } else {
      onAddExpense(data);
      if (saveAsTemplate) onSaveTemplate(data);
    }
    resetForm();
  }

  function resetForm() {
    setDesc("");
    setAmount("");
    setPaidBy("");
    setCategory("general");
    setDate(todayStr());
    setMode("equal");
    setCustom({});
    setExcluded(new Set());
    setSaveAsTemplate(false);
  }

  // Live hint under the editor.
  const liveHint = (() => {
    if (amountCents <= 0) return null;
    if (mode === "equal") {
      const n = people.filter((p) => !excluded.has(p)).length || 1;
      return `Splitting ${formatCents(amountCents, symbol)} evenly ≈ ${formatCents(Math.round(amountCents / n), symbol)} each`;
    }
    if (mode === "amounts") {
      const sum = people.reduce((s, n) => s + toCents(custom[n]), 0);
      return `Assigned ${formatCents(sum, symbol)} of ${formatCents(amountCents, symbol)}`;
    }
    const sumPct = people.reduce((s, n) => s + (parseFloat(custom[n]) || 0), 0);
    return `Assigned ${sumPct}% of 100%`;
  })();

  const modes = [
    { id: "equal", label: "Split equally" },
    { id: "amounts", label: "Exact $" },
    { id: "percent", label: "Percent %" },
  ];

  return (
    <div>
      {editing && (
        <p className="mb-3 rounded-md bg-amber-50 px-3 py-2 text-xs font-medium text-amber-700">
          ✎ Editing “{editing.description}” — make your changes and save.
        </p>
      )}

      <div className="grid gap-3 sm:grid-cols-3">
        <Input placeholder="Description" value={desc} onChange={(e) => setDesc(e.target.value)} />
        <Input
          type="number"
          inputMode="decimal"
          placeholder="Amount"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
        />
        <select
          aria-label="Who paid"
          value={paidBy}
          onChange={(e) => setPaidBy(e.target.value)}
          className="h-10 rounded-md border border-slate-200 bg-white px-3 text-sm outline-none focus:ring-2 focus:ring-slate-200 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
        >
          <option value="">Paid by…</option>
          {people.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
      </div>

      {/* Category + date */}
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <select
          aria-label="Category"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="h-10 rounded-md border border-slate-200 bg-white px-3 text-sm outline-none focus:ring-2 focus:ring-slate-200 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
        >
          {CATEGORIES.map((c) => (
            <option key={c.id} value={c.id}>
              {c.emoji} {c.label}
            </option>
          ))}
        </select>
        <Input type="date" aria-label="Date" value={date} onChange={(e) => setDate(e.target.value)} />
      </div>

      {/* Accessible split-mode selector (announced as a radio group) */}
      <div role="radiogroup" aria-label="How to split this expense" className="mt-4 flex gap-1 rounded-lg bg-slate-100 p-1 text-sm">
        {modes.map((m) => (
          <button
            key={m.id}
            role="radio"
            aria-checked={mode === m.id}
            onClick={() => setMode(m.id)}
            className={`flex-1 rounded-md py-1.5 font-medium transition ${
              mode === m.id ? "bg-white shadow-sm" : "text-slate-500 hover:text-slate-800"
            }`}
          >
            {m.label}
          </button>
        ))}
      </div>

      {/* Per-person editor */}
      <div className="mt-3 space-y-2">
        {people.length === 0 && (
          <p className="text-sm text-slate-400">Add people first to split an expense.</p>
        )}
        {people.map((name) => (
          <div key={name} className="flex items-center justify-between gap-3">
            {mode === "equal" ? (
              <label className="flex w-full cursor-pointer items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={!excluded.has(name)}
                  onChange={() => toggleIncluded(name)}
                  className="h-4 w-4 rounded border-slate-300"
                />
                {name}
              </label>
            ) : (
              <>
                <span className="w-full text-sm">{name}</span>
                <div className="relative w-28 shrink-0">
                  <span className="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 text-xs text-slate-400">
                    {mode === "amounts" ? "$" : "%"}
                  </span>
                  <Input
                    type="number"
                    inputMode="decimal"
                    aria-label={`${name}'s ${mode === "amounts" ? "amount" : "percentage"}`}
                    value={custom[name] || ""}
                    onChange={(e) => setCustomValue(name, e.target.value)}
                    className="pl-5"
                    placeholder="0"
                  />
                </div>
              </>
            )}
          </div>
        ))}
      </div>

      {liveHint && <p className="mt-2 text-xs text-slate-500">{liveHint}</p>}
      {error && <p className="mt-2 text-xs font-medium text-red-600">{error}</p>}

      <div className="mt-4 flex items-center justify-between gap-3">
        {!editing ? (
          <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-600">
            <input
              type="checkbox"
              checked={saveAsTemplate}
              onChange={(e) => setSaveAsTemplate(e.target.checked)}
              className="h-4 w-4 rounded border-slate-300"
            />
            🔁 Save as recurring template
          </label>
        ) : (
          <Button variant="ghost" onClick={() => { resetForm(); onCancelEdit(); }}>
            Cancel
          </Button>
        )}
        <Button onClick={handleSubmit}>{editing ? "Save changes" : "Add expense"}</Button>
      </div>
    </div>
  );
}
