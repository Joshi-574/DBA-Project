"""DataVault-style BankGuard operations dashboard."""
import os
import re
import time
from pathlib import Path

import pandas as pd
import psycopg
from psycopg.conninfo import conninfo_to_dict, make_conninfo
import streamlit as st
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()
st.set_page_config(page_title="BankGuard", page_icon="🛡️", layout="wide")
st.markdown("""
<style>
.stApp { background:#07111b; color:#e7edf7; }
[data-testid="stSidebar"] { background:#08121d; border-right:1px solid #162637; }
[data-testid="stMetric"] { background:#0d1927; border:1px solid #1a2c40; border-radius:12px; padding:15px 17px; }
[data-testid="stMetricLabel"] { color:#9cadbf; }
div[data-testid="stDataFrame"] { border:1px solid #1c2b3d; border-radius:10px; }
div.stButton > button { border:1px solid #147c8c; color:#63e5e3; background:#0c202b; border-radius:8px; }
div.stButton > button:hover { border-color:#38d8d6; color:white; }
</style>
""", unsafe_allow_html=True)

if "demo_events" not in st.session_state:
    st.session_state.demo_events = 49_939
env_pg_dsn = os.getenv("POSTGRES_DSN", "")
try:
    pg_defaults = conninfo_to_dict(env_pg_dsn) if env_pg_dsn else {}
except Exception:
    pg_defaults = {}
pg_host_default = pg_defaults.get("host", "127.0.0.1")
if not pg_host_default or "@" in pg_host_default:
    pg_host_default = "127.0.0.1"
with st.sidebar.form("postgres_connection_form", clear_on_submit=False):
    st.markdown("### PostgreSQL connection")
    pg_host_input = st.text_input("Host", value=pg_host_default, key="postgres_host_v2")
    pg_port_input = st.text_input("Port", value=str(pg_defaults.get("port", "5432")))
    pg_database_input = st.text_input("Database", value=pg_defaults.get("dbname", "BankGuard"))
    pg_user_input = st.text_input("Username", value=pg_defaults.get("user", "postgres"))
    pg_password_input = st.text_input("Password", value="", type="password", key="postgres_password_v2")
    pg_submit = st.form_submit_button("Connect PostgreSQL", use_container_width=True)
if pg_submit:
    try:
        submitted_dsn = make_conninfo(
            "", host=pg_host_input, port=pg_port_input, dbname=pg_database_input,
            user=pg_user_input, password=pg_password_input, connect_timeout=3,
        )
        with psycopg.connect(submitted_dsn) as test_conn:
            test_conn.execute("SELECT 1")
        st.session_state.pg_runtime_dsn = submitted_dsn
        st.session_state.pg_enabled = True
        st.session_state.pg_connect_error = None
        st.sidebar.success(f"Connected to {pg_database_input} as {pg_user_input}.")
    except Exception as exc:
        st.session_state.pg_connect_error = str(exc)
        st.sidebar.error(f"PostgreSQL connection failed: {exc}")

pg_dsn = st.session_state.get("pg_runtime_dsn", env_pg_dsn)
docker_pg_password = os.getenv("PG_PRIMARY_PASSWORD", "bankguard_primary_dev")
pg_replication_dsn = os.getenv("PG_REPLICATION_DSN") or make_conninfo(
    "", host="127.0.0.1", port=5433, dbname="BankGuard", user="postgres",
    password=docker_pg_password, connect_timeout=2,
)
pg_replica_dsns = {
    "pg-replica1": os.getenv("PG_REPLICA1_DSN") or make_conninfo(
        "", host="127.0.0.1", port=5434, dbname="BankGuard", user="postgres",
        password=docker_pg_password, connect_timeout=2,
    ),
    "pg-replica2": os.getenv("PG_REPLICA2_DSN") or make_conninfo(
        "", host="127.0.0.1", port=5435, dbname="BankGuard", user="postgres",
        password=docker_pg_password, connect_timeout=2,
    ),
}
mongo_uri = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017,127.0.0.1:27018,127.0.0.1:27019/?replicaSet=rs0")
mongo_database = os.getenv("MONGO_DATABASE", "BankGuard")
mongo_sharded_uri = os.getenv("MONGO_SHARDED_URI", "mongodb://127.0.0.1:27020/BankGuard")
mongo_shard_uris = [
    os.getenv("MONGO_SHARD1_URI", "mongodb://127.0.0.1:27101/?directConnection=true"),
    os.getenv("MONGO_SHARD2_URI", "mongodb://127.0.0.1:27102/?directConnection=true"),
    os.getenv("MONGO_SHARD3_URI", "mongodb://127.0.0.1:27103/?directConnection=true"),
]
pg, mongo = {}, {}
sharding = {}
docker_data = {}
queries = pd.DataFrame()
indexes = pd.DataFrame()
pg_live = mongo_live = False
docker_live = False
if "pg_enabled" not in st.session_state:
    st.session_state.pg_enabled = True
if "mongo_enabled" not in st.session_state:
    st.session_state.mongo_enabled = True
if "docker_enabled" not in st.session_state:
    st.session_state.docker_enabled = True

