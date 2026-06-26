"use client";

import { useState } from "react";
import { Input, Button } from "@/components/ui";

// ExpenseForm — collects a new expense and figures out each person's "share".
//
// It hands the finished expense back to the parent via onAddExpense(expense),
// where expense = { description, amount, paidBy, shares: { name: dollars } }.
// If "Save as recurring template" is ticked, it also calls onSaveTemplate(...).
export function ExpenseForm({ people, onAddExpense, onSaveTemplate }) {
  const [desc, setDesc] = useState("");
  const [amount, setAmount] = useState("");
  const [paidBy, setPaidBy] = useState("");

  // How to divide the cost: "equal", "amounts" (exact $), or "percent".
  const [mode, setMode] = useState("equal");

  // For "equal": which people are included (a set of names).
  const [included, setIncluded] = useState(() => new Set(people));

  // For "amounts"/"percent": what the user typed next to each person.
  // Shape: { Alex: "10", Sam: "20" }
  const [custom, setCustom] = useState({});

  const [saveAsTemplate, setSaveAsTemplate] = useState(false);
  const [error, setError] = useState("");

  const amountNum = parseFloat(amount) || 0;

  // Toggle a person in/out for equal-split mode.
  function toggleIncluded(name) {
    const next = new Set(included);
    if (next.has(name)) next.delete(name);
    else next.add(name);
    setIncluded(next);
  }

  // Update a per-person custom value (for amounts/percent mode).
  function setCustomValue(name, value) {
    setCustom({ ...custom, [name]: value });
  }

  // --- Work out the live "shares" (how many dollars each person owes) ---
  // Returns { shares, problem } where problem is a human message if it doesn't add up.
  function computeShares() {
    if (mode === "equal") {
      const names = people.filter((p) => included.has(p));
      if (names.length === 0) return { shares: {}, problem: "Pick at least one person." };
      const each = amountNum / names.length;
      const shares = {};
      names.forEach((n) => (shares[n] = each));
      return { shares, problem: "" };
    }

    if (mode === "amounts") {
      const shares = {};
      let sum = 0;
      people.forEach((n) => {
        const v = parseFloat(custom[n]) || 0;
        if (v > 0) shares[n] = v;
        sum += v;
      });
      const off = Math.round((amountNum - sum) * 100) / 100;
      if (off !== 0)
        return { shares, problem: `Amounts must add up to $${amountNum.toFixed(2)} (off by $${off.toFixed(2)}).` };
      return { shares, problem: "" };
    }

    // mode === "percent"
    const shares = {};
    let sumPct = 0;
    people.forEach((n) => {
      const pct = parseFloat(custom[n]) || 0;
      if (pct > 0) shares[n] = (amountNum * pct) / 100;
      sumPct += pct;
    });
    const offPct = Math.round((100 - sumPct) * 100) / 100;
    if (offPct !== 0)
      return { shares, problem: `Percentages must add up to 100% (off by ${offPct}%).` };
    return { shares, problem: "" };
  }

  function handleAdd() {
    setError("");
    if (desc.trim() === "") return setError("Add a description.");
    if (amountNum <= 0) return setError("Enter an amount greater than 0.");
    if (paidBy === "") return setError("Choose who paid.");

    const { shares, problem } = computeShares();
    if (problem) return setError(problem);

    const expense = {
      description: desc.trim(),
      amount: amountNum,
      paidBy,
      shares,
    };
    onAddExpense(expense);
    if (saveAsTemplate) onSaveTemplate(expense);

    // Reset the form.
    setDesc("");
    setAmount("");
    setPaidBy("");
    setCustom({});
    setSaveAsTemplate(false);
  }

  // A small live hint under the split editor showing what's left to assign.
  const liveHint = (() => {
    if (amountNum <= 0) return null;
    if (mode === "equal") {
      const n = people.filter((p) => included.has(p)).length || 1;
      return `Splitting $${amountNum.toFixed(2)} evenly = $${(amountNum / n).toFixed(2)} each`;
    }
    if (mode === "amounts") {
      const sum = people.reduce((s, n) => s + (parseFloat(custom[n]) || 0), 0);
      return `Assigned $${sum.toFixed(2)} of $${amountNum.toFixed(2)}`;
    }
    const sumPct = people.reduce((s, n) => s + (parseFloat(custom[n]) || 0), 0);
    return `Assigned ${sumPct}% of 100%`;
  })();

  return (
    <div>
      {/* Top row: description, amount, who paid */}
      <div className="grid gap-3 sm:grid-cols-3">
        <Input placeholder="Description" value={desc} onChange={(e) => setDesc(e.target.value)} />
        <Input
          type="number"
          placeholder="Amount"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
        />
        <select
          value={paidBy}
          onChange={(e) => setPaidBy(e.target.value)}
          className="h-10 rounded-md border border-slate-200 bg-white px-3 text-sm outline-none focus:ring-2 focus:ring-slate-200"
        >
          <option value="">Paid by…</option>
          {people.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
      </div>

      {/* Split-mode selector (a "segmented control") */}
      <div className="mt-4 flex gap-1 rounded-lg bg-slate-100 p-1 text-sm">
        {[
          { id: "equal", label: "Split equally" },
          { id: "amounts", label: "Exact $" },
          { id: "percent", label: "Percent %" },
        ].map((m) => (
          <button
            key={m.id}
            onClick={() => setMode(m.id)}
            className={`flex-1 rounded-md py-1.5 font-medium transition ${
              mode === m.id ? "bg-white shadow-sm" : "text-slate-500 hover:text-slate-800"
            }`}
          >
            {m.label}
          </button>
        ))}
      </div>

      {/* Per-person split editor */}
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
                  checked={included.has(name)}
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

      {/* Save-as-template + Add button */}
      <div className="mt-4 flex items-center justify-between">
        <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-600">
          <input
            type="checkbox"
            checked={saveAsTemplate}
            onChange={(e) => setSaveAsTemplate(e.target.checked)}
            className="h-4 w-4 rounded border-slate-300"
          />
          🔁 Save as recurring template
        </label>
        <Button onClick={handleAdd}>Add expense</Button>
      </div>
    </div>
  );
}
