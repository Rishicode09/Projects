-- ---------------------------------------------------------------------------
-- The same analysis the Python script does, written as SQL.
--
-- Run any of these against cashflow.db. Each is named so run_queries.py can
-- pick it out; the name in the -- @name comment is just a label for that.
-- ---------------------------------------------------------------------------


-- @name headline
-- The four numbers at the top of the report.
-- SUM(CASE WHEN ...) is the SQL way of writing "total, but only these rows".
SELECT
    ROUND(SUM(paid_in),  2) AS cash_in,
    ROUND(SUM(paid_out), 2) AS cash_out,
    ROUND(SUM(amount),   2) AS net_result,
    COUNT(*)                AS transactions,
    MIN(txn_date)           AS period_from,
    MAX(txn_date)           AS period_to
FROM transactions;


-- @name monthly_cashflow
-- Money in, money out and a running total, month by month.
-- strftime pulls the year-month out of the date. The window function
-- SUM(...) OVER (ORDER BY ...) gives the running total -- the single most
-- useful thing to know in finance SQL.
SELECT
    strftime('%Y-%m', txn_date)                       AS month,
    ROUND(SUM(paid_in),  2)                           AS cash_in,
    ROUND(SUM(paid_out), 2)                           AS cash_out,
    ROUND(SUM(amount),   2)                           AS net_movement,
    ROUND(SUM(SUM(amount)) OVER (
        ORDER BY strftime('%Y-%m', txn_date)
    ), 2)                                             AS running_total
FROM transactions
GROUP BY month
ORDER BY month;


-- @name profit_and_loss
-- Income first, then expenses, largest first. The ORDER BY uses a CASE so
-- income sorts above expenses regardless of the category name.
SELECT
    c.kind                        AS section,
    c.name                        AS line,
    COUNT(*)                      AS transactions,
    ROUND(SUM(t.amount), 2)       AS amount
FROM transactions t
JOIN category c ON c.category_id = t.category_id
GROUP BY c.kind, c.name
ORDER BY
    CASE c.kind WHEN 'income' THEN 0 ELSE 1 END,
    ABS(SUM(t.amount)) DESC;


-- @name by_counterparty
-- The accumulated position with each company, and its share of the money
-- flowing that direction. The subquery in the denominator is how you get a
-- percentage of a total in SQL.
SELECT
    cp.name                                          AS company,
    CASE WHEN SUM(t.amount) >= 0 THEN 'CASH IN'
         ELSE 'CASH OUT' END                         AS direction,
    COUNT(*)                                         AS transactions,
    ROUND(AVG(ABS(t.amount)), 2)                     AS average,
    ROUND(SUM(t.amount), 2)                          AS accumulated,
    ROUND(100.0 * SUM(ABS(t.amount)) / (
        SELECT SUM(ABS(amount)) FROM transactions x
        WHERE (x.amount >= 0) = (SUM(t.amount) >= 0)
    ), 1)                                            AS pct_of_direction,
    MIN(t.txn_date)                                  AS first_seen,
    MAX(t.txn_date)                                  AS last_seen
FROM transactions t
JOIN counterparty cp ON cp.counterparty_id = t.counterparty_id
GROUP BY cp.name
ORDER BY SUM(ABS(t.amount)) DESC;


-- @name recurring_processes
-- Which payment streams are monthly and which are one-offs. HAVING filters
-- on the result of an aggregate -- WHERE cannot, because it runs first.
SELECT
    t.description                                    AS process,
    cp.name                                          AS company,
    COUNT(*)                                         AS occurrences,
    CASE
        WHEN COUNT(*) >= 12 THEN 'Monthly'
        WHEN COUNT(*) = 1   THEN 'One-off'
        ELSE 'Irregular'
    END                                              AS frequency,
    ROUND(SUM(t.amount), 2)                          AS total
FROM transactions t
JOIN counterparty cp ON cp.counterparty_id = t.counterparty_id
GROUP BY t.description, cp.name
ORDER BY ABS(SUM(t.amount)) DESC;


-- @name audit_missing_documents
-- Control check: any transaction with no supporting document reference.
-- Should return no rows.
SELECT txn_date, description, amount
FROM transactions
WHERE document_ref IS NULL OR TRIM(document_ref) = ''
ORDER BY txn_date;


-- @name audit_unusual_amounts
-- Anomaly test: payments more than three times the typical transaction size.
-- A CTE (WITH ...) names an intermediate result so the main query stays
-- readable -- here, the average of every transaction, worked out once.
--
-- Note on the baseline: with more data you would compare each payment to the
-- average for ITS OWN category, which is a sharper test. That does not work
-- on this file because most categories contain a single fixed amount, so the
-- average equals the amount and nothing can ever exceed it. Choosing a
-- baseline the data can actually support is part of the job.
WITH overall AS (
    SELECT AVG(ABS(amount)) AS avg_amount FROM transactions
)
SELECT
    t.txn_date,
    t.description,
    c.name                                AS category,
    ROUND(t.amount, 2)                    AS amount,
    ROUND(o.avg_amount, 2)                AS average_transaction,
    ROUND(ABS(t.amount) / o.avg_amount, 1) AS times_average
FROM transactions t
JOIN category c ON c.category_id = t.category_id
CROSS JOIN overall o
WHERE ABS(t.amount) > 3 * o.avg_amount
ORDER BY ABS(t.amount) DESC;


-- @name concentration_risk
-- How dependent is the company on its biggest customer? For a landlord with
-- one tenant this is the headline risk, and it is one line of SQL.
SELECT
    cp.name                                          AS customer,
    ROUND(SUM(t.paid_in), 2)                         AS income,
    ROUND(100.0 * SUM(t.paid_in) /
          (SELECT SUM(paid_in) FROM transactions), 1) AS pct_of_income
FROM transactions t
JOIN counterparty cp ON cp.counterparty_id = t.counterparty_id
WHERE t.paid_in > 0
GROUP BY cp.name
ORDER BY income DESC;