try:
    if st.session_state.pg_enabled and pg_dsn:
        with psycopg.connect(pg_dsn, connect_timeout=3) as conn:
            pg_live = True
            pg.update(pd.read_sql("""SELECT count(*) FILTER(WHERE state='active') active,
              count(*) FILTER(WHERE state='idle') idle,count(*) connections
              FROM pg_stat_activity WHERE datname=current_database()""", conn).iloc[0].to_dict())
            pg["is_standby"] = bool(pd.read_sql("SELECT pg_is_in_recovery() AS value", conn).iloc[0]["value"])
            if pg["is_standby"]:
                pg["standby_receiver"] = pd.read_sql("""SELECT status,sender_host,sender_port,
                  latest_msg_receipt_time,latest_end_time,
                  round(EXTRACT(EPOCH FROM (now()-latest_msg_receipt_time))::numeric,3) AS receipt_age_seconds
                  FROM pg_stat_wal_receiver""", conn)
                pg["replicas"] = pd.DataFrame()
            else:
                pg["replicas"] = pd.read_sql("""SELECT CASE WHEN application_name='walreceiver'
                  THEN 'pg-replica'||row_number() OVER (PARTITION BY application_name ORDER BY client_addr)::text
                  ELSE application_name END AS replica,
                  client_addr::text AS client_address,state,sync_state,
                  round(EXTRACT(EPOCH FROM write_lag)::numeric,3) AS write_lag_seconds,
                  round(EXTRACT(EPOCH FROM flush_lag)::numeric,3) AS flush_lag_seconds,
                  round(EXTRACT(EPOCH FROM replay_lag)::numeric,3) AS replay_lag_seconds
                  FROM pg_stat_replication ORDER BY application_name""", conn)
            pg["tables"] = pd.read_sql("""SELECT relname AS table,n_live_tup AS estimated_rows,
              n_dead_tup AS dead_rows,last_autovacuum,last_autoanalyze
              FROM pg_stat_user_tables ORDER BY relname""", conn)
            pg["core_counts"] = pd.read_sql("""SELECT 'customers' AS table_name,COUNT(*) AS row_count FROM customers
              UNION ALL SELECT 'accounts',COUNT(*) FROM accounts
              UNION ALL SELECT 'transactions',COUNT(*) FROM transactions
              UNION ALL SELECT 'auditlogs',COUNT(*) FROM auditlogs
              UNION ALL SELECT 'fraudevents',COUNT(*) FROM fraudevents
              ORDER BY table_name""", conn)
            pg["transaction_summary"] = pd.read_sql("""SELECT COUNT(*) AS transactions,
              COALESCE(SUM(amount),0) AS total_amount,COALESCE(AVG(amount),0) AS average_amount,
              COUNT(*) FILTER (WHERE transaction_status ILIKE 'completed') AS completed
              FROM transactions""", conn).iloc[0].to_dict()
            pg["fraud_summary"] = pd.read_sql("""SELECT risk_level,COUNT(*) AS events
              FROM fraudevents GROUP BY risk_level ORDER BY risk_level""", conn)
            enabled = pd.read_sql("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname='pg_stat_statements') enabled", conn).iloc[0]["enabled"]
            if enabled:
                queries = pd.read_sql("""SELECT query AS \"Query\",calls AS \"Calls\",
                  round(total_exec_time::numeric,2) AS \"Total Time (ms)\",
                  round(mean_exec_time::numeric,2) AS \"Mean Time (ms)\",
                  rows AS \"Avg Rows\" FROM pg_stat_statements
                  WHERE dbid=(SELECT oid FROM pg_database WHERE datname=current_database())
                    AND query NOT ILIKE '%pg_stat_statements%'
                  ORDER BY total_exec_time DESC LIMIT 100""", conn)
            indexes = pd.read_sql("""SELECT tablename AS table,indexname AS index,
                  indexdef AS definition FROM pg_indexes WHERE schemaname='public'
                  ORDER BY tablename,indexname""", conn)
            pg["query_source"] = "pg_stat_statements" if enabled else "not enabled"
except Exception as exc:
    pg["error"] = str(exc)
if not st.session_state.pg_enabled:
    pg["disabled"] = True

# Optional Docker primary dedicated to streaming-replica monitoring.
if st.session_state.pg_enabled and pg_replication_dsn and pg_replication_dsn != pg_dsn:
    try:
        with psycopg.connect(pg_replication_dsn, connect_timeout=2) as conn:
            pg["is_standby"] = bool(pd.read_sql("SELECT pg_is_in_recovery() AS value", conn).iloc[0]["value"])
            if pg["is_standby"]:
                pg["standby_receiver"] = pd.read_sql("""SELECT status,sender_host,sender_port,latest_msg_receipt_time,
                  latest_end_time,round(EXTRACT(EPOCH FROM (now()-latest_msg_receipt_time))::numeric,3) AS receipt_age_seconds
                  FROM pg_stat_wal_receiver""", conn)
                pg["replicas"] = pd.DataFrame()
            else:
                pg["replicas"] = pd.read_sql("""SELECT CASE WHEN application_name='walreceiver'
                  THEN 'pg-replica'||row_number() OVER (PARTITION BY application_name ORDER BY client_addr)::text
                  ELSE application_name END AS replica,client_addr::text AS client_address,
                  state,sync_state,round(EXTRACT(EPOCH FROM write_lag)::numeric,3) AS write_lag_seconds,
                  round(EXTRACT(EPOCH FROM flush_lag)::numeric,3) AS flush_lag_seconds,
                  round(EXTRACT(EPOCH FROM replay_lag)::numeric,3) AS replay_lag_seconds
                  FROM pg_stat_replication ORDER BY application_name""", conn)
            pg["replication_source"] = "Docker PostgreSQL primary"
    except Exception as exc:
        pg["replication_error"] = str(exc)

try:
    if st.session_state.mongo_enabled:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2500, connectTimeoutMS=2500)
        client.admin.command("ping")
        mongo_live = True
        db = client[mongo_database]
        mongo["collections"] = db.list_collection_names()
        mongo["collection_metrics"] = [
            {"Collection": name, "Documents": db[name].estimated_document_count()}
            for name in mongo["collections"]
        ]
        mongo["documents"] = sum(row["Documents"] for row in mongo["collection_metrics"])
        try:
            server_status = db.command("serverStatus")
            mongo["connections"] = server_status.get("connections", {})
            mongo["memory_mb"] = server_status.get("mem", {}).get("resident")
            mongo["server_version"] = server_status.get("version", "Unknown")
        except Exception as exc:
            mongo["server_stats_error"] = str(exc)
        try:
            db_stats = db.command("dbStats")
            mongo["data_size_mb"] = round(db_stats.get("dataSize", 0) / (1024 * 1024), 2)
            mongo["storage_size_mb"] = round(db_stats.get("storageSize", 0) / (1024 * 1024), 2)
            mongo["index_size_mb"] = round(db_stats.get("indexSize", 0) / (1024 * 1024), 2)
        except Exception as exc:
            mongo["db_stats_error"] = str(exc)
        hello = db.command("hello")
        mongo["hosts"] = hello.get("hosts", [])
        mongo["primary"] = hello.get("primary", "")
        try:
            replica_status = db.command("replSetGetStatus")
            mongo["replica_members"] = replica_status.get("members", [])
            primary_member = next((m for m in mongo["replica_members"] if m.get("stateStr") == "PRIMARY"), None)
            primary_optime = primary_member.get("optimeDate") if primary_member else None
            mongo["replica_table"] = []
            for member in mongo["replica_members"]:
                member_optime = member.get("optimeDate")
                lag_seconds = max(0, (primary_optime - member_optime).total_seconds()) if primary_optime and member_optime else None
                mongo["replica_table"].append({
                    "Member": member.get("name"),
                    "State": member.get("stateStr"),
                    "Health": member.get("health"),
                    "Replication Lag (seconds)": round(lag_seconds, 3) if lag_seconds is not None else "—",
                    "Heartbeat (ms)": round(member.get("pingMs", 0), 2),
                })
        except Exception:
            mongo["replica_members"] = []
        client.close()
    else:
        mongo["disabled"] = True
