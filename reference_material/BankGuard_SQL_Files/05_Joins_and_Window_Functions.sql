-- Read-only JOIN and window function examples.

SELECT c.customer_id, c.first_name, c.last_name, a.account_number, a.balance
FROM customers c INNER JOIN accounts a ON c.customer_id = a.customer_id;

SELECT c.customer_id, c.first_name, a.account_number
FROM customers c LEFT JOIN accounts a ON c.customer_id = a.customer_id;

SELECT c.customer_id, c.first_name, a.account_number
FROM customers c RIGHT JOIN accounts a ON c.customer_id = a.customer_id;

SELECT c.customer_id, c.first_name, a.account_number
FROM customers c FULL OUTER JOIN accounts a ON c.customer_id = a.customer_id;

SELECT c.customer_id, c.first_name, a.account_number,
       t.transaction_id, t.amount, t.transaction_type
FROM customers c
JOIN accounts a ON c.customer_id = a.customer_id
JOIN transactions t ON a.account_id = t.account_id;

SELECT transaction_id, amount,
       ROW_NUMBER() OVER (ORDER BY amount DESC) AS row_num
FROM transactions;

SELECT transaction_id, amount,
       RANK() OVER (ORDER BY amount DESC) AS transaction_rank
FROM transactions;

SELECT transaction_id, amount,
       DENSE_RANK() OVER (ORDER BY amount DESC) AS dense_rank
FROM transactions;

SELECT transaction_id, amount,
       SUM(amount) OVER (ORDER BY transaction_id
       ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_total
FROM transactions;

SELECT transaction_id, amount, AVG(amount) OVER () AS overall_average
FROM transactions;
