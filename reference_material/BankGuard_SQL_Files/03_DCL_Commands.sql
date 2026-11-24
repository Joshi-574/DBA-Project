-- Run administrative statements using the postgres/admin connection.
-- Role bg_analyst was created. Do not put passwords in shared project files.

GRANT CONNECT ON DATABASE "BankGuard" TO bg_analyst;
GRANT USAGE ON SCHEMA public TO bg_analyst;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO bg_analyst;

-- Test as bg_analyst:
SELECT * FROM customers LIMIT 5;

-- An INSERT attempt as bg_analyst correctly failed with permission denied.
-- Optional REVOKE demonstration:
-- REVOKE SELECT ON fraudevents FROM bg_analyst;
-- Test as analyst: SELECT * FROM fraudevents;
-- Restore as admin: GRANT SELECT ON fraudevents TO bg_analyst;