except Exception as exc:
    mongo["error"] = str(exc)

if st.session_state.mongo_enabled:
    try:
        sharded_client = MongoClient(mongo_sharded_uri, serverSelectionTimeoutMS=1500, connectTimeoutMS=1500)
        sharded_client.admin.command("ping")
        sharded_db = sharded_client[mongo_database]
        sharding["total"] = sharded_db["shard_demo"].estimated_document_count()
        sharding["shards"] = []
        for index, shard_uri in enumerate(mongo_shard_uris, start=1):
            shard_client = MongoClient(shard_uri, serverSelectionTimeoutMS=1000, connectTimeoutMS=1000, directConnection=True)
            count = shard_client[mongo_database]["shard_demo"].count_documents({})
            sharding["shards"].append({"Shard": f"shard{index}rs", "Documents": count})
            shard_client.close()
        sharding["live"] = True
        sharded_client.close()
    except Exception as exc:
        sharding["error"] = str(exc)

try:
    if st.session_state.docker_enabled:
        import docker

        docker_client = docker.from_env(timeout=3)
        docker_client.ping()
        docker_live = True
        docker_data["containers"] = []
        for container in docker_client.containers.list(all=True):
            item = {
                "Container": container.name,
                "Image": container.image.tags[0] if container.image.tags else container.image.short_id,
                "Status": container.status,
                "CPU %": "—",
                "Memory": "—",
                "Ports": ", ".join(
                    f"{binding.get('HostIp', '0.0.0.0')}:{binding.get('HostPort')} → {port}"
                    for port, bindings in (container.attrs.get("NetworkSettings", {}).get("Ports") or {}).items()
                    if bindings for binding in bindings
                ) or "—",
            }
            if container.status == "running":
                try:
                    stats = container.stats(stream=False)
                    cpu = stats.get("cpu_stats", {})
                    precpu = stats.get("precpu_stats", {})
                    cpu_delta = cpu.get("cpu_usage", {}).get("total_usage", 0) - precpu.get("cpu_usage", {}).get("total_usage", 0)
                    system_delta = cpu.get("system_cpu_usage", 0) - precpu.get("system_cpu_usage", 0)
                    cpu_count = cpu.get("online_cpus") or len(cpu.get("cpu_usage", {}).get("percpu_usage", [])) or 1
                    if cpu_delta > 0 and system_delta > 0:
                        item["CPU %"] = round((cpu_delta / system_delta) * cpu_count * 100, 2)
                    memory = stats.get("memory_stats", {})
                    used = memory.get("usage", 0)
                    cache = memory.get("stats", {}).get("cache", 0)
                    item["Memory"] = f"{max(0, used-cache)/(1024**2):.1f} MB"
                except Exception:
                    pass
            docker_data["containers"].append(item)
        docker_data["running"] = sum(1 for row in docker_data["containers"] if row["Status"] == "running")
        docker_client.close()
    else:
        docker_data["disabled"] = True
except Exception as exc:
    docker_data["error"] = str(exc)

live = pg_live or mongo_live or docker_live or sharding.get("live", False)
dashboard_pages = ["Slow Queries", "Replication Health", "Shard Balance", "Index Advisor", "Project Files", "Docker Containers"]
lab_pages = ["Lab Execution"]
all_pages = dashboard_pages + lab_pages
if st.session_state.get("active_page") not in all_pages:
    st.session_state.active_page = "Slow Queries"
with st.sidebar:
    st.markdown("## 🛡️ BankGuard")
    for nav_page in dashboard_pages:
        if st.button(nav_page, key=f"nav_{nav_page}", use_container_width=True,
                     type="primary" if st.session_state.active_page == nav_page else "secondary"):
            st.session_state.active_page = nav_page
            st.rerun()
    st.markdown("**Lab Execution**")
    for nav_page in lab_pages:
        if st.button(nav_page, key=f"nav_{nav_page}", use_container_width=True,
                     type="primary" if st.session_state.active_page == nav_page else "secondary"):
            st.session_state.active_page = nav_page
            st.rerun()
    page = st.session_state.active_page
    st.divider()
    demo = st.toggle("Simulation/Demo Mode", value=not live, help="Show example operational data when databases are unavailable.")
    st.caption(f"API status  {'🟢 Online' if live or demo else '🔴 Offline'}")
    st.caption("Database connection checks active.")
    st.caption(f"Docker Engine {'🟢 Connected' if docker_live else '⚪ Offline'}")

header_left, _ = st.columns([3, 3])
header_left.title(page)
header_left.caption({
    "Slow Queries": "Real-time ranking of heavy PostgreSQL queries from pg_stat_statements.",
    "Replication Health": "Replica availability, standby state, and replication lag trends.",
    "Shard Balance": "MongoDB shard document distribution and imbalance diagnostics.",
    "Index Advisor": "Index recommendations based on BankGuard query patterns.",
    "Project Files": "Browse the SQL and benchmark files supplied for this BankGuard project.",
    "Docker Containers": "Container health, CPU usage, memory use, and published ports from the Docker Engine.",
    "Lab Execution": "Interactive, simulation-only exercises for transactions, isolation, concurrency, and SQL concepts.",
}[page])
connection_cards = st.columns([1, 1, 1, 0.65])
connection_specs = [
    (connection_cards[0], "PostgreSQL", "pg_enabled", pg_live),
    (connection_cards[1], "MongoDB", "mongo_enabled", mongo_live),
    (connection_cards[2], "Docker", "docker_enabled", docker_live),
]
for card, name, state_key, connected in connection_specs:
    enabled = st.session_state[state_key]
    label = "Connected" if connected else ("Offline" if enabled else "Disabled")
    with card:
        st.markdown(f"**{'🟢' if connected else '⚪'} {name}: {label}**")
        buttons = st.columns(2)
        if buttons[0].button("Connect", key=f"{state_key}_connect", disabled=connected, use_container_width=True):
            st.session_state[state_key] = True
            st.rerun()
        if buttons[1].button("Disable", key=f"{state_key}_disable", disabled=not enabled, use_container_width=True):
            st.session_state[state_key] = False
            st.rerun()
