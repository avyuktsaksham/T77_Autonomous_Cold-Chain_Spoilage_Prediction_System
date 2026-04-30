#!/usr/bin/env python3

import os
from dotenv import load_dotenv
from pymongo import MongoClient

# Load environment
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "coldchain")

print(f"🔗 Connecting to MongoDB: {MONGODB_URI}")
client = MongoClient(MONGODB_URI)
db = client[MONGODB_DB]

# List collections
print("\n📦 Collections in database:")
collections = db.list_collection_names()
for col in collections:
    count = db[col].count_documents({})
    print(f"  - {col}: {count} documents")

# Check predictions collection
print("\n📊 Predictions Data (first 3 docs):")
predictions = list(db['predictions_on_real_time_data'].find().limit(3))
for pred in predictions:
    print(f"  - {pred.get('asset_id', 'N/A')}: {pred.get('predicted_risk', 'N/A')}, TTF: {pred.get('time_to_failure_hours', 'N/A')}")

# Check decisions collection
print("\n🤖 Decisions Data (first 3 docs):")
decisions = list(db['decision_engine_outputs'].find().limit(3))
for dec in decisions:
    print(f"  - {dec.get('asset_id', 'N/A')}: {dec.get('routing_recommendation', 'N/A')}")

print("\n✅ MongoDB check complete")
