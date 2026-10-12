
BEGIN TRANSACTION ISOLATION LEVEL READ COMMITTED;

SELECT balance
FROM acid_accounts
WHERE account_id = 101;

SELECT balance
FROM acid_accounts
WHERE account_id = 101;

COMMIT;

BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ;

SELECT balance
FROM acid_accounts
WHERE account_id = 101;

SELECT balance
FROM acid_accounts
WHERE account_id = 101;

COMMIT;

BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;

SELECT SUM(balance)
FROM acid_accounts;

UPDATE acid_accounts
SET balance = balance + 200
WHERE account_id = 102;

COMMIT;

BEGIN;

SELECT *
FROM acid_accounts
WHERE account_id = 101
FOR UPDATE;

COMMIT;

BEGIN;

LOCK TABLE acid_accounts
IN EXCLUSIVE MODE;

SELECT * FROM acid_accounts;

COMMIT;

BEGIN;

UPDATE acid_accounts
SET balance = balance + 10
WHERE account_id = 101;

UPDATE acid_accounts
SET balance = balance + 10
WHERE account_id = 102;

ROLLBACK;
SELECT *
FROM acid_accounts
ORDER BY account_id;