if connection_cards[3].button("⟳ Poll Now", key="poll_databases", use_container_width=True):
    st.rerun()

if st.session_state.pg_enabled and not pg_live:
    st.caption("PostgreSQL is offline. Check the POSTGRES_DSN in .env and confirm the server is running.")
if st.session_state.docker_enabled and not docker_live:
    st.caption("Docker is offline. Start Docker Desktop/Engine to connect.")

@st.fragment(run_every=1)
def render_live_pg_replication():
    st.subheader("PostgreSQL Streaming Replication")
    st.caption(f"Monitoring source: Docker PostgreSQL primary · refreshed every second · updated {time.strftime('%H:%M:%S')}")
    if not st.session_state.pg_enabled:
        st.info("PostgreSQL monitoring is disabled. Click Connect to resume live replication metrics.")
        return
    try:
        with psycopg.connect(pg_replication_dsn, connect_timeout=2) as primary_conn:
            replicas = pd.read_sql("""SELECT application_name AS replica,host(client_addr) AS client_address,
              state,sync_state,round(EXTRACT(EPOCH FROM write_lag)::numeric,4) AS write_lag_seconds,
              round(EXTRACT(EPOCH FROM flush_lag)::numeric,4) AS flush_lag_seconds,
              round(EXTRACT(EPOCH FROM replay_lag)::numeric,4) AS replay_lag_seconds
              FROM pg_stat_replication ORDER BY client_addr""", primary_conn)
            try:
                primary_heartbeat = primary_conn.execute("SELECT emitted_at FROM replication_heartbeat WHERE id=1").fetchone()
                primary_heartbeat = primary_heartbeat[0] if primary_heartbeat else None
            except psycopg.Error:
                primary_heartbeat = None
    except Exception as exc:
        st.error(f"Could not poll PostgreSQL replication: {exc}")
        return

    if replicas.empty:
        st.warning("No PostgreSQL standbys are connected to the Docker primary.")
        return

    # Identify standbys by the IP reported by their own connection. PostgreSQL
    # can report the generic application_name "walreceiver" for both replicas.
    rows_by_name = {}
    for expected_name, replica_dsn in pg_replica_dsns.items():
        try:
            with psycopg.connect(replica_dsn, connect_timeout=2) as replica_conn:
                replica_address = replica_conn.execute("SELECT host(inet_server_addr())").fetchone()[0]
                beat = replica_conn.execute("SELECT emitted_at FROM replication_heartbeat WHERE id=1").fetchone()
                heartbeat_lag = max(0.0, (primary_heartbeat - beat[0]).total_seconds()) if primary_heartbeat and beat else None
            matching = replicas[replicas["client_address"] == replica_address]
            if matching.empty:
                matching = replicas[replicas["replica"] == expected_name]
            if not matching.empty:
                item = matching.iloc[0].to_dict()
                item["replica"] = expected_name
                item["heartbeat_lag_seconds"] = heartbeat_lag
                rows_by_name[expected_name] = item
        except Exception:
            continue

    for _, row in replicas.iterrows():
        item = row.to_dict()
        name = item["replica"] if item["replica"] in pg_replica_dsns else None
        if not name:
            continue
        item["heartbeat_lag_seconds"] = None
        rows_by_name.setdefault(name, item)

    # Keep a stable left-to-right layout even if PostgreSQL changes row order.
    rows = [rows_by_name[name] for name in ("pg-replica1", "pg-replica2") if name in rows_by_name]
    cards = st.columns(2)
    sample_time = pd.Timestamp.now()
    history = st.session_state.setdefault("pg_replica_lag_history", [])
    for replica_index, col in enumerate(cards, start=1):
        replica_name = f"pg-replica{replica_index}"
        item = rows_by_name.get(replica_name)
        if item is None:
            with col.container(border=True):
                st.markdown(f"### {replica_name} · ⚪ WAITING")
                st.caption("Waiting for this standby to connect to the primary.")
                st.metric("Replication Lag", "—")
                st.metric("Write Lag", "—")
                st.markdown("Standby State  **not connected**")
            continue
        replay_lag = item["replay_lag_seconds"]
        hb_lag = item["heartbeat_lag_seconds"]
        measured_lag = float(replay_lag) if pd.notna(replay_lag) else hb_lag
        reported_write_lag = item["write_lag_seconds"]
        write_lag = float(reported_write_lag) if pd.notna(reported_write_lag) else measured_lag
        healthy = item["state"] == "streaming" and (measured_lag is None or measured_lag < 5)
        with col.container(border=True):
            st.markdown(f"### {item['replica']} · {'🟢 HEALTHY' if healthy else '🟠 WARNING'}")
            st.caption(f"Replica client: {item['client_address']}")
            st.metric("Replication Lag", f"{measured_lag:.3f}s" if measured_lag is not None else "Waiting for WAL")
            st.metric("Write Lag", f"{write_lag:.3f}s" if write_lag is not None else "Waiting for WAL")
            st.markdown(f"Standby State  **{item['state']}**")
            if pd.notna(item["write_lag_seconds"]) and measured_lag is not None and hb_lag is not None:
                st.caption("Write lag is PostgreSQL's reported value; replication lag is measured from the replicated heartbeat.")
        # A NULL PostgreSQL lag means no recent WAL sample. With a streaming
        # standby and no heartbeat lag, plot the truthful zero-lag baseline.
        plotted_lag = measured_lag if measured_lag is not None else (0.0 if item["state"] == "streaming" else None)
        if plotted_lag is not None:
            history.append({"sampled_at": sample_time, "replica": item["replica"], "lag_seconds": plotted_lag})

    st.session_state.pg_replica_lag_history = history[-300:]
    history_df = pd.DataFrame(st.session_state.pg_replica_lag_history)
    if not history_df.empty:
        chart = history_df.pivot_table(index="sampled_at", columns="replica", values="lag_seconds", aggfunc="last")
        st.subheader("Streaming Replication Lag Over Time")
        st.caption("Live heartbeat lag sampled once per second; zero means streaming with no pending WAL lag reported.")
        st.line_chart(chart, y_label="Lag seconds")


