// settle.js — the "who owes whom" brain of the app.
//
// It takes:
//   people   = an array (a numbered list) of names, e.g. ["Alex", "Sam"]
//   expenses = an array of expense objects, e.g.
//              [{ description: "Groceries", amount: 60, paidBy: "Alex" }]
//
// It returns an object with: the total, each person's fair share,
// every person's balance, and the list of payments to settle up.

export function settleUp(people, expenses, settlements = []) {
  // --- Step 1: Total spent ---
  // .reduce(...) walks through the list adding each amount onto a running sum.
  const total = expenses.reduce((sum, e) => sum + e.amount, 0);

  // --- Step 2: Each person's fair share ---
  // Split the total evenly. (Guard against dividing by zero if nobody added yet.)
  const perPersonShare = people.length > 0 ? total / people.length : 0;

  // --- Step 3: Work out each person's balance ---
  // balance = (money they paid out) minus (their fair share).
  //   positive balance  => the household OWES them money
  //   negative balance  => THEY owe the household money
  const balances = {}; // an object that maps a name -> their balance number
  people.forEach((name) => {
    balances[name] = 0;
  });

  // Add what each person actually paid.
  expenses.forEach((e) => {
    if (balances[e.paidBy] !== undefined) {
      balances[e.paidBy] += e.amount;
    }
  });

  // Subtract everyone's fair share.
  people.forEach((name) => {
    balances[name] -= perPersonShare;
  });

  // Apply any settlements (debts already paid off in real life).
  // When "from" pays "to", it's as if "from" paid out money (debt shrinks)
  // and "to" received money (what they're owed shrinks).
  settlements.forEach((s) => {
    if (balances[s.from] !== undefined) balances[s.from] += s.amount;
    if (balances[s.to] !== undefined) balances[s.to] -= s.amount;
  });

  // --- Step 4: Turn balances into actual payments ---
  // Split people into those who owe (debtors) and those who are owed (creditors).
  const debtors = [];
  const creditors = [];
  people.forEach((name) => {
    const b = round(balances[name]);
    if (b < 0) debtors.push({ name, amount: -b }); // store owed amount as positive
    else if (b > 0) creditors.push({ name, amount: b });
  });

  // Match debtors to creditors one by one until everyone is squared up.
  const transactions = [];
  let i = 0; // points at the current debtor
  let j = 0; // points at the current creditor
  while (i < debtors.length && j < creditors.length) {
    // Pay the smaller of (what this debtor owes) and (what this creditor is owed).
    const pay = Math.min(debtors[i].amount, creditors[j].amount);

    transactions.push({
      from: debtors[i].name,
      to: creditors[j].name,
      amount: round(pay),
    });

    debtors[i].amount -= pay;
    creditors[j].amount -= pay;

    // If a person is fully settled, move on to the next one.
    if (debtors[i].amount <= 0.001) i++;
    if (creditors[j].amount <= 0.001) j++;
  }

  return { total, perPersonShare, balances, transactions };
}

// Small helper: round money to 2 decimal places so we never show $12.333333.
function round(n) {
  return Math.round(n * 100) / 100;
}
