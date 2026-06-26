// settle.js — the "who owes whom" brain of the app.
//
// It takes:
//   people      = array of names, e.g. ["Alex", "Sam"]
//   expenses    = array of expense objects. Each one looks like:
//                 {
//                   description: "Taxi",
//                   amount: 30,
//                   paidBy: "Alex",
//                   shares: { Alex: 15, Sam: 15 }  // how much each owes for THIS expense
//                 }
//   settlements = array of debts already paid off, e.g.
//                 [{ from: "Sam", to: "Alex", amount: 15 }]
//
// It returns: the total, each person's net balance, and the payments to settle up.

export function settleUp(people, expenses, settlements = []) {
  // --- Total spent ---
  const total = expenses.reduce((sum, e) => sum + e.amount, 0);

  // --- Each person's balance ---
  // balance = (money they paid out) minus (their share of every expense).
  //   positive => the household OWES them ;  negative => THEY owe.
  const balances = {};
  people.forEach((name) => {
    balances[name] = 0;
  });

  expenses.forEach((e) => {
    // The person who paid is credited the full amount they laid out.
    if (balances[e.paidBy] !== undefined) {
      balances[e.paidBy] += e.amount;
    }
    // Each person is debited their personal share of this expense.
    const shares = e.shares || {};
    Object.keys(shares).forEach((name) => {
      if (balances[name] !== undefined) {
        balances[name] -= shares[name];
      }
    });
  });

  // --- Apply settlements (debts already paid in real life) ---
  settlements.forEach((s) => {
    if (balances[s.from] !== undefined) balances[s.from] += s.amount;
    if (balances[s.to] !== undefined) balances[s.to] -= s.amount;
  });

  // --- Turn balances into actual payments ---
  const debtors = [];
  const creditors = [];
  people.forEach((name) => {
    const b = round(balances[name]);
    if (b < 0) debtors.push({ name, amount: -b });
    else if (b > 0) creditors.push({ name, amount: b });
  });

  const transactions = [];
  let i = 0;
  let j = 0;
  while (i < debtors.length && j < creditors.length) {
    const pay = Math.min(debtors[i].amount, creditors[j].amount);
    transactions.push({
      from: debtors[i].name,
      to: creditors[j].name,
      amount: round(pay),
    });
    debtors[i].amount -= pay;
    creditors[j].amount -= pay;
    if (debtors[i].amount <= 0.001) i++;
    if (creditors[j].amount <= 0.001) j++;
  }

  return { total, balances, transactions };
}

// Round money to 2 decimal places so we never show $12.333333.
function round(n) {
  return Math.round(n * 100) / 100;
}
