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

  // Run the math every time the screen draws, using our settle.js brain.
  const { total, perPersonShare, transactions } = settleUp(people, expenses);

  return (
    <main className="mx-auto max-w-2xl px-4 py-10">
      <header className="mb-8 text-center">
        <h1 className="text-3xl font-bold tracking-tight">
          🏠 Household Expense Splitter
        </h1>
        <p className="mt-2 text-slate-500">
          Add your flatmates, log expenses, and see who owes whom.
        </p>
      </header>

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

      {/* ---------- SECTION 3: SUMMARY ---------- */}
      <Card>
        <SectionTitle step="3" title="Summary — who owes whom" />
        <div className="flex justify-between rounded-md bg-slate-50 px-4 py-3 text-sm">
          <span>Total spent</span>
          <span className="font-semibold">${total.toFixed(2)}</span>
        </div>
        <div className="mt-1 flex justify-between rounded-md bg-slate-50 px-4 py-3 text-sm">
          <span>Fair share each ({people.length} people)</span>
          <span className="font-semibold">${perPersonShare.toFixed(2)}</span>
        </div>

        <div className="mt-4 space-y-2">
          {transactions.length === 0 ? (
            <p className="text-sm text-slate-400">
              Everyone is settled up — no payments needed. 🎉
            </p>
          ) : (
            transactions.map((t, i) => (
              <div
                key={i}
                className="flex items-center justify-between rounded-md border border-slate-200 px-4 py-2 text-sm"
              >
                <span>
                  <span className="font-medium text-red-600">{t.from}</span> owes{" "}
                  <span className="font-medium text-green-600">{t.to}</span>
                </span>
                <span className="font-semibold">${t.amount.toFixed(2)}</span>
              </div>
            ))
          )}
        </div>
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
