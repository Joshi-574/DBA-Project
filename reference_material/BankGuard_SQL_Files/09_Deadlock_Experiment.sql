-- Deadlock experiment uses TWO separate pgAdmin Query Tool sessions.
-- The table and its two initial rows were created/inserted.
-- Check both sessions and transaction state before repeating any step.

-- Setup already completed:
-- CREATE TABLE deadlock_test (
--   account_id INT PRIMARY KEY, account_name VARCHAR(50), balance NUMERIC(10,2)
-- );
-- INSERT INTO deadlock_test VALUES (1,'Account A',5000),(2,'Account B',7000);

-- Session A:
-- BEGIN;
-- UPDATE deadlock_test SET balance=balance-100 WHERE account_id=1;

-- Session B:
-- BEGIN;
-- UPDATE deadlock_test SET balance=balance-100 WHERE account_id=2;

-- Session A (waits for Session B's lock):
-- UPDATE deadlock_test SET balance=balance-100 WHERE account_id=2;

-- Session B (completes the circular wait; PostgreSQL should detect deadlock):
-- UPDATE deadlock_test SET balance=balance-100 WHERE account_id=1;

-- After PostgreSQL reports deadlock, ROLLBACK the surviving open transaction.
-- Inspect table after both sessions are out of their transactions:
SELECT * FROM deadlock_test ORDER BY account_id;
