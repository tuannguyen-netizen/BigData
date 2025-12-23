"""
Simplified Flask app - serve everything from same origin
"""
from flask import Flask, jsonify, send_from_directory
from kafka import KafkaConsumer
import json
import threading
from collections import deque
import os

app = Flask(__name__, static_folder='.')

# Configuration
KAFKA_BROKER = "192.168.80.51:9092"
TOPIC = "house_prediction"

# Store latest predictions (max 100)
predictions = deque(maxlen=100)
stats = {
    'total': 0,
    'avg_price': 0,
    'max_price': 0,
    'min_price': 0
}

def consume_predictions():
    """Background thread to consume from Kafka"""
    try:
        consumer = KafkaConsumer(
            TOPIC,
            bootstrap_servers=KAFKA_BROKER,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='latest',
            enable_auto_commit=True,
            group_id='web_dashboard'
        )
        
        print(f"✓ Connected to Kafka: {KAFKA_BROKER}")
        print(f"✓ Consuming from topic: {TOPIC}")
        
        for message in consumer:
            prediction_data = message.value
            
            # Add to predictions list
            predictions.appendleft({
                'id': stats['total'] + 1,
                'prediction': prediction_data.get('prediction', 0),
                'features': {
                    'square_footage': prediction_data.get('f_4012', 0),
                    'bedrooms': prediction_data.get('f_3', 0),
                    'bathrooms': prediction_data.get('f_12', 0),
                    'year_built': prediction_data.get('f_2016', 0),
                    'lot_size': prediction_data.get('f_2_09809241489216', 0),
                    'garage': prediction_data.get('f_15', 0),
                    'neighborhood': prediction_data.get('f_5', 0)
                },
                'timestamp': message.timestamp
            })
            
            # Update stats
            stats['total'] += 1
            prices = [p['prediction'] for p in predictions]
            if prices:
                stats['avg_price'] = sum(prices) / len(prices)
                stats['max_price'] = max(prices)
                stats['min_price'] = min(prices)
            
            print(f"[{stats['total']}] Prediction: ${prediction_data.get('prediction', 0):,.2f}")
    except Exception as e:
        print(f"❌ Kafka consumer error: {e}")

# Start Kafka consumer in background thread
consumer_thread = threading.Thread(target=consume_predictions, daemon=True)
consumer_thread.start()

@app.route('/')
def index():
    """Serve dashboard HTML"""
    return send_from_directory('.', 'dashboard.html')

@app.route('/api/predictions')
def get_predictions():
    """API endpoint to get latest predictions"""
    return jsonify({
        'predictions': list(predictions)[:50],  # Return latest 50
        'stats': stats
    })

@app.route('/api/stats')
def get_stats():
    """API endpoint to get statistics"""
    return jsonify(stats)

if __name__ == '__main__':
    print("=" * 60)
    print("🌐 STARTING WEB DASHBOARD")
    print("=" * 60)
    print(f"Dashboard URL: http://0.0.0.0:5000")
    print(f"Kafka Broker: {KAFKA_BROKER}")
    print(f"Kafka Topic: {TOPIC}")
    print("=" * 60)
    print()
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
