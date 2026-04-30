#!/usr/bin/env python3
"""
Standalone data generator for cold-chain monitoring system.
Generates sensor data and stores it in MongoDB.
"""

import os
import sys
import json
import time
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent / "iot-simulator"))

from dotenv import load_dotenv
from pymongo import MongoClient

from sensors import (
    ColdChainSensorSimulator,
    ShipmentScenario,
    Route,
    CARGO_PROFILES,
)

load_dotenv()

# MongoDB configuration
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "coldchain")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION", "sensors")

def init_mongo():
    """Initialize MongoDB connection"""
    try:
        client = MongoClient(MONGODB_URI)
        db = client[MONGODB_DB]
        collection = db[MONGODB_COLLECTION]
        
        # Test connection
        client.admin.command('ping')
        print(f"✅ Connected to MongoDB at {MONGODB_URI}")
        return client, collection
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        return None, None

def generate_sensor_data(fleet_size: int = 50, interval_sec: int = 2):
    """Generate sensor data for multiple trucks"""
    
    client, collection = init_mongo()
    if collection is None:
        print("❌ Cannot proceed without MongoDB")
        return
    
    # Create simulators for each truck
    simulators = []
    cargo_types = list(CARGO_PROFILES.keys())[:5]  # Use first 5 cargo types
    
    for i in range(fleet_size):
        asset_id = f"TRUCK_{i+1:03d}"
        cargo_type = random.choice(cargo_types)
        scenario = random.choice(["normal", "micro_excursions", "refrigeration_failure"])
        
        # Create route
        route = Route(
            origin=(27.1767, 78.0081),
            destination=(28.7041, 77.1025),
            waypoints=[(27.4924, 77.6737)]
        )
        
        sim = ColdChainSensorSimulator(
            asset_id=asset_id,
            cargo_type=cargo_type,
            scenario=ShipmentScenario(scenario),
            route=route,
            publish_interval_sec=interval_sec,
            seed=i
        )
        
        simulators.append({
            "asset_id": asset_id,
            "cargo_type": cargo_type,
            "simulator": sim
        })
    
    print(f"🚚 Created {fleet_size} truck simulators")
    print("=" * 60)
    print("📡 Generating and storing sensor data...")
    print("=" * 60)
    
    try:
        iteration = 0
        while True:
            iteration += 1
            print(f"\n🔄 Iteration {iteration}")
            
            for truck_data in simulators:
                sim = truck_data["simulator"]
                telemetry = sim.get_telemetry()
                
                # Store in MongoDB
                try:
                    result = collection.insert_one(telemetry)
                    print(f"  ✅ {truck_data['asset_id']}: Stored (ID: {str(result.inserted_id)[:8]}...)")
                except Exception as e:
                    print(f"  ❌ {truck_data['asset_id']}: Error storing - {e}")
            
            print(f"  📊 Total documents in MongoDB: {collection.count_documents({})}")
            
            # Wait before next iteration
            time.sleep(interval_sec)
            
    except KeyboardInterrupt:
        print("\n\n⛔ Data generation stopped by user")
    finally:
        if client:
            client.close()
            print("✅ MongoDB connection closed")

if __name__ == "__main__":
    fleet_size = 50
    interval_sec = 2
    
    print("=" * 60)
    print("🚀 Cold-Chain Sensor Data Generator")
    print("=" * 60)
    print(f"📦 Fleet Size: {fleet_size}")
    print(f"⏱️  Interval: {interval_sec}s")
    
    generate_sensor_data(fleet_size=fleet_size, interval_sec=interval_sec)
