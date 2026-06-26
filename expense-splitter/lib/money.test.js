import { describe, it, expect } from "vitest";
import { toCents, formatCents, categoryOf } from "./money.js";

describe("money helpers", () => {
  it("converts dollar strings to integer cents", () => {
    expect(toCents("12.50")).toBe(1250);
    expect(toCents("0.1")).toBe(10);
    expect(toCents("")).toBe(0);
    expect(toCents("abc")).toBe(0);
  });

  it("formats cents with a currency symbol", () => {
    expect(formatCents(1250)).toBe("$12.50");
    expect(formatCents(1250, "€")).toBe("€12.50");
    expect(formatCents(0, "₹")).toBe("₹0.00");
  });

  it("looks up a category, falling back to the first one", () => {
    expect(categoryOf("food").label).toBe("Food & Drink");
    expect(categoryOf("does-not-exist").id).toBe("general");
  });
});
