import os
from datetime import datetime, timezone
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017/bankguard"), serverSelectionTimeoutMS=5000)
db = client[os.getenv("MONGO_DATABASE", "bankguard")]
db.customers.create_index("customer_id", unique=True)
db.transactions.create_index([("account_id", 1), ("occurred_at", -1)])
db.fraud_events.create_index([("resolved", 1), ("risk_score", -1)])
db.customers.bulk_write([
    __import__("pymongo").ReplaceOne({"customer_id": n}, {"customer_id": n, "name": f"Customer {n:04d}", "email": f"customer{n}@example.test", "created_at": datetime.now(timezone.utc)}, upsert=True)
    for n in range(1, 501)
])
db.accounts.bulk_write([
    __import__("pymongo").ReplaceOne({"account_id": n}, {"account_id": n, "customer_id": n, "type": ["checking", "savings", "business"][n % 3], "balance": round(1000 + n * 17.35, 2)}, upsert=True)
    for n in range(1, 501)
])
print(f"Seeded {db.customers.count_documents({})} customers and {db.accounts.count_documents({})} accounts in {db.name}")
