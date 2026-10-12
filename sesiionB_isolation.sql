UPDATE acid_accounts
SET balance = balance + 500
WHERE account_id = 101;

COMMIT;

UPDATE acid_accounts
SET balance = balance + 500
WHERE account_id = 101;

COMMIT;

BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;

UPDATE acid_accounts
SET balance = balance + 100
WHERE account_id = 101;

COMMIT;

UPDATE acid_accounts
SET balance = balance + 500
WHERE account_id = 101;

SELECT *
FROM acid_accounts
WHERE account_id = 101;

BEGIN;

UPDATE acid_accounts
SET balance = balance + 20
WHERE account_id = 102;

UPDATE acid_accounts
SET balance = balance + 20
WHERE account_id = 101;

ROLLBACK;

SELECT *
FROM acid_accounts
ORDER BY account_id;