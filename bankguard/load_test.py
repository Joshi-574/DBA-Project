"""Run a bounded concurrent insert workload against both configured databases."""
import argparse
import os
import time
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
import psycopg
from pymongo import MongoClient

load_dotenv()

def postgres_run(total: int, workers: int) -> None:
    dsn = os.environ["POSTGRES_DSN"]
    def batch(bounds):
        start, stop = bounds
        with psycopg.connect(dsn) as conn, conn.cursor() as cur:
            cur.executemany("INSERT INTO concurrency_test(worker_id,operation_no) VALUES (%s,%s)", [(start % workers, i) for i in range(start, stop)])
    chunk = max(1, total // workers)
    ranges = [(i, min(total, i+chunk)) for i in range(0, total, chunk)]
    t = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(batch, ranges))
    print(f"PostgreSQL: {total:,} inserts, {workers} concurrent workers, {time.perf_counter()-t:.2f}s")

def mongo_run(total: int, workers: int) -> None:
    client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017/bankguard"), maxPoolSize=workers)
    coll = client[os.getenv("MONGO_DATABASE", "bankguard")].concurrency_test
    coll.create_index([("run_id", 1), ("operation_no", 1)], unique=True)
    run_id = str(time.time_ns())
    def batch(bounds):
        start, stop = bounds
        coll.insert_many([{"run_id": run_id, "worker_id": start % workers, "operation_no": i} for i in range(start, stop)], ordered=False)
    chunk = max(1, total // workers)
    ranges = [(i, min(total, i+chunk)) for i in range(0, total, chunk)]
    t = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(batch, ranges))
    print(f"MongoDB: {total:,} inserts, {workers} concurrent workers, {time.perf_counter()-t:.2f}s")
    client.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--operations", type=int, default=50000)
    parser.add_argument("--workers", type=int, default=32)
    args = parser.parse_args()
    if args.operations < 1 or args.workers < 1: parser.error("operations and workers must be positive")
    postgres_run(args.operations, args.workers)
    mongo_run(args.operations, args.workers)
