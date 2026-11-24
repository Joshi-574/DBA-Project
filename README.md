# BankGuard Dashboard and Local Replication Lab

The Streamlit dashboard reads the supplied PostgreSQL schema and MongoDB replica set, and can monitor a local Docker lab. The Docker Compose lab creates a PostgreSQL primary with two physical streaming replicas, plus a MongoDB sharded cluster with three shards. Its `BankGuard.shard_demo` collection is seeded with 2,000 records per shard, evenly partitioned by `shard_group`.

## Start the Docker lab

Docker Desktop must be running. From this project folder:

```powershell
docker compose up -d
docker compose ps
```

First startup pulls the official Postgres 18 and MongoDB 8.0.12 images, initializes the databases and replica/shard topology, and may take a few minutes. PostgreSQL ports are primary `5433`, replica1 `5434`, and replica2 `5435`. MongoDB mongos is `27020`; direct shard metrics use `27101`, `27102`, and `27103`. The existing MongoDB replica set from the supplied notes remains separate on `27017`–`27019`.

The PostgreSQL Docker primary is initialized from the schema in `reference_material/BankGuard_SQL_Files/01_Database_and_Tables.sql` and seeded with 500 sample rows in each main table. Its default local development passwords are `bankguard_primary_dev` and `bankguard_repl_dev`; set `PG_PRIMARY_PASSWORD` and `PG_REPL_PASSWORD` in `.env` before first startup if you want different local credentials. These ports bind to localhost. Do not expose the development defaults to a network. Replica1 applies WAL after 200 ms and replica2 after 700 ms, keeping both inside the dashboard's healthy lag threshold while producing live heartbeat samples.

To stop the containers while preserving their data:

```powershell
docker compose down
```

To recreate the lab from a clean state, volumes must be deleted explicitly with `docker compose down -v`; that deletes the Docker lab's stored database data.

## Dashboard

Install dependencies and run:

```powershell
python -m pip install -r requirements.txt
streamlit run dashboard.py
```

Open this project folder in VS Code: `C:\Users\mdsan\Desktop\BankGuard_SQL_Files`. Select your Python 3 interpreter, then run the commands above in the VS Code PowerShell terminal. The `.env` file in this folder supplies your local connection settings; do not replace it with `.env.example` unless you intentionally want to recreate the settings.

The app has PostgreSQL, MongoDB, and Docker Connect/Disable controls. The **Replication Health** page polls PostgreSQL lag/write lag/state and MongoDB replica-set member health every second. A one-row heartbeat produces fresh WAL for the live lag chart. Set `PG_REPLICATION_DSN=postgresql://postgres:bankguard_primary_dev@127.0.0.1:5433/BankGuard` in `.env` to monitor the Docker PostgreSQL primary. Set the MongoDB values from `.env.example` to view the sharded cluster on **Shard Balance** while retaining `MONGO_URI` for the existing `rs0` replica set. **Lab Execution** contains simulation-only ACID, isolation, concurrency, and SQL learning tabs; lab buttons do not change database records.

The **Slow Queries** page ranks live `pg_stat_statements` by total execution time when the extension is enabled. The **Project Files** page browses the supplied SQL and benchmark files; saved pgbench results are identified as benchmark data, not live dashboard measurements.

## Sharding behavior

The sharded collection has exactly 6,000 sample documents with 2,000 assigned to each shard. Sharding partitions documents: each record lives on one shard, while replication copies each shard's records to that shard's replica members. The Compose cluster uses one MongoDB process per shard for a lightweight local demonstration, plus one config-server process. It is a learning setup, not a highly available production cluster.
