#!/bin/bash
set -eu

psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --set ON_ERROR_STOP=1 --set rep_password="$PG_REPL_PASSWORD" <<'SQL'
SELECT format('CREATE ROLE replicator WITH LOGIN REPLICATION PASSWORD %L', :'rep_password') \gexec
SELECT pg_create_physical_replication_slot('pg_replica1_slot');
SELECT pg_create_physical_replication_slot('pg_replica2_slot');
SQL

cat >> "$PGDATA/pg_hba.conf" <<'HBA'
host replication replicator 0.0.0.0/0 scram-sha-256
HBA
