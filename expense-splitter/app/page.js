"use client"; // tells Next.js this page runs in the browser (needed for useState).

import { useState } from "react";
import { settleUp } from "@/lib/settle";

export default function Home() {
  // --- STATE ---
  // "state" is the app's live memory while it's open in the browser.
  // useState gives us a value and a function to change it. Changing it
  // automatically re-draws the screen.

  // The household members. Starts with two example names.
  const [people, setPeople] = useState(["Alex", "Sam"]);

  // The logged expenses. Each one is { description, amount, paidBy }.
  const [expenses, setExpenses] = useState([]);

  // Debts that have already been paid off in real life.
  // Each one is { from, to, amount }.
  const [settlements, setSettlements] = useState([]);

  // Temporary values for the input boxes (what the user is currently typing).
  const [newPerson, setNewPerson] = useState("");
  const [desc, setDesc] = useState("");
  const [amount, setAmount] = useState("");
  const [paidBy, setPaidBy] = useState("");

  // --- ACTIONS ---

  // Add a new person to the list.
  function addPerson() {
    const name = newPerson.trim();
    if (name === "") return; // ignore empty input
    if (people.includes(name)) return; // no duplicate names
    setPeople([...people, name]); // [...people, name] = old list plus the new name
    setNewPerson(""); // clear the input box
  }

  // Remove a person (and any expenses they paid for, to keep things consistent).
  function removePerson(name) {
    setPeople(people.filter((p) => p !== name));
    setExpenses(expenses.filter((e) => e.paidBy !== name));
  }

  // Add a new expense.
  function addExpense() {
    const value = parseFloat(amount); // turn the typed text into a number
    if (desc.trim() === "" || isNaN(value) || value <= 0 || paidBy === "") {
      return; // ignore incomplete or invalid input
    }
    setExpenses([
      ...expenses,
      { description: desc.trim(), amount: value, paidBy },
    ]);
    // Clear the form.
    setDesc("");
    setAmount("");
    setPaidBy("");
  }

  // Remove a single expense by its position in the list.
  function removeExpense(index) {
    setExpenses(expenses.filter((_, i) => i !== index));
  }

  // Mark a suggested payment as paid. We record it as a real settlement,
  // so the math updates and the debt correctly disappears.
  function markAsPaid(transaction) {
    setSettlements([...settlements, transaction]);
  }

  // Run the math every time the screen draws, using our settle.js brain.
  // We now also pass in the settlements so paid-off debts are accounted for.
  const { total, perPersonShare, transactions } = settleUp(
    people,
    expenses,
    settlements
  );

  return (
    <main className="mx-auto max-w-2xl px-4 py-10">
      <header className="mb-6 text-center">
        <h1 className="text-3xl font-bold tracking-tight">
          🏠 Household Expense Splitter
        </h1>
        <p className="mt-2 text-slate-500">
          Add your flatmates, log expenses, and see who owes whom.
        </p>
      </header>

      {/* ---------- HERO: total household spend ---------- */}
      <div className="mb-6 rounded-2xl bg-gradient-to-br from-slate-900 to-slate-700 p-6 text-center shadow-lg">
        <p className="text-sm font-medium uppercase tracking-wide text-slate-300">
          Total household spend
        </p>
        <p className="mt-1 text-5xl font-bold text-white">
          ${total.toFixed(2)}
        </p>
        <p className="mt-2 text-sm text-slate-300">
          Split between {people.length}{" "}
          {people.length === 1 ? "person" : "people"} · $
          {perPersonShare.toFixed(2)} each
        </p>
      </div>

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

        {/* Show each person as a removable "chip". */}
        <div className="mt-4 flex flex-wrap gap-2">
          {people.length === 0 && (
            <p className="text-sm text-slate-400">No people yet — add someone above.</p>
          )}
          {people.map((name) => (
            <span
              key={name}
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
            </span>
          ))}
        </div>
      </Card>

      {/* ---------- SECTION 2: ADD AN EXPENSE ---------- */}
      <Card>
        <SectionTitle step="2" title="Add an expense" />
        <div className="grid gap-3 sm:grid-cols-3">
          <Input
            placeholder="Description"
            value={desc}
            onChange={(e) => setDesc(e.target.value)}
          />
          <Input
            type="number"
            placeholder="Amount"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
          />
          {/* A dropdown of who paid. Built from the people list. */}
          <select
            value={paidBy}
            onChange={(e) => setPaidBy(e.target.value)}
            className="h-10 rounded-md border border-slate-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-slate-400"
          >
            <option value="">Paid by…</option>
            {people.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </div>
        <div className="mt-3">
          <Button onClick={addExpense}>Add expense</Button>
        </div>

        {/* List of logged expenses. */}
        <div className="mt-5 divide-y divide-slate-100">
          {expenses.length === 0 && (
            <p className="text-sm text-slate-400">No expenses logged yet.</p>
          )}
          {expenses.map((e, index) => (
            <div key={index} className="flex items-center justify-between py-2 text-sm">
              <span>
                <span className="font-medium">{e.description}</span>{" "}
                <span className="text-slate-400">· paid by {e.paidBy}</span>
              </span>
              <span className="flex items-center gap-3">
                <span className="font-semibold">${e.amount.toFixed(2)}</span>
                <button
                  onClick={() => removeExpense(index)}
                  className="text-slate-400 hover:text-red-500"
                  aria-label="Remove expense"
                >
                  ✕
                </button>
              </span>
            </div>
          ))}
        </div>
      </Card>

      {/* ---------- SECTION 3: BALANCES ---------- */}
      <Card>
        <SectionTitle step="3" title="Balances — who owes whom" />

        <div className="space-y-3">
          {transactions.length === 0 ? (
            <div className="rounded-lg bg-green-50 px-4 py-6 text-center">
              <p className="text-2xl">🎉</p>
              <p className="mt-1 text-sm font-medium text-green-700">
                Everyone is settled up — no payments needed.
              </p>
            </div>
          ) : (
            transactions.map((t, i) => (
              <div
                key={i}
                className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm"
              >
                {/* Left: who pays whom, with colored avatars */}
                <div className="flex items-center gap-3">
                  <Avatar name={t.from} tone="red" />
                  <div className="text-sm">
                    <p>
                      <span className="font-semibold text-red-600">{t.from}</span>{" "}
                      needs to pay{" "}
                      <span className="font-semibold text-green-600">{t.to}</span>
                    </p>
                    <p className="text-lg font-bold text-slate-900">
                      ${t.amount.toFixed(2)}
                    </p>
                  </div>
                </div>

                {/* Right: the action button */}
                <button
                  onClick={() => markAsPaid(t)}
                  className="shrink-0 rounded-md bg-green-600 px-3 py-2 text-sm font-medium text-white transition hover:bg-green-700"
                >
                  ✓ Mark as Paid
                </button>
              </div>
            ))
          )}
        </div>

        {/* A small log of debts already settled, so it's clear what was paid. */}
        {settlements.length > 0 && (
          <div className="mt-5 border-t border-slate-100 pt-4">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
              Already settled
            </p>
            <div className="space-y-1">
              {settlements.map((s, i) => (
                <p key={i} className="text-sm text-slate-400 line-through">
                  {s.from} paid {s.to} ${s.amount.toFixed(2)}
                </p>
              ))}
            </div>
          </div>
        )}
      </Card>

      <p className="mt-6 text-center text-xs text-slate-400">
        Data is kept in memory only — refreshing the page resets everything.
      </p>
    </main>
  );
}

/* ---------- Small reusable UI pieces (Shadcn-style, hand-written) ---------- */

// A white "card" container with padding and a soft shadow.
function Card({ children }) {
  return (
    <section className="mb-5 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      {children}
    </section>
  );
}

// A numbered section heading.
function SectionTitle({ step, title }) {
  return (
    <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold">
      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-900 text-xs text-white">
        {step}
      </span>
      {title}
    </h2>
  );
}

// A styled text input. {...props} passes through value, onChange, etc.
function Input(props) {
  return (
    <input
      {...props}
      className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-slate-400"
    />
  );
}

// A small colored circle showing a person's first initial.
function Avatar({ name, tone = "slate" }) {
  const tones = {
    red: "bg-red-100 text-red-700",
    green: "bg-green-100 text-green-700",
    slate: "bg-slate-100 text-slate-700",
  };
  const initial = name ? name.charAt(0).toUpperCase() : "?";
  return (
    <span
      className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-sm font-semibold ${tones[tone]}`}
    >
      {initial}
    </span>
  );
}

// A styled button.
function Button({ children, onClick }) {
  return (
    <button
      onClick={onClick}
      className="h-10 shrink-0 rounded-md bg-slate-900 px-4 text-sm font-medium text-white transition hover:bg-slate-700"
    >
      {children}
    </button>
  );
}
