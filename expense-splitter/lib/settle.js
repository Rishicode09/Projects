// settle.js — the "who owes whom" brain. Everything here is in integer CENTS.
//
//   people      = ["Alex", "Sam"]
//   expenses    = [{ description, amount, paidBy, shares: { Alex: 1500, Sam: 1500 } }]
//                 (amount and every share are in cents)
//   settlements = [{ from: "Sam", to: "Alex", amount: 1500 }]
//
// Returns: { total, balances, transactions } — all amounts in cents.

export function settleUp(people, expenses, settlements = []) {
  // Total spent (cents).
  const total = expenses.reduce((sum, e) => sum + e.amount, 0);

  // Each person's balance: (money paid out) minus (their share of every expense).
  //   positive => household owes them ;  negative => they owe.
  const balances = {};
  people.forEach((name) => {
    balances[name] = 0;
  });

  expenses.forEach((e) => {
    if (balances[e.paidBy] !== undefined) {
      balances[e.paidBy] += e.amount; // payer is credited what they laid out
    }
    const shares = e.shares || {};
    Object.keys(shares).forEach((name) => {
      if (balances[name] !== undefined) {
        balances[name] -= shares[name]; // each person owes their share
      }
    });
  });

  // Debts already paid off in real life.
  settlements.forEach((s) => {
    if (balances[s.from] !== undefined) balances[s.from] += s.amount;
    if (balances[s.to] !== undefined) balances[s.to] -= s.amount;
  });

  // Match people who owe (debtors) to people who are owed (creditors),
  // producing the fewest payments. All integers, so no rounding needed.
  const debtors = [];
  const creditors = [];
  people.forEach((name) => {
    const b = balances[name];
    if (b < 0) debtors.push({ name, amount: -b });
    else if (b > 0) creditors.push({ name, amount: b });
  });

  const transactions = [];
  let i = 0;
  let j = 0;
  while (i < debtors.length && j < creditors.length) {
    const pay = Math.min(debtors[i].amount, creditors[j].amount);
    if (pay > 0) {
      transactions.push({ from: debtors[i].name, to: creditors[j].name, amount: pay });
    }
    debtors[i].amount -= pay;
    creditors[j].amount -= pay;
    if (debtors[i].amount === 0) i++;
    if (creditors[j].amount === 0) j++;
  }

  return { total, balances, transactions };
}
