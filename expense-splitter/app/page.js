"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { settleUp } from "@/lib/settle";
import { splitCents, formatCents, toCents, categoryOf, CURRENCIES } from "@/lib/money";
import { useLocalStorage } from "@/lib/useLocalStorage";
import { ExpenseForm } from "@/components/ExpenseForm";
import { Charts } from "@/components/Charts";
import { Card, SectionTitle, Input, Button, Avatar, AnimatedMoney } from "@/components/ui";

const uid = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 7);

const itemMotion = {
  layout: true,
  initial: { opacity: 0, y: -10, scale: 0.98 },
  animate: { opacity: 1, y: 0, scale: 1 },
  exit: { opacity: 0, x: -30, scale: 0.95 },
  transition: { type: "spring", stiffness: 400, damping: 30 },
};

export default function Home() {
  // Core data (saved to the browser).
  const [people, setPeople, hP] = useLocalStorage("es_people", ["Alex", "Sam"]);
  const [expenses, setExpenses, hE] = useLocalStorage("es_expenses", []);
  const [settlements, setSettlements, hS] = useLocalStorage("es_settlements", []);
  const [templates, setTemplates, hT] = useLocalStorage("es_templates", []);
  const [activity, setActivity, hA] = useLocalStorage("es_activity", []);

  // Settings.
  const [dark, setDark] = useLocalStorage("es_dark", false);
  const [currency, setCurrency] = useLocalStorage("es_currency", "USD");
  const symbol = (CURRENCIES.find((c) => c.code === currency) || CURRENCIES[0]).symbol;

  const ready = hP && hE && hS && hT && hA;

  // Transient UI state.
  const [newPerson, setNewPerson] = useState("");
  const [showActivity, setShowActivity] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [search, setSearch] = useState("");
  const [catFilter, setCatFilter] = useState("all");
  const [history, setHistory] = useState([]); // for Undo
  const fileInputRef = useRef(null);

  const editing = expenses.find((e) => e.id === editingId) || null;

  // Keep the <html> dark class in sync with the setting.
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);

  function logActivity(message) {
    setActivity((prev) => [{ id: uid(), time: Date.now(), message }, ...prev].slice(0, 50));
  }

  // Save a snapshot of the data BEFORE a change, so "Undo" can restore it.
  function snapshot() {
    setHistory((h) => [...h.slice(-9), { people, expenses, settlements, templates }]);
  }
  function undo() {
    const last = history[history.length - 1];
    if (!last) return;
    setPeople(last.people);
    setExpenses(last.expenses);
    setSettlements(last.settlements);
    setTemplates(last.templates);
    setHistory(history.slice(0, -1));
    logActivity("Undid the last change");
  }

  // --- PEOPLE ---
  function addPerson() {
    const name = newPerson.trim();
    if (name === "" || people.includes(name)) return;
    snapshot();
    setPeople([...people, name]);
    setNewPerson("");
    logActivity(`Added ${name} to the household`);
  }

  function removePerson(name) {
    if (!window.confirm(`Remove ${name}? Expenses they paid will be deleted, and their share of other expenses will be re-split.`)) return;
    snapshot();
    let next = expenses.filter((e) => e.paidBy !== name);
    next = next
      .map((e) => {
        if (e.shares[name] === undefined) return e;
        const removed = e.shares[name];
        const others = Object.keys(e.shares).filter((n) => n !== name);
        if (others.length === 0) return null;
        const newShares = { ...e.shares };
        delete newShares[name];
        const add = splitCents(removed, others.map((n) => e.shares[n] || 1));
        others.forEach((n, i) => (newShares[n] += add[i]));
        return { ...e, shares: newShares };
      })
      .filter(Boolean);
    setExpenses(next);
    setSettlements(settlements.filter((s) => s.from !== name && s.to !== name));
    setTemplates(templates.filter((t) => t.paidBy !== name));
    setPeople(people.filter((p) => p !== name));
    if (editing && editing.paidBy === name) setEditingId(null);
    logActivity(`Removed ${name}`);
  }

  function renamePerson(oldName) {
    const input = window.prompt(`Rename ${oldName} to:`, oldName);
    if (input === null) return;
    const newName = input.trim();
    if (newName === "" || newName === oldName) return;
    if (people.includes(newName)) return window.alert("That name is already taken.");
    snapshot();
    const renameShares = (shares) => {
      if (shares[oldName] === undefined) return shares;
      const { [oldName]: v, ...rest } = shares;
      return { ...rest, [newName]: v };
    };
    setPeople(people.map((p) => (p === oldName ? newName : p)));
    setExpenses(expenses.map((e) => ({
      ...e,
      paidBy: e.paidBy === oldName ? newName : e.paidBy,
      shares: renameShares(e.shares),
    })));
    setSettlements(settlements.map((s) => ({
      from: s.from === oldName ? newName : s.from,
      to: s.to === oldName ? newName : s.to,
      amount: s.amount,
    })));
    setTemplates(templates.map((t) => ({
      ...t,
      paidBy: t.paidBy === oldName ? newName : t.paidBy,
      shares: renameShares(t.shares),
    })));
    logActivity(`Renamed ${oldName} to ${newName}`);
  }

  // --- EXPENSES ---
  function addExpense(expense) {
    snapshot();
    const full = { ...expense, id: uid(), date: expense.date || new Date().toISOString() };
    setExpenses([full, ...expenses]);
    logActivity(`${expense.paidBy} added “${expense.description}” — ${formatCents(expense.amount, symbol)}`);
  }
  function updateExpense(updated) {
    snapshot();
    setExpenses(expenses.map((e) => (e.id === updated.id ? updated : e)));
    setEditingId(null);
    logActivity(`Edited “${updated.description}”`);
  }
  function removeExpense(id) {
    const e = expenses.find((x) => x.id === id);
    if (!e) return;
    if (!window.confirm(`Delete “${e.description}”?`)) return;
    snapshot();
    setExpenses(expenses.filter((x) => x.id !== id));
    if (editingId === id) setEditingId(null);
    logActivity(`Deleted “${e.description}”`);
  }

  // --- SETTLEMENTS (with partial payments) ---
  function markAsPaid(t) {
    const input = window.prompt(
      `How much did ${t.from} pay ${t.to}? (up to ${formatCents(t.amount, symbol)})`,
      (t.amount / 100).toFixed(2)
    );
    if (input === null) return;
    let cents = toCents(input);
    if (cents <= 0) return;
    if (cents > t.amount) cents = t.amount;
    snapshot();
    setSettlements([...settlements, { from: t.from, to: t.to, amount: cents }]);
    logActivity(`${t.from} paid ${t.to} ${formatCents(cents, symbol)}`);
  }

  // --- RECURRING TEMPLATES ---
  function saveTemplate(expense) {
    setTemplates([...templates, { ...expense, id: uid() }]);
    logActivity(`Saved recurring template “${expense.description}”`);
  }
  function addFromTemplate(t) {
    if (!people.includes(t.paidBy)) {
      return window.alert(`${t.paidBy} (who paid) is no longer in the household. Remove or recreate this template.`);
    }
    const names = Object.keys(t.shares).filter((n) => people.includes(n));
    if (names.length === 0) {
      return window.alert("None of this template's people are still in the household.");
    }
    const parts = splitCents(t.amount, names.map((n) => t.shares[n]));
    const shares = {};
    names.forEach((n, i) => (shares[n] = parts[i]));
    addExpense({ description: t.description, amount: t.amount, paidBy: t.paidBy, category: t.category || "general", shares });
  }
  function removeTemplate(id) {
    snapshot();
    setTemplates(templates.filter((t) => t.id !== id));
  }

  // --- BACKUP ---
  function exportData() {
    const data = { version: 2, people, expenses, settlements, templates, activity, currency };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "expense-splitter-backup.json";
    a.click();
    URL.revokeObjectURL(url);
  }
  function importData(file) {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const d = JSON.parse(reader.result);
        snapshot();
        if (d.people) setPeople(d.people);
        if (d.expenses) setExpenses(d.expenses);
        if (d.settlements) setSettlements(d.settlements);
        if (d.templates) setTemplates(d.templates);
        if (d.activity) setActivity(d.activity);
        if (d.currency) setCurrency(d.currency);
        logActivity("Restored data from a backup file");
      } catch {
        window.alert("Sorry — that file couldn't be read as a backup.");
      }
    };
    reader.readAsText(file);
  }

  const { total, transactions } = settleUp(people, expenses, settlements);
  const perPerson = people.length > 0 ? Math.round(total / people.length) : 0;

  // Apply search + category filter to the displayed expense list.
  const visibleExpenses = expenses.filter((e) => {
    const matchesText = e.description.toLowerCase().includes(search.toLowerCase());
    const matchesCat = catFilter === "all" || (e.category || "general") === catFilter;
    return matchesText && matchesCat;
  });

  if (!ready) {
    return (
      <main className="mx-auto max-w-2xl px-4 py-20 text-center text-slate-400">
        Loading your household…
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-2xl px-4 py-10">
      <header className="mb-6 flex items-start justify-between gap-3">
        <div className="text-center sm:text-left">
          <h1 className="text-3xl font-bold tracking-tight">🏠 Household Expense Splitter</h1>
          <p className="mt-2 text-slate-500 dark:text-slate-400">
            Add your flatmates, log expenses, and see who owes whom.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            aria-label="Currency"
            value={currency}
            onChange={(e) => setCurrency(e.target.value)}
            className="h-9 rounded-md border border-slate-200 bg-white px-2 text-sm dark:border-slate-700 dark:bg-slate-800"
          >
            {CURRENCIES.map((c) => (
              <option key={c.code} value={c.code}>
                {c.symbol} {c.code}
              </option>
            ))}
          </select>
          <button
            onClick={() => setDark((d) => !d)}
            aria-label="Toggle dark mode"
            title="Toggle dark mode"
            className="flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 bg-white text-base dark:border-slate-700 dark:bg-slate-800"
          >
            {dark ? "☀️" : "🌙"}
          </button>
        </div>
      </header>

      {/* HERO */}
      <motion.div layout className="mb-6 rounded-2xl bg-gradient-to-br from-slate-900 to-slate-700 p-6 text-center shadow-lg">
        <p className="text-sm font-medium uppercase tracking-wide text-slate-300">Total household spend</p>
        <AnimatedMoney cents={total} symbol={symbol} className="mt-1 block text-5xl font-bold text-white" />
        <p className="mt-2 text-sm text-slate-300">
          Split across {people.length} {people.length === 1 ? "person" : "people"} · about {formatCents(perPerson, symbol)} each
        </p>
      </motion.div>

      {/* PEOPLE */}
      <Card>
        <SectionTitle icon="👥" title="People in the household" />
        <div className="flex gap-2">
          <Input
            placeholder="Add a name (e.g. Jordan)"
            value={newPerson}
            onChange={(e) => setNewPerson(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && addPerson()}
          />
          <Button onClick={addPerson}>Add</Button>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {people.length === 0 && <p className="text-sm text-slate-400">No people yet — add someone above.</p>}
          <AnimatePresence>
            {people.map((name) => (
              <motion.span
                key={name}
                {...itemMotion}
                className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-sm font-medium dark:bg-slate-700"
              >
                {name}
                <button onClick={() => renamePerson(name)} className="text-slate-400 hover:text-slate-700 dark:hover:text-slate-200" aria-label={`Rename ${name}`} title="Rename">✎</button>
                <button onClick={() => removePerson(name)} className="text-slate-400 hover:text-red-500" aria-label={`Remove ${name}`} title="Remove">✕</button>
              </motion.span>
            ))}
          </AnimatePresence>
        </div>
      </Card>

      {/* ADD / EDIT EXPENSE */}
      <Card>
        <SectionTitle icon="➕" title="Add an expense" />
        <ExpenseForm
          people={people}
          symbol={symbol}
          onAddExpense={addExpense}
          onSaveTemplate={saveTemplate}
          editing={editing}
          onUpdateExpense={updateExpense}
          onCancelEdit={() => setEditingId(null)}
        />

        {/* Search + category filter */}
        {expenses.length > 0 && (
          <div className="mt-5 flex gap-2">
            <Input placeholder="Search expenses…" value={search} onChange={(e) => setSearch(e.target.value)} />
            <select
              aria-label="Filter by category"
              value={catFilter}
              onChange={(e) => setCatFilter(e.target.value)}
              className="h-10 rounded-md border border-slate-200 bg-white px-2 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
            >
              <option value="all">All</option>
              {[...new Set(expenses.map((e) => e.category || "general"))].map((id) => (
                <option key={id} value={id}>
                  {categoryOf(id).emoji} {categoryOf(id).label}
                </option>
              ))}
            </select>
          </div>
        )}

        <div className="mt-3 space-y-2">
          {expenses.length === 0 && (
            <p className="text-sm text-slate-400">No expenses yet — add your first one above to get started.</p>
          )}
          {expenses.length > 0 && visibleExpenses.length === 0 && (
            <p className="text-sm text-slate-400">No expenses match your search.</p>
          )}
          <AnimatePresence>
            {visibleExpenses.map((e) => (
              <motion.div
                key={e.id}
                {...itemMotion}
                className={`flex items-center justify-between gap-3 rounded-lg border px-3 py-2 text-sm ${
                  editingId === e.id
                    ? "border-amber-300 bg-amber-50 dark:border-amber-500/50 dark:bg-amber-500/10"
                    : "border-slate-100 bg-slate-50 dark:border-slate-700 dark:bg-slate-900/50"
                }`}
              >
                <span>
                  <span className="mr-1">{categoryOf(e.category).emoji}</span>
                  <span className="font-medium">{e.description}</span>{" "}
                  <span className="text-slate-400">· {e.paidBy} · {new Date(e.date).toLocaleDateString()}</span>
                </span>
                <span className="flex items-center gap-3">
                  <span className="font-semibold">{formatCents(e.amount, symbol)}</span>
                  <button onClick={() => setEditingId(e.id)} className="text-slate-400 hover:text-slate-700 dark:hover:text-slate-200" aria-label="Edit expense" title="Edit">✎</button>
                  <button onClick={() => removeExpense(e.id)} className="text-slate-400 hover:text-red-500" aria-label="Delete expense" title="Delete">✕</button>
                </span>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </Card>

      {/* INSIGHTS */}
      <Card>
        <SectionTitle icon="📊" title="Spending insights" />
        <Charts people={people} expenses={expenses} symbol={symbol} />
      </Card>

      {/* RECURRING */}
      {templates.length > 0 && (
        <Card>
          <SectionTitle icon="🔁" title="Recurring expenses" />
          <p className="mb-3 text-xs text-slate-500">One click adds these for the current month (e.g. rent, internet).</p>
          <div className="space-y-2">
            <AnimatePresence>
              {templates.map((t) => (
                <motion.div
                  key={t.id}
                  {...itemMotion}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700"
                >
                  <span>
                    <span className="mr-1">{categoryOf(t.category).emoji}</span>
                    <span className="font-medium">{t.description}</span>{" "}
                    <span className="text-slate-400">· {formatCents(t.amount, symbol)} · paid by {t.paidBy}</span>
                  </span>
                  <span className="flex items-center gap-2">
                    <Button variant="ghost" onClick={() => addFromTemplate(t)}>+ Add this month</Button>
                    <button onClick={() => removeTemplate(t.id)} className="text-slate-400 hover:text-red-500" aria-label="Remove template" title="Remove">✕</button>
                  </span>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        </Card>
      )}

      {/* BALANCES */}
      <Card>
        <SectionTitle icon="💸" title="Balances — who owes whom" />
        <div className="space-y-3">
          {transactions.length === 0 ? (
            <div className="rounded-lg bg-green-50 px-4 py-6 text-center dark:bg-green-900/20">
              <p className="text-2xl">🎉</p>
              <p className="mt-1 text-sm font-medium text-green-700 dark:text-green-300">Everyone is settled up — no payments needed.</p>
            </div>
          ) : (
            <AnimatePresence>
              {transactions.map((t) => (
                <motion.div
                  key={`${t.from}->${t.to}`}
                  {...itemMotion}
                  className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm dark:border-slate-700 dark:bg-slate-800"
                >
                  <div className="flex items-center gap-3">
                    <Avatar name={t.from} tone="red" />
                    <span aria-hidden className="text-slate-400">→</span>
                    <Avatar name={t.to} tone="green" />
                    <div className="text-sm">
                      <p>
                        <span className="font-semibold text-red-600 dark:text-red-400">{t.from}</span> pays{" "}
                        <span className="font-semibold text-green-600 dark:text-green-400">{t.to}</span>
                      </p>
                      <p className="text-lg font-bold">{formatCents(t.amount, symbol)}</p>
                    </div>
                  </div>
                  <Button variant="green" onClick={() => markAsPaid(t)}>✓ Mark as Paid</Button>
                </motion.div>
              ))}
            </AnimatePresence>
          )}
        </div>
      </Card>

      {/* ACTIVITY LOG */}
      <Card>
        <SectionTitle
          icon="📜"
          title="Activity log"
          right={
            <div className="flex gap-2">
              <Button variant="ghost" onClick={undo} title="Undo last change">↩ Undo</Button>
              <Button variant="ghost" onClick={() => setShowActivity((s) => !s)}>
                {showActivity ? "Hide" : "Show"}
              </Button>
            </div>
          }
        />
        <AnimatePresence initial={false}>
          {showActivity && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.25 }}
              className="overflow-hidden"
            >
              {activity.length === 0 ? (
                <p className="text-sm text-slate-400">No activity yet.</p>
              ) : (
                <div className="space-y-1">
                  {activity.map((a) => (
                    <p key={a.id} className="text-sm text-slate-500 dark:text-slate-400">
                      <span className="text-slate-400 dark:text-slate-500">
                        {new Date(a.time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </span>{" "}
                      — {a.message}
                    </p>
                  ))}
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </Card>

      {/* BACKUP */}
      <Card>
        <SectionTitle icon="💾" title="Backup & restore" />
        <p className="mb-3 text-xs text-slate-500">
          Your data lives in this browser only. Export a file to keep a backup or move it to another device.
        </p>
        <div className="flex gap-2">
          <Button variant="ghost" onClick={exportData}>⬇ Export backup</Button>
          <Button variant="ghost" onClick={() => fileInputRef.current?.click()}>⬆ Import backup</Button>
          <input
            ref={fileInputRef}
            type="file"
            accept="application/json"
            className="hidden"
            onChange={(e) => {
              if (e.target.files?.[0]) importData(e.target.files[0]);
              e.target.value = "";
            }}
          />
        </div>
      </Card>

      <p className="mt-6 text-center text-xs text-slate-400">
        Your data is saved in this browser only — it stays private to you.
      </p>
    </main>
  );
}
