-- TCL exercises performed using acidaccounts.
-- Existing test accounts: Rahul / ACID1001 and Priya / ACID1002.
-- Do not rerun the UPDATE examples blindly; balances will change.

-- COMMIT transfer example (already completed):
-- BEGIN;
-- UPDATE acidaccounts SET balance = balance - 2000 WHERE account_number='ACID1001';
-- UPDATE acidaccounts SET balance = balance + 2000 WHERE account_number='ACID1002';
-- COMMIT;

-- ROLLBACK example (already completed):
-- BEGIN;
-- UPDATE acidaccounts SET balance = balance - 1000 WHERE account_number='ACID1001';
-- ROLLBACK;

-- SAVEPOINT example (already completed):
-- BEGIN;
-- UPDATE acidaccounts SET balance = balance + 500 WHERE account_number='ACID1001';
-- SAVEPOINT transfer_point;
-- UPDATE acidaccounts SET balance = balance + 1000 WHERE account_number='ACID1002';
-- ROLLBACK TO SAVEPOINT transfer_point;
-- COMMIT;

-- A later READ COMMITTED demonstration added another 500 to ACID1001.
-- Check actual current balances before further tests:
SELECT account_number, account_holder, balance
FROM acidaccounts ORDER BY account_number;