@st.fragment(run_every=1)
def render_replication_insert_status():
    inserted = st.session_state.get("replication_demo_insert")
    if not inserted:
        st.info("Run an INSERT on the primary above. This panel will check both replicas once per second for the inserted row.")
        return
    st.caption(f"Inserted on primary: account {inserted['account_number']} · account_id {inserted['account_id']} · balance ₹{inserted['balance']:,.2f}")
    replica_cols = st.columns(2)
    for col, (name, dsn) in zip(replica_cols, pg_replica_dsns.items()):
        with col.container(border=True):
            st.markdown(f"### {name}")
            try:
                with psycopg.connect(dsn, connect_timeout=2) as replica_conn:
                    is_standby = replica_conn.execute("SELECT pg_is_in_recovery()").fetchone()[0]
                    row = replica_conn.execute(
                        "SELECT account_id, account_number, balance FROM accounts WHERE account_number=%s",
                        (inserted["account_number"],),
                    ).fetchone()
                if row:
                    st.success("Replicated row visible")
                    st.dataframe(pd.DataFrame([{
                        "account_id": row[0], "account_number": row[1], "balance": f"₹{row[2]:,.2f}",
                        "is_standby": is_standby,
                    }]), use_container_width=True, hide_index=True)
                else:
                    st.warning("Waiting for the WAL change to arrive…")
            except Exception as exc:
                st.error(f"Replica not reachable: {exc}")


def render_primary_replication_insert_demo():
    st.divider()
    st.subheader("Primary → Replica Insert Demo")
    st.caption("Enter one INSERT into accounts and run it on the Docker primary. PostgreSQL streams the committed row to both read-only replicas automatically.")
    default_insert = """INSERT INTO accounts (customer_id, account_number, account_type, balance, currency, account_status)
VALUES (1, 'DEMO-SIR-2026-002', 'Savings', 12345.00, 'INR', 'Active')
ON CONFLICT (account_number) DO UPDATE SET balance = EXCLUDED.balance;"""
    insert_sql = st.text_area("SQL to execute on primary", value=default_insert, height=120, key="replication_demo_sql")
    if st.button("Execute on primary", key="run_primary_replication_insert", type="primary", disabled=not st.session_state.pg_enabled):
        statement = insert_sql.strip()
        if statement.endswith(";"):
            statement = statement[:-1].rstrip()
        if ";" in statement:
            st.error("Enter a single SQL statement only.")
        elif not re.match(r"(?is)^INSERT\s+INTO\s+(?:public\.)?accounts\s*\(", statement):
            st.error("For safety, this demo accepts INSERT statements into the BankGuard accounts table only.")
        elif not re.search(r"(?i)\bVALUES\b", statement) or re.search(r"(?i)\bRETURNING\b", statement):
            st.error("Use INSERT ... VALUES syntax and omit RETURNING; the dashboard adds RETURNING to capture the inserted account.")
        else:
            try:
                with psycopg.connect(pg_replication_dsn, connect_timeout=3) as primary_conn:
                    inserted_rows = primary_conn.execute(
                        statement + " RETURNING account_id, account_number, balance"
                    ).fetchall()
                if not inserted_rows:
                    st.error("The INSERT did not add or update a row. Check the account number and try again.")
                else:
                    row = inserted_rows[0]
                    st.session_state.replication_demo_insert = {
                        "account_id": row[0], "account_number": row[1], "balance": float(row[2]),
                    }
                    st.success("Committed on the primary. Checking both replicas below…")
            except Exception as exc:
                st.error(f"Primary INSERT failed and was rolled back: {exc}")
    render_replication_insert_status()

if demo:
    st.warning("Simulation / Demo Mode: displayed values are illustrative until database connections are configured.")

if page == "Slow Queries":
    if queries.empty and demo:
        queries = pd.DataFrame([
            {"Query":"SELECT * FROM transactions WHERE is_flagged = true AND created_at > NOW() - INTERVAL '30 days'", "Calls":850, "Total Time (ms)":3825000.0, "Mean Time (ms)":4500.0, "Avg Rows":4200},
            {"Query":"SELECT * FROM orders WHERE status = 'pending' AND user_id = $1 ORDER BY created_at DESC LIMIT 50", "Calls":12450, "Total Time (ms)":1867500.0, "Mean Time (ms)":150.0, "Avg Rows":249000},
            {"Query":"SELECT account_id, SUM(amount) FROM transactions GROUP BY account_id", "Calls":420, "Total Time (ms)":98000.0, "Mean Time (ms)":233.3, "Avg Rows":500},
        ])
    total_docs = mongo.get("documents", st.session_state.demo_events if demo else 0)
    slow = int((queries["Mean Time (ms)"] > 100).sum()) if not queries.empty else 0
    metrics = st.columns(4)
    metrics[0].metric("MongoDB Documents", f"{total_docs:,}", "Across configured collections")
    metrics[1].metric("Pg Slow Queries (>100ms)", slow, "Average > 100ms")
    actual_secondaries = sum(1 for member in mongo.get("replica_members", []) if member.get("stateStr") == "SECONDARY")
    metrics[2].metric("MongoDB Secondaries", actual_secondaries if mongo_live else ("2" if demo else "—"), "Healthy members" if mongo_live else "Demo value")
    mongo_memory = mongo.get("memory_mb")
    metrics[3].metric("MongoDB Resident Memory", f"{mongo_memory:,} MB" if mongo_memory is not None else ("119 MB" if demo else "—"), "Server process RAM")
    st.subheader("Top Slow Queries by Total Time")
    if not queries.empty:
        query_filter = st.text_input("Filter queries", placeholder="Filter queries...")
        shown = queries[queries["Query"].str.contains(query_filter, case=False, na=False)] if query_filter else queries
        st.dataframe(shown, use_container_width=True, hide_index=True, height=330)
    elif pg_live:
        st.info("No query history yet. Enable pg_stat_statements on the PostgreSQL server to collect ranked query statistics.")
    else:
        st.info("Connect PostgreSQL and enable pg_stat_statements to show live query history.")
    st.subheader("Database activity")
    c = st.columns(4)
    c[0].metric("Connections", int(pg.get("connections", 0) or 0))
    c[1].metric("Active now", int(pg.get("active", 0) or 0))
    c[2].metric("Idle", int(pg.get("idle", 0) or 0))
    c[3].metric("Query history", "Available" if pg.get("query_source") == "pg_stat_statements" else ("Demo" if demo else "Unavailable"))
    if pg_live and "core_counts" in pg:
        st.subheader("BankGuard PostgreSQL tables")
        st.dataframe(pg["core_counts"], use_container_width=True, hide_index=True)
        tx = pg["transaction_summary"]
        stats = st.columns(4)
        stats[0].metric("Transactions", f"{tx['transactions']:,}")
        stats[1].metric("Completed", f"{tx['completed']:,}")
        stats[2].metric("Transaction Amount", f"₹{tx['total_amount']:,.2f}")
        stats[3].metric("Average Amount", f"₹{tx['average_amount']:,.2f}")
        st.subheader("Fraud events by risk level")
        st.dataframe(pg["fraud_summary"], use_container_width=True, hide_index=True)
    st.subheader("MongoDB metrics")
    mongo_cards = st.columns(5)
    mongo_cards[0].metric("Connection", "Connected" if mongo_live else ("Demo" if demo else "Offline"))
    mongo_cards[1].metric("Current Connections", mongo.get("connections", {}).get("current", "—"))
    mongo_cards[2].metric("Data Size", f"{mongo.get('data_size_mb', 0):,.2f} MB" if mongo_live else ("Demo" if demo else "—"))
    mongo_cards[3].metric("Storage Size", f"{mongo.get('storage_size_mb', 0):,.2f} MB" if mongo_live else ("Demo" if demo else "—"))
    mongo_cards[4].metric("Index Size", f"{mongo.get('index_size_mb', 0):,.2f} MB" if mongo_live else ("Demo" if demo else "—"))
    if mongo_live:
        st.caption(f"MongoDB {mongo.get('server_version')} · Database: {mongo_database} · Collections: {len(mongo.get('collections', []))}")
        with st.expander("MongoDB collection metrics"):
            st.dataframe(pd.DataFrame(mongo.get("collection_metrics", [])), use_container_width=True, hide_index=True)

