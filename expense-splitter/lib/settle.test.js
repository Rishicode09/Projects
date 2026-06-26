import { describe, it, expect } from "vitest";
import { settleUp } from "./settle.js";
import { splitCents } from "./money.js";

describe("settleUp (amounts in cents)", () => {
  it("is empty when there are no expenses", () => {
    const { total, transactions } = settleUp(["A", "B"], [], []);
    expect(total).toBe(0);
    expect(transactions).toEqual([]);
  });

  it("settles a simple equal split", () => {
    // A paid $30, split $15/$15. B should owe A $15.
    const expenses = [{ description: "x", amount: 3000, paidBy: "A", shares: { A: 1500, B: 1500 } }];
    const { transactions } = settleUp(["A", "B"], expenses, []);
    expect(transactions).toEqual([{ from: "B", to: "A", amount: 1500 }]);
  });

  it("clears a debt once it is marked paid (settlement)", () => {
    const expenses = [{ description: "x", amount: 2000, paidBy: "A", shares: { A: 1000, B: 1000 } }];
    const settlements = [{ from: "B", to: "A", amount: 1000 }];
    const { transactions } = settleUp(["A", "B"], expenses, settlements);
    expect(transactions).toEqual([]);
  });

  it("balances always sum to exactly zero (no lost pennies)", () => {
    const expenses = [{ description: "x", amount: 1000, paidBy: "A", shares: { A: 334, B: 333, C: 333 } }];
    const { balances } = settleUp(["A", "B", "C"], expenses, []);
    const sum = Object.values(balances).reduce((s, v) => s + v, 0);
    expect(sum).toBe(0);
  });
});

describe("splitCents", () => {
  it("distributes leftover pennies so parts sum to the total", () => {
    const parts = splitCents(1000, [1, 1, 1]); // $10 three ways
    expect(parts.reduce((s, v) => s + v, 0)).toBe(1000);
    expect(parts).toEqual([334, 333, 333]);
  });

  it("handles percentage weights exactly", () => {
    const parts = splitCents(1000, [50, 30, 20]);
    expect(parts).toEqual([500, 300, 200]);
  });
});
