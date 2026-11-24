import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
db = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017/bankguard"))[os.getenv("MONGO_DATABASE", "bankguard")]
print("High balance accounts:", list(db.accounts.find({"balance": {"$gte": 5000}}, {"_id": 0}).limit(10)))
print("Account counts by type:", list(db.accounts.aggregate([{"$group": {"_id": "$type", "count": {"$sum": 1}}}])) )
print("Mongo server status:", db.command("serverStatus")["connections"])
