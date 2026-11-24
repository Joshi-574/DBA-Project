-- EXPLAIN and EXPLAIN ANALYZE experiments:
EXPLAIN SELECT * FROM transactions WHERE amount > 10000;

EXPLAIN ANALYZE
SELECT * FROM transactions WHERE amount > 10000;

-- Index was created during the experiment (already exists; do not rerun blindly):
-- CREATE INDEX idx_transactions_amount ON transactions(amount);

SHOW autovacuum;

SELECT relname, n_live_tup, n_dead_tup, last_vacuum, last_autovacuum,
       last_analyze, last_autoanalyze
FROM pg_stat_user_tables
WHERE relname = 'transactions';

-- VACUUM (ANALYZE) transactions; -- already executed

SELECT pid, usename, state, query, now() - query_start AS running_time
FROM pg_stat_activity
WHERE datname = 'BankGuard' AND state = 'active';

-- Monitoring demonstration query:
-- SELECT pg_sleep(20);