elif page == "Lab Execution":
    acid_tab, isolation_tab, concurrency_tab, reference_tab = st.tabs([
        "ACID Transactions", "Isolation Levels", "Concurrency Lab", "Concepts & SQL Reference"
    ])

    with acid_tab:
        st.subheader("Bank transfer simulation")
        st.info("Simulation only — no banking records or database tables are changed. Use the buttons to demonstrate COMMIT-like success and ROLLBACK-like failure.")
        st.session_state.setdefault("lab_sender_balance", 10_000.0)
        st.session_state.setdefault("lab_receiver_balance", 5_000.0)
        st.session_state.setdefault("lab_transfer_result", "No transfer run yet.")
        a, b = st.columns(2)
        a.metric("Account A · Sender", f"₹{st.session_state.lab_sender_balance:,.2f}")
        b.metric("Account B · Receiver", f"₹{st.session_state.lab_receiver_balance:,.2f}")
        amount = st.number_input("Transfer amount (₹)", min_value=1.0, max_value=10_000_000.0, value=3_000.0, step=500.0, key="lab_transfer_amount")
        execute_col, fail_col, reset_col = st.columns(3)
        if execute_col.button("Execute transfer", key="lab_transfer_commit", type="primary", use_container_width=True):
            if amount <= st.session_state.lab_sender_balance:
                st.session_state.lab_sender_balance -= amount
                st.session_state.lab_receiver_balance += amount
                st.session_state.lab_transfer_result = f"COMMIT simulated: ₹{amount:,.2f} transferred. Both account updates succeeded together."
            else:
                st.session_state.lab_transfer_result = "Transaction rejected: insufficient funds. The debit was rolled back; neither balance changed."
            st.rerun()
        if fail_col.button("Simulate failure", key="lab_transfer_rollback", use_container_width=True):
            st.session_state.lab_transfer_result = f"ROLLBACK simulated after a ₹{amount:,.2f} debit attempt. Original balances were restored; no partial transfer remains."
            st.rerun()
        if reset_col.button("Reset demo", key="lab_transfer_reset", use_container_width=True):
            st.session_state.lab_sender_balance = 10_000.0
            st.session_state.lab_receiver_balance = 5_000.0
            st.session_state.lab_transfer_result = "Demo reset. Ready for a new transfer."
            st.rerun()
        st.subheader("Latest transaction result")
        st.success(st.session_state.lab_transfer_result)
        with st.expander("How this demonstrates ACID"):
            st.markdown("**Atomicity:** debit and credit happen together; a failure undoes the debit.\n\n**Consistency:** the sender cannot go below zero.\n\n**Isolation:** each simulated transfer is treated as one transaction.\n\n**Durability:** a successful COMMIT would persist in a real database; this teaching demo keeps values only in the current browser session.")

    with isolation_tab:
        st.subheader("Two-session read visibility")
        st.info("Simulated session timeline only. No SQL is sent to the database. The behavior models PostgreSQL read visibility.")
        level = st.selectbox("Isolation level for Session A", ["READ COMMITTED", "REPEATABLE READ", "SERIALIZABLE"], key="lab_isolation_level")
        if st.session_state.get("lab_iso_level_seen") != level:
            st.session_state.lab_iso_level_seen = level
            st.session_state.lab_iso_balance = 8_000.0
            st.session_state.lab_iso_first_read = None
            st.session_state.lab_iso_second_read = None
            st.session_state.lab_iso_writer_committed = False
        reset_col, read_col, commit_col, reread_col = st.columns(4)
        if reset_col.button("Reset scenario", key="lab_iso_reset", use_container_width=True):
            st.session_state.lab_iso_balance = 8_000.0
            st.session_state.lab_iso_first_read = None
            st.session_state.lab_iso_second_read = None
            st.session_state.lab_iso_writer_committed = False
            st.rerun()
        if read_col.button("1. Session A reads", key="lab_iso_read1", type="primary", use_container_width=True):
            st.session_state.lab_iso_first_read = st.session_state.lab_iso_balance
            st.session_state.lab_iso_second_read = None
            st.rerun()
        if commit_col.button("2. Session B commits", key="lab_iso_commit", use_container_width=True):
            st.session_state.lab_iso_balance += 500.0
            st.session_state.lab_iso_writer_committed = True
            st.rerun()
        if reread_col.button("3. Session A reads again", key="lab_iso_read2", disabled=st.session_state.lab_iso_first_read is None or not st.session_state.lab_iso_writer_committed, use_container_width=True):
            st.session_state.lab_iso_second_read = st.session_state.lab_iso_balance if level == "READ COMMITTED" else st.session_state.lab_iso_first_read
            st.rerun()
        left, right = st.columns(2)
        with left.container(border=True):
            st.markdown("### Session A · Reader")
            st.metric("First read", f"₹{st.session_state.lab_iso_first_read:,.2f}" if st.session_state.lab_iso_first_read is not None else "Not run")
            st.metric("Second read", f"₹{st.session_state.lab_iso_second_read:,.2f}" if st.session_state.lab_iso_second_read is not None else "Not run")
        with right.container(border=True):
            st.markdown("### Session B · Writer")
            st.metric("Committed demo balance", f"₹{st.session_state.lab_iso_balance:,.2f}")
            st.caption("Session B adds ₹500 and commits between Session A's reads.")
        if st.session_state.lab_iso_second_read is not None:
            if level == "READ COMMITTED":
                st.success("Session A sees the newly committed ₹500 on its second statement.")
            else:
                st.success(f"Session A keeps its original snapshot at ₹{st.session_state.lab_iso_first_read:,.2f}; the concurrent commit is hidden until its transaction ends.")
        with st.expander("Why the results differ"):
            st.markdown("**READ COMMITTED:** each statement gets a fresh snapshot, so the second read sees Session B's commit.\n\n**REPEATABLE READ:** Session A keeps the snapshot established by its first read.\n\n**SERIALIZABLE:** it uses a stable snapshot and PostgreSQL may abort a transaction if concurrent work cannot be safely serialized.")

    with concurrency_tab:
        st.subheader("Lost update simulation")
        st.info("Two workers each add 1 to the same counter. Step through the interleaving to see how a lost update happens.")
        st.session_state.setdefault("lab_counter", 0)
        st.session_state.setdefault("lab_read_a", None)
        st.session_state.setdefault("lab_read_b", None)
        st.session_state.setdefault("lab_concurrency_note", "Start by letting both sessions read the counter.")
        st.metric("Shared counter", st.session_state.lab_counter)
        c1, c2, c3, c4 = st.columns(4)
        if c1.button("Reset", key="lab_conc_reset", use_container_width=True):
            st.session_state.lab_counter = 0
            st.session_state.lab_read_a = None
            st.session_state.lab_read_b = None
            st.session_state.lab_concurrency_note = "Scenario reset."
            st.rerun()
        if c2.button("Both sessions read", key="lab_conc_read", use_container_width=True):
            st.session_state.lab_read_a = st.session_state.lab_counter
            st.session_state.lab_read_b = st.session_state.lab_counter
            st.session_state.lab_concurrency_note = f"Session A and B both read {st.session_state.lab_counter}."
            st.rerun()
        if c3.button("Session A writes +1", key="lab_conc_a", disabled=st.session_state.lab_read_a is None, use_container_width=True):
            st.session_state.lab_counter = st.session_state.lab_read_a + 1
            st.session_state.lab_concurrency_note = "Session A writes its increment."
            st.rerun()
        if c4.button("Session B writes +1", key="lab_conc_b", disabled=st.session_state.lab_read_b is None, use_container_width=True):
            st.session_state.lab_counter = st.session_state.lab_read_b + 1
            st.session_state.lab_concurrency_note = "Lost update: B writes from its old value, overwriting A's increment. The final value is 1 instead of 2."
            st.rerun()
        st.write(st.session_state.lab_concurrency_note)
        st.markdown("A real database can prevent this pattern with row locks (`SELECT ... FOR UPDATE`), atomic updates (`SET counter = counter + 1`), or suitable transaction isolation.")

    with reference_tab:
        st.subheader("Concepts & SQL Reference")
        st.markdown("**ACID transfer pattern**")
        st.code("BEGIN;\nUPDATE acidaccounts SET balance = balance - 3000 WHERE account_id = 1 AND balance >= 3000;\nUPDATE acidaccounts SET balance = balance + 3000 WHERE account_id = 2;\nCOMMIT;  -- use ROLLBACK if any step fails", language="sql")
        st.markdown("**Isolation level examples**")
        st.code("BEGIN TRANSACTION ISOLATION LEVEL READ COMMITTED;\n-- or REPEATABLE READ / SERIALIZABLE\nSELECT balance FROM acidaccounts WHERE account_id = 1;\nCOMMIT;", language="sql")
        st.markdown("**Concurrency-safe increment**")
        st.code("UPDATE concurrency_test\nSET operation_no = operation_no + 1\nWHERE worker_id = 1;\n-- For read-modify-write workflows, lock the row:\nSELECT * FROM acidaccounts WHERE account_id = 1 FOR UPDATE;", language="sql")
        st.caption("These snippets are for learning and are not executed by the simulation tabs.")

