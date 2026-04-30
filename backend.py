from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# MongoDB configuration
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_URI_PREDICTIONS = os.getenv("MONGODB_URI_PREDICTIONS", MONGODB_URI)
MONGODB_DB = os.getenv("MONGODB_DB", "coldchain")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION", "sensors_data")
MONGODB_PREDICTIONS_COLLECTION = os.getenv("MONGODB_COLLECTION_PREDICTIONS", "predictions_on_real_time_data")
MONGODB_DECISIONS_COLLECTION = os.getenv("MONGODB_COLLECTION_DECISIONS", "decision_engine_outputs")

try:
    mongo_client = MongoClient(MONGODB_URI)
    db = mongo_client[MONGODB_DB]
    sensors_collection = db[MONGODB_COLLECTION]
    predictions_db_client = MongoClient(MONGODB_URI_PREDICTIONS)
    predictions_db = predictions_db_client[MONGODB_DB]
    predictions_collection = predictions_db[MONGODB_PREDICTIONS_COLLECTION]
    decisions_collection = db[MONGODB_DECISIONS_COLLECTION]
    logger.info("Connected to MongoDB successfully")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
    mongo_client = None
    db = None
    sensors_collection = None
    predictions_collection = None
    decisions_collection = None


@app.route('/api/sensors/<data_id>', methods=['GET'])
def get_sensor_data(data_id):
    """Fetch live sensor data from MongoDB"""
    try:
        if sensors_collection is None:
            return jsonify({"error": "Database connection failed"}), 500

        # Always fetch the latest document for this asset
        sensor_data = sensors_collection.find_one(
            {"asset_id": data_id},
            sort=[("timestamp", -1)]
        )
        
        if not sensor_data:
            return jsonify({"error": f"Data ID {data_id} not found"}), 404

        # Convert ObjectId to string for JSON serialization
        sensor_data['_id'] = str(sensor_data.get('_id', ''))
        
        return jsonify(sensor_data), 200
    except Exception as e:
        logger.error(f"Error fetching sensor data: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/risk/<data_id>', methods=['GET'])
def get_risk_analysis(data_id):
    """Fetch risk analysis from MongoDB"""
    try:
        if sensors_collection is None:
            return jsonify({"error": "Database connection failed"}), 500

        requested_timestamp = request.args.get("timestamp")
        sensor_query = {"asset_id": data_id}
        if requested_timestamp:
            sensor_query["timestamp"] = requested_timestamp

        # If timestamp is supplied by frontend, use the exact same reading.
        if requested_timestamp:
            sensor_data = sensors_collection.find_one(sensor_query)
        else:
            sensor_data = sensors_collection.find_one(sensor_query, sort=[("timestamp", -1)])
        
        if not sensor_data:
            return jsonify({"error": f"Data ID {data_id} not found"}), 404
        
        # Generate risk analysis based on sensor data
        risk_data = generate_risk_analysis(sensor_data)
        
        risk_data['_id'] = str(risk_data.get('_id', ''))
        
        return jsonify(risk_data), 200
    except Exception as e:
        logger.error(f"Error fetching risk analysis: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/summary/<data_id>', methods=['GET'])
def get_summary(data_id):
    """Fetch GenAI-generated summary from MongoDB"""
    try:
        if sensors_collection is None:
            return jsonify({"error": "Database connection failed"}), 500

        requested_timestamp = request.args.get("timestamp")
        sensor_query = {"asset_id": data_id}
        if requested_timestamp:
            sensor_query["timestamp"] = requested_timestamp

        # If timestamp is supplied by frontend, use the exact same reading.
        if requested_timestamp:
            sensor_data = sensors_collection.find_one(sensor_query)
        else:
            sensor_data = sensors_collection.find_one(sensor_query, sort=[("timestamp", -1)])
        
        if not sensor_data:
            return jsonify({"error": f"Data ID {data_id} not found"}), 404
        
        # Generate risk analysis first
        risk_data = generate_risk_analysis(sensor_data)
        
        # Generate summary
        summary_data = generate_summary(risk_data)
        
        summary_data['_id'] = str(summary_data.get('_id', ''))
        
        return jsonify(summary_data), 200
    except Exception as e:
        logger.error(f"Error fetching summary: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/all-data', methods=['GET'])
def get_all_data():
    """Fetch all sensor data from MongoDB"""
    try:
        if sensors_collection is None:
            return jsonify({"error": "Database connection failed"}), 500

        all_sensors = list(sensors_collection.find({}).sort("timestamp", -1).limit(100))
        
        # Convert ObjectId to string for JSON serialization
        for sensor in all_sensors:
            sensor['_id'] = str(sensor.get('_id', ''))
        
        return jsonify(all_sensors), 200
    except Exception as e:
        logger.error(f"Error fetching all data: {e}")
        return jsonify({"error": str(e)}), 500


def generate_risk_analysis(sensor_data):
    """Generate risk analysis based on sensor data"""
    try:
        # Extract sensor readings
        temperature = sensor_data.get("temperature", 5.0)
        humidity = sensor_data.get("humidity", 50.0)
        vibration = sensor_data.get("vibration", 0.5)
        cargo_type = sensor_data.get("cargo_type", "vaccines")
        asset_id = sensor_data.get("asset_id", "unknown")
        
        # Risk scoring logic
        risk_score = 0
        warnings = []
        
        # Temperature risk assessment
        if cargo_type == "vaccines":
            if temperature < 2.0 or temperature > 8.0:
                risk_score += 30
                warnings.append(f"Temperature {temperature}°C is outside vaccine range (2-8°C)")
            elif temperature < 0.0 or temperature > 12.0:
                risk_score += 50
                warnings.append(f"CRITICAL: Temperature {temperature}°C is outside hard limits (0-12°C)")
        
        # Humidity risk assessment
        if humidity < 30.0 or humidity > 60.0:
            risk_score += 20
            warnings.append(f"Humidity {humidity}% is outside optimal range (30-60%)")
        
        # Vibration risk assessment
        if vibration > 2.5:
            risk_score += 20
            warnings.append(f"Vibration {vibration}g exceeds warning threshold (2.5g)")
        if vibration > 5.0:
            risk_score += 30
            warnings.append(f"CRITICAL: Vibration {vibration}g exceeds critical threshold (5.0g)")
        
        # Determine risk level
        if risk_score >= 50:
            risk_level = "CRITICAL"
        elif risk_score >= 30:
            risk_level = "HIGH"
        elif risk_score >= 15:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        return {
            "data_id": asset_id,
            "risk_score": min(risk_score, 100),
            "risk_level": risk_level,
            "warnings": warnings,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source_timestamp": sensor_data.get("timestamp"),
            "sensor_readings": {
                "temperature": temperature,
                "humidity": humidity,
                "vibration": vibration,
                "cargo_type": cargo_type
            }
        }
    except Exception as e:
        logger.error(f"Error generating risk analysis: {e}")
        return {
            "data_id": sensor_data.get("asset_id", "unknown"),
            "error": str(e)
        }


def generate_summary(risk_data):
    """Generate GenAI summary based on risk analysis"""
    try:
        risk_level = risk_data.get("risk_level", "UNKNOWN")
        risk_score = risk_data.get("risk_score", 0)
        warnings = risk_data.get("warnings", [])
        
        # Generate summary based on risk level
        if risk_level == "CRITICAL":
            summary_text = (
                f"Critical risk detected (score: {risk_score}/100). "
                "Current shipment conditions indicate a high probability of spoilage without immediate intervention."
            )
        elif risk_level == "HIGH":
            summary_text = (
                f"High risk detected (score: {risk_score}/100). "
                "Environmental conditions are trending outside control limits and require prompt mitigation."
            )
        elif risk_level == "MEDIUM":
            summary_text = (
                f"Moderate risk detected (score: {risk_score}/100). "
                "Some variables are approaching tolerance thresholds and should be monitored closely."
            )
        else:
            summary_text = (
                f"Low risk detected (score: {risk_score}/100). "
                "Shipment conditions are stable and within recommended operating range."
            )
        
        warnings_text = "\n".join([f"• {warning}" for warning in warnings])
        
        return {
            "data_id": risk_data.get("data_id", "unknown"),
            "summary": summary_text,
            "warnings": warnings_text,
            "recommendation": get_recommendation(risk_level, warnings),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        return {
            "data_id": risk_data.get("data_id", "unknown"),
            "error": str(e)
        }


def get_recommendation(risk_level, warnings):
    """Get recommended actions based on risk level"""
    if risk_level == "CRITICAL":
        return "Immediately reduce temperature. Contact logistics team. Consider diverting cargo."
    elif risk_level == "HIGH":
        return "Increase monitoring frequency. Prepare contingency routes. Alert refrigeration team."
    elif risk_level == "MEDIUM":
        return "Monitor conditions closely. Prepare to adjust temperature or route."
    else:
        return "Maintain current conditions. Continue routine monitoring."


@app.route('/api/predictions/<data_id>', methods=['GET'])
def get_predictions(data_id):
    """Fetch live ML predictions strictly from MongoDB"""
    try:
        if predictions_collection is None:
            return jsonify({
                "predicted_risk": None,
                "time_to_failure_hours": None,
                "timestamp": None,
                "source": "mongodb_unavailable",
                "message": "Predictions collection is not available."
            }), 200

        prediction = predictions_collection.find_one(
            {"asset_id": data_id},
            sort=[("timestamp", -1)]
        )

        if not prediction:
            return jsonify({
                "predicted_risk": None,
                "time_to_failure_hours": None,
                "timestamp": None,
                "source": "mongodb_live",
                "message": "No live prediction found in MongoDB for this shipment."
            }), 200

        prediction["_id"] = str(prediction.get("_id", ""))
        predicted_risk = prediction.get("predicted_risk")
        if predicted_risk is None:
            predicted_risk = prediction.get("predicted_risk_proxy")

        return jsonify({
            "predicted_risk": predicted_risk,
            "time_to_failure_hours": prediction.get("time_to_failure_hours"),
            "timestamp": prediction.get("timestamp"),
            "source": "mongodb_live",
            "message": None
        }), 200
    except Exception as e:
        logger.error(f"Error fetching predictions: {e}")
        return jsonify({
            "error": str(e),
            "predicted_risk": None,
            "time_to_failure_hours": None,
            "timestamp": None,
            "source": "error"
        }), 200


@app.route('/api/decisions/<data_id>', methods=['GET'])
def get_decisions(data_id):
    """Fetch decision engine output with nearest centres and navigation"""
    try:
        # Try to get from MongoDB first
        if decisions_collection is not None:
            decision = decisions_collection.find_one(
                {"asset_id": data_id},
                sort=[("timestamp", -1)]
            )
            
            if decision:
                decision['_id'] = str(decision.get('_id', ''))
                return jsonify({
                    "nearest_centres": decision.get("nearest_distribution_centers", []),
                    "routing_recommendation": decision.get("routing_recommendation", None),
                    "source": "decision_engine"
                }), 200

        # Fallback: generate sample distribution centres
        distribution_centres = [
            {
                "id": "DC_AGRA_001",
                "name": "Agra Cold Hub",
                "distance_km": 45.2,
                "eta_hours": 1.2,
                "available_capacity": 850,
                "location": [27.1767, 78.0081],
                "refrigeration_status": "✅ Optimal"
            },
            {
                "id": "DC_MATHURA_001", 
                "name": "Mathura Distribution Centre",
                "distance_km": 68.5,
                "eta_hours": 1.8,
                "available_capacity": 1200,
                "location": [27.4924, 77.6736],
                "refrigeration_status": "✅ Optimal"
            },
            {
                "id": "DC_GHAZIABAD_001",
                "name": "Ghaziabad Regional Hub",
                "distance_km": 92.3,
                "eta_hours": 2.4,
                "available_capacity": 950,
                "location": [28.6692, 77.4538],
                "refrigeration_status": "✅ Optimal"
            }
        ]

        routing_recommendation = {
            "recommendation": f"Route to Agra Cold Hub (45.2 km, 1.2 hours ETA). Optimal capacity available.",
            "alternate_destination": "Mathura Distribution Centre is available as backup"
        }
        
        return jsonify({
            "nearest_centres": distribution_centres,
            "routing_recommendation": routing_recommendation,
            "source": "generated"
        }), 200
    except Exception as e:
        logger.error(f"Error fetching decisions: {e}")
        return jsonify({"nearest_centres": [], "routing_recommendation": None}), 200
        
        # Extract nearest centres and routing info
        nearest_centres = decision.get("routing_recommendation", {}).get("nearest_distribution_centers", [])
        
        # Format nearest centres for UI
        formatted_centres = []
        for centre in nearest_centres[:3]:  # Top 3 closest
            formatted_centres.append({
                "id": centre.get("id", ""),
                "name": centre.get("name", ""),
                "distance_km": centre.get("distance_km", 0),
                "eta_hours": centre.get("eta_hours", 0),
                "available_capacity": centre.get("available_capacity", 0),
                "location": centre.get("location", [])
            })
        
        return jsonify({
            "nearest_centres": formatted_centres,
            "routing_recommendation": decision.get("routing_recommendation", {}),
            "refrigeration_recommendation": decision.get("refrigeration_recommendation", {}),
            "predicted_risk": decision.get("predicted_risk", 0),
            "timestamp": decision.get("timestamp", ""),
            "full_decision": decision
        }), 200
    except Exception as e:
        logger.error(f"Error fetching decisions: {e}")
        return jsonify({"error": str(e), "nearest_centres": []}), 200


@app.route('/api/live-dashboard/<data_id>', methods=['GET'])
def get_live_dashboard(data_id):
    """Get comprehensive dashboard with sensor, risk, prediction, and decision data"""
    try:
        response = {}
        
        # Get sensor data
        if sensors_collection:
            sensor_data = sensors_collection.find_one({"asset_id": data_id})
            if sensor_data:
                sensor_data['_id'] = str(sensor_data.get('_id', ''))
                response['sensor_data'] = sensor_data
        
        # Get risk analysis
        if sensors_collection:
            sensor_data = sensors_collection.find_one(
                {"asset_id": data_id},
                sort=[("timestamp", -1)]
            )
            if sensor_data:
                risk_data = generate_risk_analysis(sensor_data)
                response['actual_risk'] = risk_data
                response['summary'] = generate_summary(risk_data)
        
        # Get predictions
        if predictions_collection:
            prediction = predictions_collection.find_one(
                {"asset_id": data_id},
                sort=[("timestamp", -1)]
            )
            if prediction:
                prediction['_id'] = str(prediction.get('_id', ''))
                response['predicted_risk'] = prediction.get("predicted_risk_proxy", 0)
                response['prediction_data'] = prediction
        
        # Get decision engine output
        if decisions_collection:
            decision = decisions_collection.find_one(
                {"asset_id": data_id},
                sort=[("timestamp", -1)]
            )
            if decision:
                decision['_id'] = str(decision.get('_id', ''))
                nearest_centres = decision.get("routing_recommendation", {}).get("nearest_distribution_centers", [])
                
                formatted_centres = []
                for centre in nearest_centres[:3]:
                    formatted_centres.append({
                        "id": centre.get("id", ""),
                        "name": centre.get("name", ""),
                        "distance_km": centre.get("distance_km", 0),
                        "eta_hours": centre.get("eta_hours", 0),
                        "available_capacity": centre.get("available_capacity", 0),
                        "location": centre.get("location", [])
                    })
                
                response['nearest_centres'] = formatted_centres
                response['routing_recommendation'] = decision.get("routing_recommendation", {})
                response['decision_data'] = decision
        
        return jsonify(response), 200
    except Exception as e:
        logger.error(f"Error fetching live dashboard: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
