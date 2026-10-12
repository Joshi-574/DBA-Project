INSERT INTO customers
(full_name, email, phone, date_of_birth, city)
VALUES
('Rahul Kumar', 'rahul@gmail.com', '9876543210', '2000-05-15', 'Vijayawada'),
('Priya Sharma', 'priya@gmail.com', '9876543211', '1999-08-20', 'Hyderabad'),
('Arjun Reddy', 'arjun@gmail.com', '9876543212', '2001-02-10', 'Bangalore'),
('Sneha Rao', 'sneha@gmail.com', '9876543213', '2000-11-25', 'Chennai'),
('Kiran Kumar', 'kiran@gmail.com', '9876543214', '1998-06-18', 'Mumbai');

SELECT * FROM customers;

INSERT INTO accounts
(customer_id, account_number, account_type, balance)
VALUES
(1, 'BG100001', 'SAVINGS', 50000.00),
(2, 'BG100002', 'SAVINGS', 75000.00),
(3, 'BG100003', 'CURRENT', 120000.00),
(4, 'BG100004', 'SAVINGS', 45000.00),
(5, 'BG100005', 'CURRENT', 90000.00);

SELECT * FROM accounts;

INSERT INTO transactions
(account_id, transaction_type, amount, recipient_account, description)
VALUES
(1, 'DEPOSIT', 10000.00, NULL, 'Salary credit'),
(1, 'WITHDRAWAL', 5000.00, NULL, 'ATM withdrawal'),
(1, 'TRANSFER', 8000.00, 'BG100002', 'Fund transfer'),
(2, 'DEPOSIT', 15000.00, NULL, 'Salary credit'),
(2, 'TRANSFER', 12000.00, 'BG100003', 'Fund transfer'),
(3, 'DEPOSIT', 25000.00, NULL, 'Business payment'),
(3, 'TRANSFER', 20000.00, 'BG100005', 'Business transfer'),
(4, 'WITHDRAWAL', 3000.00, NULL, 'ATM withdrawal'),
(5, 'DEPOSIT', 30000.00, NULL, 'Business income'),
(5, 'TRANSFER', 18000.00, 'BG100001', 'Fund transfer');

SELECT * FROM transactions;

INSERT INTO audit_logs
(customer_id, action, ip_address, details)
VALUES
(1, 'LOGIN', '192.168.1.10', 'Successful login'),
(2, 'LOGIN', '192.168.1.11', 'Successful login'),
(3, 'PASSWORD_CHANGE', '192.168.1.12', 'Password changed successfully'),
(4, 'LOGIN', '192.168.1.13', 'Successful login'),
(5, 'LOGOUT', '192.168.1.14', 'User logged out'),
(1, 'TRANSFER_INITIATED', '192.168.1.10', 'Fund transfer initiated'),
(2, 'LOGIN_FAILED', '192.168.1.15', 'Invalid password attempt'),
(3, 'ACCOUNT_UPDATE', '192.168.1.12', 'Account information updated');

SELECT * FROM audit_logs;

INSERT INTO fraud_events
(transaction_id, customer_id, fraud_type, risk_score, status)
VALUES
(3, 1, 'Unusual Transfer', 82.50, 'OPEN'),
(5, 2, 'High Value Transfer', 75.00, 'INVESTIGATING'),
(7, 3, 'Suspicious Transaction', 91.00, 'OPEN'),
(10, 5, 'Unusual Transfer Pattern', 68.50, 'RESOLVED');

SELECT * FROM fraud_events;

SELECT * FROM customers;
SELECT customer_id, full_name, city
FROM customers;
SELECT *
FROM customers
WHERE city = 'Vijayawada';
UPDATE customers
SET city = 'Guntur'
WHERE customer_id = 1;
SELECT *
FROM customers
WHERE customer_id = 1;
UPDATE accounts
SET balance = balance + 5000
WHERE account_id = 1;
SELECT *
FROM accounts
WHERE account_id = 1;
INSERT INTO customers
(full_name, email, phone, date_of_birth, city)
VALUES
('Test User', 'testuser@gmail.com', '9000000000', '2000-01-01', 'Test City');
SELECT *
FROM customers
WHERE email = 'testuser@gmail.com';
DELETE FROM customers
WHERE email = 'testuser@gmail.com';
SELECT *
FROM customers
WHERE email = 'testuser@gmail.com';

-- =========================================
-- BANKGUARD - WINDOW FUNCTIONS
-- =========================================

-- 1. ROW_NUMBER()
-- Assign a unique number to each transaction
-- based on amount (highest first)

SELECT
    transaction_id,
    amount,
    ROW_NUMBER() OVER (ORDER BY amount DESC) AS row_num
FROM transactions;


-- 2. RANK()
-- Rank transactions based on amount

SELECT
    transaction_id,
    amount,
    RANK() OVER (ORDER BY amount DESC) AS rank
FROM transactions;


-- 3. DENSE_RANK()
-- Rank transactions without gaps

SELECT
    transaction_id,
    amount,
    DENSE_RANK() OVER (ORDER BY amount DESC) AS dense_rank
FROM transactions;


-- 4. PARTITION BY
-- Rank transactions separately for each account

SELECT
    transaction_id,
    account_id,
    amount,
    RANK() OVER (
        PARTITION BY account_id
        ORDER BY amount DESC
    ) AS account_rank
FROM transactions;


-- 5. LAG()
-- Display the previous transaction amount
-- for the same account

SELECT
    transaction_id,
    account_id,
    amount,
    LAG(amount) OVER (
        PARTITION BY account_id
        ORDER BY transaction_date
    ) AS previous_amount
FROM transactions;


-- 6. LEAD()
-- Display the next transaction amount
-- for the same account

SELECT
    transaction_id,
    account_id,
    amount,
    LEAD(amount) OVER (
        PARTITION BY account_id
        ORDER BY transaction_date
    ) AS next_amount
FROM transactions;

SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

-- =========================================
-- BANKGUARD - INNER JOIN
-- Customers + Accounts
-- =========================================

SELECT
    c.customer_id,
    c.full_name,
    c.email,
    a.account_id,
    a.account_type,
    a.balance
FROM public.customers AS c
INNER JOIN public.accounts AS a
    ON c.customer_id = a.customer_id;

-- =========================================
-- BANKGUARD - LEFT JOIN
-- Show all customers and their accounts
-- =========================================

SELECT
    c.customer_id,
    c.full_name,
    a.account_id,
    a.account_type,
    a.balance
FROM public.customers AS c
LEFT JOIN public.accounts AS a
    ON c.customer_id = a.customer_id;

-- =========================================
-- BANKGUARD - RIGHT JOIN
-- Show all accounts, even if
-- customer information is missing
-- =========================================

SELECT
    c.customer_id,
    c.full_name,
    c.email,
    a.account_id,
    a.account_type,
    a.balance
FROM public.customers AS c
RIGHT JOIN public.accounts AS a
    ON c.customer_id = a.customer_id;