elif page == "Replication Health":
    if demo:
        st.caption("Illustrative three-node MongoDB replica set; connect databases to show live health.")
    render_live_pg_replication()
    render_primary_replication_insert_demo()
    if not demo and mongo_live:
        st.subheader("MongoDB Replica Set Health")
        st.caption(f"Primary: {mongo.get('primary') or 'Not advertised'} · Set: rs0 (from supplied project connection)")
        members = mongo.get("replica_table", [])
        if members:
            primary = next((row for row in members if row["State"] == "PRIMARY"), None)
            secondaries = [row for row in members if row["State"] == "SECONDARY"]
            if primary:
                st.markdown(f"### {primary['Member']} · PRIMARY · {'🟢 HEALTHY' if primary['Health'] == 1 else '🔴 UNHEALTHY'}")
            cols = st.columns(max(1, len(secondaries)))
            for col, member in zip(cols, secondaries):
                lag = member["Replication Lag (seconds)"]
                healthy = member["Health"] == 1 and isinstance(lag, (int, float)) and lag < 5
                with col:
                    st.markdown(f"### {member['Member']} · {'🟢 HEALTHY' if healthy else '🟠 WARNING'}")
                    st.metric("Replication Lag", f"{lag}s" if isinstance(lag, (int, float)) else "Unavailable")
                    st.metric("Heartbeat Latency", f"{member['Heartbeat (ms)']} ms")
                    st.markdown(f"Member State  **{member['State']}**")
            st.dataframe(pd.DataFrame(members), use_container_width=True, hide_index=True)

            now = pd.Timestamp.now()
            history = st.session_state.setdefault("mongo_replica_lag_history", [])
            for member in secondaries:
                lag = member["Replication Lag (seconds)"]
                if isinstance(lag, (int, float)):
                    history.append({"sampled_at": now, "member": member["Member"], "lag_seconds": lag})
            st.session_state.mongo_replica_lag_history = history[-240:]
            history_df = pd.DataFrame(st.session_state.mongo_replica_lag_history)
            if not history_df.empty:
                chart = history_df.pivot_table(index="sampled_at", columns="member", values="lag_seconds", aggfunc="last")
                st.subheader("Replication Lag Over Time")
                st.caption("Click Poll Now to collect another live lag sample.")
                st.line_chart(chart, y_label="Lag seconds", color=["#20c6d7", "#38b991"])
        else:
            st.write("Advertised members:", mongo.get("hosts", []))
            st.info("Replica member states require permission to run replSetGetStatus.")
    elif not demo and not pg_live:
        st.info("Enable demo mode or connect MongoDB to display replica-set health.")

