CREATE TABLE IF NOT EXISTS acid_accounts (
    account_id INT PRIMARY KEY,
    customer_name VARCHAR(50),
    balance NUMERIC(10,2) CHECK (balance >= 0)
);

INSERT INTO acid_accounts (account_id, customer_name, balance)
VALUES
    (101, 'Priya', 10000),
    (102, 'Rahul', 5000)
ON CONFLICT (account_id) DO NOTHING;

SELECT * FROM acid_accounts;


#Atomicity
BEGIN;

UPDATE acid_accounts
SET balance = balance - 1000
WHERE account_id = 101;
#consistency
UPDATE acid_accounts
SET balance = balance + 1000
WHERE account_id = 102;

COMMIT;

SELECT * FROM acid_accounts;

UPDATE acid_accounts
SET balance = -500
WHERE account_id = 101;

#Isolation
BEGIN;
UPDATE acid_accounts
SET balance = balance - 500
WHERE account_id = 101;

#Durability
COMMIT;

SELECT * FROM acid_accounts;