-- DCL: execute as owner/superuser. Role creation is repeatable.
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='bankguard_analyst') THEN
    CREATE ROLE bankguard_analyst LOGIN;
  END IF;
END $$;
GRANT CONNECT ON DATABASE "BankGuard" TO bankguard_analyst;
GRANT USAGE ON SCHEMA public TO bankguard_analyst;
GRANT SELECT ON customers,accounts,transactions,auditlogs,fraudevents TO bankguard_analyst;

-- TCL / ACID: atomic transfer example. ROLLBACK is shown; replace with COMMIT to persist.
BEGIN;
UPDATE acidaccounts SET balance=balance-100, updated_at=now() WHERE account_id=1 AND balance>=100;
UPDATE acidaccounts SET balance=balance+100, updated_at=now() WHERE account_id=2;
-- COMMIT;
ROLLBACK;

-- Isolation-level exercise: run in separate sessions to observe snapshot behavior.
-- Session A: BEGIN ISOLATION LEVEL REPEATABLE READ; SELECT balance FROM acidaccounts WHERE account_id=1;
-- Session B: UPDATE acidaccounts SET balance=balance-10 WHERE account_id=1; COMMIT;
-- Session A: repeat the SELECT (same snapshot); COMMIT.
-- For a serialization check, use SERIALIZABLE in both sessions and retry SQLSTATE 40001.

-- Deadlock exercise: open two sessions and run the following in the indicated order.
-- Session A: BEGIN; UPDATE acidaccounts SET balance=balance+1 WHERE account_id=1;
-- Session B: BEGIN; UPDATE acidaccounts SET balance=balance+1 WHERE account_id=2;
-- Session A: UPDATE acidaccounts SET balance=balance+1 WHERE account_id=2; (waits)
-- Session B: UPDATE acidaccounts SET balance=balance+1 WHERE account_id=1; (one transaction is aborted as deadlock victim)
-- ROLLBACK the surviving session. PostgreSQL detects the cycle and aborts one participant.

-- Concurrency table smoke check. The Python load test supplies the 50,000-row concurrent run.
SELECT count(*) AS concurrency_rows FROM concurrency_test;

-- Join examples
SELECT c.customer_id,c.full_name,a.account_id,a.balance
FROM customers c JOIN accounts a USING(customer_id) ORDER BY a.balance DESC LIMIT 10;
SELECT t.transaction_id,t.amount,f.risk_score,f.event_type
FROM transactions t LEFT JOIN fraudevents f USING(transaction_id)
WHERE f.risk_score >= 80 ORDER BY f.risk_score DESC;

-- Window functions: rank balances per account type and rolling transaction average.
SELECT account_id,account_type,balance,
       rank() OVER(PARTITION BY account_type ORDER BY balance DESC) AS type_rank
FROM accounts;
SELECT account_id,occurred_at,amount,
       avg(amount) OVER(PARTITION BY account_id ORDER BY occurred_at ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) AS rolling_avg
FROM transactions;

