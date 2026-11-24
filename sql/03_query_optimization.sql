-- Run in a separate pgAdmin Query Tool tab after 01_foundation.sql.
-- Compare plans before and after indexes; ANALYZE refreshes planner statistics.
EXPLAIN SELECT * FROM transactions WHERE account_id=42 ORDER BY occurred_at DESC;
CREATE INDEX IF NOT EXISTS idx_transactions_account_time
    ON transactions(account_id,occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_fraudevents_unresolved_risk
    ON fraudevents(risk_score DESC) WHERE resolved=false;
CREATE INDEX IF NOT EXISTS idx_auditlogs_details_gin
    ON auditlogs USING gin(details);
ANALYZE transactions;
ANALYZE fraudevents;
EXPLAIN ANALYZE SELECT * FROM transactions WHERE account_id=42 ORDER BY occurred_at DESC;
EXPLAIN ANALYZE SELECT * FROM fraudevents
    WHERE resolved=false AND risk_score>=80 ORDER BY risk_score DESC;

-- Autovacuum is managed by PostgreSQL. Inspect settings and per-table activity.
SELECT name,setting,unit FROM pg_settings
WHERE name IN ('autovacuum','autovacuum_vacuum_scale_factor','autovacuum_analyze_scale_factor');
SELECT relname,n_live_tup,n_dead_tup,last_autovacuum,last_autoanalyze
FROM pg_stat_user_tables ORDER BY n_dead_tup DESC;

-- Historical slow-query analysis requires pg_stat_statements to be installed and
-- shared_preload_libraries configured by the server administrator, followed by restart.
-- CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
SELECT query,calls,round(total_exec_time::numeric,2) AS total_ms,
       round(mean_exec_time::numeric,2) AS mean_ms,rows
FROM pg_stat_statements
WHERE dbid=(SELECT oid FROM pg_database WHERE datname=current_database())
ORDER BY total_exec_time DESC LIMIT 20;