elif page == "Shard Balance":
    st.subheader("MongoDB Shard Document Imbalance Diagnostics")
    st.caption("MongoDB assigns each sharded document to one shard. This page checks whether document counts are evenly distributed.")
    st.caption(f"Docker sharded cluster: {'Connected' if sharding.get('live') else 'Offline'}")
    if sharding.get("live") and not demo:
        shard_counts = sharding.get("shards", [])
        total_live = sum(item["Documents"] for item in shard_counts)
        avg_live = total_live / max(1, len(shard_counts))
        live_rows = [{
            "Shard ID": item["Shard"],
            "Document Count": item["Documents"],
            "% of Total Docs": f"{(item['Documents'] / total_live * 100 if total_live else 0):.1f}%",
            "Deviation from Even Split": f"{(abs(item['Documents'] - avg_live) / avg_live * 100 if avg_live else 0):.1f}%",
        } for item in shard_counts]
        st.metric("Documents in sharded collection", f"{total_live:,}", "BankGuard.shard_demo")
        st.dataframe(pd.DataFrame(live_rows), use_container_width=True, hide_index=True)
        st.subheader("Document Distribution across Shards")
        st.bar_chart(pd.Series({item["Shard"]: item["Documents"] for item in shard_counts}), color="#19b9c7")
    elif demo:
        st.caption("Illustrative balanced distribution; connect to the Docker sharded cluster for live counts.")
        demo_counts = [2000, 2000, 2000]
        demo_shards = ["shard1rs", "shard2rs", "shard3rs"]
        st.dataframe(pd.DataFrame({"Shard ID": demo_shards, "Document Count": demo_counts, "% of Total Docs": ["33.3%"] * 3, "Deviation from Even Split": ["0.0%"] * 3}), use_container_width=True, hide_index=True)
        st.bar_chart(pd.Series(dict(zip(demo_shards, demo_counts))), color="#19b9c7")
    else:
        st.info("Start the Docker sharded cluster with `docker compose up -d`, then click Poll Now. Check MONGO_SHARDED_URI and MONGO_SHARD1_URI through MONGO_SHARD3_URI in .env if it stays offline.")

elif page == "Index Advisor":
    st.subheader("Index Advisor")
    st.caption("Recommendations follow BankGuard's slow-query filters and sort patterns.")
    suggestions = pd.DataFrame([
        {"Collection/Table":"transactions", "Recommended Index":"(amount)", "Reason":"Supports the supplied amount > 10000 optimization query", "Status":"Present" if "idx_transactions_amount" in set(indexes.get("index", [])) else "Check SQL experiment"},
        {"Collection/Table":"transactions", "Recommended Index":"(account_id, transaction_date DESC)", "Reason":"Account transaction history and date ordering", "Status":"Recommended"},
        {"Collection/Table":"fraudevents", "Recommended Index":"(risk_level, fraud_status)", "Reason":"Filter and summarize fraud by risk and review status", "Status":"Recommended"},
    ])
    st.dataframe(suggestions, use_container_width=True, hide_index=True)
    if not indexes.empty:
        with st.expander("Existing PostgreSQL indexes"):
            st.dataframe(indexes, use_container_width=True, hide_index=True)
    if not demo:
        st.code("CREATE INDEX CONCURRENTLY idx_transactions_account_date ON transactions(account_id, transaction_date DESC);", language="sql")

elif page == "Project Files":
    st.subheader("Supplied BankGuard files")
    files_root = Path(__file__).parent / "reference_material" / "BankGuard_SQL_Files"
    if files_root.exists():
        files = sorted(p for p in files_root.iterdir() if p.is_file())
        selected = st.selectbox("Choose a project file", files, format_func=lambda p: p.name)
        contents = selected.read_text(encoding="utf-8", errors="replace")
        if selected.name == "07_Concurrency_Benchmark.txt":
            results = []
            for line in contents.splitlines():
                match = re.match(r"\s*([\d,]+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*(\d+)\s*$", line)
                if match:
                    results.append({"Transactions": int(match.group(1).replace(",", "")), "Avg latency (ms)": float(match.group(2)), "TPS": float(match.group(3)), "Failed": int(match.group(4))})
            if results:
                benchmark = pd.DataFrame(results)
                m = st.columns(3)
                m[0].metric("Largest Run", f"{benchmark['Transactions'].max():,}")
                m[1].metric("Peak TPS", f"{benchmark['TPS'].max():,.0f}")
                m[2].metric("Failures", f"{benchmark['Failed'].sum():,}")
                st.subheader("Supplied pgbench results")
                st.line_chart(benchmark.set_index("Transactions")[["TPS"]], y_label="Transactions per second")
                st.dataframe(benchmark, use_container_width=True, hide_index=True)
            st.code(contents, language="text")
        elif selected.suffix.lower() == ".sql":
            st.code(contents, language="sql")
        else:
            st.code(contents, language="text")
    else:
        st.info("The supplied ZIP files were not found. Keep the reference_material folder next to dashboard.py.")

elif page == "Docker Containers":
    st.subheader("Docker Engine metrics")
    if docker_live:
        rows = docker_data.get("containers", [])
        running = docker_data.get("running", 0)
        metrics = st.columns(3)
        metrics[0].metric("Engine", "Connected")
        metrics[1].metric("Containers", len(rows))
        metrics[2].metric("Running", running)
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("Docker is connected, but no containers were found.")
    else:
        st.info("Docker Engine is not reachable. Start Docker Desktop/Engine and install the Python client with `python -m pip install docker`.")
        if docker_data.get("error"):
            st.caption(docker_data["error"])

if pg.get("tables") is not None:
    with st.expander("PostgreSQL table and autovacuum statistics"):
        st.dataframe(pg["tables"], use_container_width=True, hide_index=True)
if pg.get("error"):
    st.sidebar.caption(f"PostgreSQL: {pg['error']}")
if mongo.get("error"):
    st.sidebar.caption(f"MongoDB: {mongo['error']}")
if mongo.get("server_stats_error") or mongo.get("db_stats_error"):
    st.caption("Some MongoDB server or database metrics require additional monitoring privileges.")
