-- Verified existing row counts: 500 rows in each of these tables:
-- customers, accounts, transactions, auditlogs, fraudevents.
-- Original bulk INSERT statements were not retained verbatim.
-- DO NOT rerun bulk inserts; this may create duplicates or unique-key errors.

SELECT 'customers' AS table_name, COUNT(*) AS row_count FROM customers
UNION ALL SELECT 'accounts', COUNT(*) FROM accounts
UNION ALL SELECT 'transactions', COUNT(*) FROM transactions
UNION ALL SELECT 'auditlogs', COUNT(*) FROM auditlogs
UNION ALL SELECT 'fraudevents', COUNT(*) FROM fraudevents;
