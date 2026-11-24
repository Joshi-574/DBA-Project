# 🛡️ BankGuard – Database Administration Dashboard & Replication Lab

**BankGuard** is a database administration and monitoring platform built using Python, Streamlit, PostgreSQL, MongoDB, and Docker. It provides a unified interface for database monitoring, replication health analysis, query optimization, sharding visualization, transaction management concepts, and database security experiments.

The project combines a monitoring dashboard with a local database infrastructure lab to demonstrate practical Database Administration (DBA) concepts.

## 🚀 Key Features

- **Slow Queries:** Identify and analyze expensive PostgreSQL queries using query statistics.
- **Replication Health:** Monitor PostgreSQL streaming replication and MongoDB replica-set health.
- **Shard Balance:** Visualize MongoDB sharding and document distribution across shards.
- **Index Advisor:** Explore index recommendations and query optimization.
- **Lab Execution:** Demonstrate ACID properties, transaction isolation levels, concurrency, and SQL concepts.
- **Fraud & Audit:** Explore database audit and fraud-monitoring concepts.
- **Docker Replication Lab:** Run a local PostgreSQL primary with two replicas and a MongoDB sharded cluster.

## 🏗️ Technology Stack

| Component | Technology |
|---|---|
| Frontend / Dashboard | Streamlit |
| Programming Language | Python |
| Relational Database | PostgreSQL 18 |
| NoSQL Database | MongoDB 8 |
| Containerization | Docker & Docker Compose |
| Data Processing | Pandas |
| Database Connectivity | PostgreSQL and MongoDB drivers |

## 🗂️ Project Structure

```text
BankGuard/
│
├── dashboard.py
├── requirements.txt
├── docker-compose.yml
├── .env.example
├── .gitignore
│
├── bankguard/
│   ├── load_test.py
│   ├── mongo_queries.py
│   └── seed_mongo.py
│
├── docker/
│   └── postgres/
│       ├── 01_replication_user.sh
│       └── 20_seed_bankguard.sql
│
├── sql/
│   ├── 01_foundation.sql
│   ├── 02_queries_and_security.sql
│   └── 03_query_optimization.sql
│
└── reference_material/
    └── BankGuard_SQL_Files/
        ├── Database and Tables
        ├── DCL and TCL Commands
        ├── Joins and Window Functions
        ├── Query Optimization
        ├── Transaction Isolation
        └── Deadlock Experiments
```

## ⚙️ Prerequisites

Install the following before running the project:

- Python 3.10 or later
- Docker Desktop
- Git
- VS Code (recommended)
- PostgreSQL and MongoDB connectivity for monitoring external databases

## 📥 Installation

**1. Clone the repository**

```bash
git clone https://github.com/Joshi-574/DBA-Project.git
cd DBA-Project
```

**2. Create a virtual environment**

Windows:

```cmd
python -m venv .venv
.venv\Scripts\activate
```

**3. Install dependencies**

```bash
python -m pip install -r requirements.txt
```

**4. Configure environment variables**

```cmd
copy .env.example .env
```

Update `.env` with your local PostgreSQL and MongoDB connection settings. Never commit real credentials.

**5. Start the dashboard**

```bash
streamlit run dashboard.py
```

Open the local URL displayed in the terminal.

## 🐳 Docker Replication Lab

Make sure Docker Desktop is running.

Start the infrastructure:

```bash
docker compose up -d
```

Check container status:

```bash
docker compose ps
```

The local Docker lab provides:

### PostgreSQL Streaming Replication

- One PostgreSQL primary
- Two physical streaming replicas
- WAL-based replication monitoring
- Replica lag and heartbeat observation

### MongoDB Sharded Cluster

- One mongos router
- One config-server process
- Three shard processes
- 6,000 demonstration documents
- 2,000 documents assigned to each shard

**Local ports:**

| Service | Port |
|---|---:|
| PostgreSQL Primary | 5433 |
| PostgreSQL Replica 1 | 5434 |
| PostgreSQL Replica 2 | 5435 |
| MongoDB mongos | 27020 |
| MongoDB Shard 1 | 27101 |
| MongoDB Shard 2 | 27102 |
| MongoDB Shard 3 | 27103 |

Stop containers:

```bash
docker compose down
```

To remove the lab's stored database volumes as well:

```bash
docker compose down -v
```

**Warning:** The second command permanently removes the Docker lab's stored database data.

## 🧪 Database Concepts Demonstrated

- ACID properties
- Transaction isolation levels
- Concurrent transactions
- Deadlock experiments
- SQL joins and window functions
- Database access control
- Query optimization
- PostgreSQL WAL and streaming replication
- MongoDB replica sets and sharding

## 📊 Architecture Overview

```text
              BANKGUARD DASHBOARD
                  Streamlit
                      |
          +-----------+-----------+
          |                       |
      PostgreSQL                MongoDB
          |                       |
     Primary Node              mongos Router
       /      \                /     |     \
   Replica1 Replica2         Shard1 Shard2 Shard3
          |                       |
     WAL Monitoring          Shard Distribution
          |                       |
          +-----------+-----------+
                      |
               DBA Monitoring
```

## ⚠️ Project Limitations

- The Docker infrastructure is intended for local learning and demonstration.
- The one-process-per-shard setup is not a highly available production cluster.
- Dashboard monitoring depends on valid database connections and enabled database extensions.
- Lab Execution simulations do not modify actual database records.

## 🎯 Project Objective

The main objective of BankGuard is to demonstrate practical Database Administration skills through a unified dashboard and hands-on database infrastructure, combining relational databases, NoSQL databases, replication, sharding, query optimization, and transaction management.

---

**Developed as a Database Administration project.**

GitHub: https://github.com/Joshi-574/DBA-Project
