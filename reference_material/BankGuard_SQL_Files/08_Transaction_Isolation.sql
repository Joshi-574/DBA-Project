-- Default isolation observed: read committed.
-- isolation_test was created and now contains Rahul, Priya, Arjun and Sneha.
-- Inspect before inserting; do not repeat the original INSERT statements.

CREATE TABLE isolation_test (
 id INT PRIMARY KEY, customer_name VARCHAR(50), balance NUMERIC(10,2)
);

SELECT * FROM isolation_test ORDER BY id;

-- READ COMMITTED non-repeatable-read demonstration (two pgAdmin sessions):
-- Session A: BEGIN;
-- Session A: SELECT account_number, balance FROM acidaccounts WHERE account_number='ACID1001';
-- Session B: BEGIN;
-- Session B: UPDATE acidaccounts SET balance=balance+500 WHERE account_number='ACID1001';
-- Session B: COMMIT;
-- Session A repeats SELECT and sees the newly committed balance.

-- READ COMMITTED phantom-read demonstration:
-- Session A: BEGIN;
-- Session A: SELECT * FROM isolation_test WHERE balance > 4000;
-- Session B: BEGIN;
-- Session B: INSERT INTO isolation_test VALUES (3,'Arjun',9000.00);
-- Session B: COMMIT;
-- Session A repeats SELECT and sees the additional matching row.

-- REPEATABLE READ demonstration:
-- Session A: BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ;
-- Session A: SELECT * FROM isolation_test WHERE balance > 4000;
-- Session B: BEGIN;
-- Session B: INSERT INTO isolation_test VALUES (4,'Sneha',6000.00);
-- Session B: COMMIT;
-- Session A repeats SELECT and continues seeing its original snapshot.
-- Session A: COMMIT;
