"use client"; // this page runs in the browser (needed for state + localStorage).

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { settleUp } from "@/lib/settle";
import { useLocalStorage } from "@/lib/useLocalStorage";
import { ExpenseForm } from "@/components/ExpenseForm";
import { Card, SectionTitle, Input, Button, Avatar, AnimatedMoney } from "@/components/ui";

// A tiny helper to make a unique id for each new item.
const uid = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 7);

// Shared animation settings for items entering/leaving a list.
const itemMotion = {
  layout: true,
  initial: { opacity: 0, y: -10, scale: 0.98 },
  animate: { opacity: 1, y: 0, scale: 1 },
  exit: { opacity: 0, x: -30, scale: 0.95 },
  transition: { type: "spring", stiffness: 400, damping: 30 },
};

export default function Home() {
  // --- STATE (now saved to the browser, so it survives refreshes) ---
  const [people, setPeople] = useLocalStorage("es_people", ["Alex", "Sam"]);
  const [expenses, setExpenses] = useLocalStorage("es_expenses", []);
  const [settlements, setSettlements] = useLocalStorage("es_settlements", []);
  const [templates, setTemplates] = useLocalStorage("es_templates", []);
  const [activity, setActivity] = useLocalStorage("es_activity", []);

  const [newPerson, setNewPerson] = useState("");
  const [showActivity, setShowActivity] = useState(false);

  // Add a line to the activity log (newest first).
  function logActivity(message) {
    setActivity((prev) => [{ id: uid(), time: Date.now(), message }, ...prev].slice(0, 50));
  }

  // --- PEOPLE ---
  function addPerson() {
    const name = newPerson.trim();
    if (name === "" || people.includes(name)) return;
    setPeople([...people, name]);
    setNewPerson("");
    logActivity(`Added ${name} to the household`);
  }
  function removePerson(name) {
    setPeople(people.filter((p) => p !== name));
    setExpenses(expenses.filter((e) => e.paidBy !== name));
    logActivity(`Removed ${name}`);
  }

  // --- EXPENSES ---
  function addExpense(expense) {
    const full = { ...expense, id: uid(), date: new Date().toISOString() };
    setExpenses([full, ...expenses]);
    logActivity(`${expense.paidBy} added "${expense.description}" — $${expense.amount.toFixed(2)}`);
  }
  function removeExpense(id) {
    const e = expenses.find((x) => x.id === id);
    setExpenses(expenses.filter((x) => x.id !== id));
    if (e) logActivity(`Removed "${e.description}"`);
  }

  // --- SETTLEMENTS ("Mark as Paid") ---
  function markAsPaid(t) {
    setSettlements([...settlements, t]);
    logActivity(`${t.from} paid ${t.to} $${t.amount.toFixed(2)}`);
  }

  // --- RECURRING TEMPLATES ---
  function saveTemplate(expense) {
    setTemplates([...templates, { ...expense, id: uid() }]);
    logActivity(`Saved recurring template "${expense.description}"`);
  }
  function addFromTemplate(t) {
    addExpense({ description: t.description, amount: t.amount, paidBy: t.paidBy, shares: t.shares });
  }
  function removeTemplate(id) {
    setTemplates(templates.filter((t) => t.id !== id));
  }

  // Run the math (re-computed on every render).
  const { total, transactions } = settleUp(people, expenses, settlements);
  const perPerson = people.length > 0 ? total / people.length : 0;

  return (
    <main className="mx-auto max-w-2xl px-4 py-10">
      <header className="mb-6 text-center">
        <h1 className="text-3xl font-bold tracking-tight">🏠 Household Expense Splitter</h1>
        <p className="mt-2 text-slate-500">
          Add your flatmates, log expenses, and see who owes whom.
        </p>
      </header>

      {/* ---------- HERO: total household spend (animated count-up) ---------- */}
      <motion.div
        layout
        className="mb-6 rounded-2xl bg-gradient-to-br from-slate-900 to-slate-700 p-6 text-center shadow-lg"
      >
        <p className="text-sm font-medium uppercase tracking-wide text-slate-300">
          Total household spend
        </p>
        <AnimatedMoney value={total} className="mt-1 block text-5xl font-bold text-white" />
        <p className="mt-2 text-sm text-slate-300">
          Split across {people.length} {people.length === 1 ? "person" : "people"} · about $
          {perPerson.toFixed(2)} each
        </p>
      </motion.div>

      {/* ---------- SECTION 1: PEOPLE ---------- */}
      <Card>
        <SectionTitle step="1" title="People in the household" />
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
          {people.length === 0 && (
            <p className="text-sm text-slate-400">No people yet — add someone above.</p>
          )}
          <AnimatePresence>
            {people.map((name) => (
              <motion.span
                key={name}
                {...itemMotion}
                className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-sm font-medium"
              >
                {name}
                <button
                  onClick={() => removePerson(name)}
                  className="text-slate-400 hover:text-red-500"
                  aria-label={`Remove ${name}`}
                >
                  ✕
                </button>
              </motion.span>
            ))}
          </AnimatePresence>
        </div>
      </Card>

      {/* ---------- SECTION 2: ADD AN EXPENSE ---------- */}
      <Card>
        <SectionTitle step="2" title="Add an expense" />
        <ExpenseForm people={people} onAddExpense={addExpense} onSaveTemplate={saveTemplate} />

        {/* List of logged expenses */}
        <div className="mt-5 space-y-2">
          {expenses.length === 0 && (
            <p className="text-sm text-slate-400">No expenses logged yet.</p>
          )}
          <AnimatePresence>
            {expenses.map((e) => (
              <motion.div
                key={e.id}
                {...itemMotion}
                className="flex items-center justify-between gap-3 rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 text-sm"
              >
                <span>
                  <span className="font-medium">{e.description}</span>{" "}
                  <span className="text-slate-400">
                    · {e.paidBy} · {new Date(e.date).toLocaleDateString()}
                  </span>
                </span>
                <span className="flex items-center gap-3">
                  <span className="font-semibold">${e.amount.toFixed(2)}</span>
                  <button
                    onClick={() => removeExpense(e.id)}
                    className="text-slate-400 hover:text-red-500"
                    aria-label="Remove expense"
                  >
                    ✕
                  </button>
                </span>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </Card>

      {/* ---------- SECTION 3: RECURRING TEMPLATES ---------- */}
      {templates.length > 0 && (
        <Card>
          <SectionTitle step="🔁" title="Recurring expenses" />
          <p className="mb-3 text-xs text-slate-500">
            One click adds these for the current month (e.g. rent, internet).
          </p>
          <div className="space-y-2">
            <AnimatePresence>
              {templates.map((t) => (
                <motion.div
                  key={t.id}
                  {...itemMotion}
                  className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 px-3 py-2 text-sm"
                >
                  <span>
                    <span className="font-medium">{t.description}</span>{" "}
                    <span className="text-slate-400">
                      · ${t.amount.toFixed(2)} · paid by {t.paidBy}
                    </span>
                  </span>
                  <span className="flex items-center gap-2">
                    <Button variant="ghost" onClick={() => addFromTemplate(t)}>
                      + Add this month
                    </Button>
                    <button
                      onClick={() => removeTemplate(t.id)}
                      className="text-slate-400 hover:text-red-500"
                      aria-label="Remove template"
                    >
                      ✕
                    </button>
                  </span>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        </Card>
      )}

      {/* ---------- SECTION 4: BALANCES ---------- */}
      <Card>
        <SectionTitle step="4" title="Balances — who owes whom" />
        <div className="space-y-3">
          {transactions.length === 0 ? (
            <div className="rounded-lg bg-green-50 px-4 py-6 text-center">
              <p className="text-2xl">🎉</p>
              <p className="mt-1 text-sm font-medium text-green-700">
                Everyone is settled up — no payments needed.
              </p>
            </div>
          ) : (
            <AnimatePresence>
              {transactions.map((t) => (
                <motion.div
                  key={`${t.from}->${t.to}`}
                  {...itemMotion}
                  className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm"
                >
                  <div className="flex items-center gap-3">
                    <Avatar name={t.from} tone="red" />
                    <div className="text-sm">
                      <p>
                        <span className="font-semibold text-red-600">{t.from}</span> needs to pay{" "}
                        <span className="font-semibold text-green-600">{t.to}</span>
                      </p>
                      <p className="text-lg font-bold text-slate-900">${t.amount.toFixed(2)}</p>
                    </div>
                  </div>
                  <Button variant="green" onClick={() => markAsPaid(t)}>
                    ✓ Mark as Paid
                  </Button>
                </motion.div>
              ))}
            </AnimatePresence>
          )}
        </div>
      </Card>

      {/* ---------- SECTION 5: ACTIVITY LOG ---------- */}
      <Card>
        <SectionTitle
          step="📜"
          title="Activity log"
          right={
            <Button variant="ghost" onClick={() => setShowActivity((s) => !s)}>
              {showActivity ? "Hide" : "Show"}
            </Button>
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
                    <p key={a.id} className="text-sm text-slate-500">
                      <span className="text-slate-400">
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

      <p className="mt-6 text-center text-xs text-slate-400">
        Your data is saved in this browser only — it stays private to you.
      </p>
    </main>
  );
}
