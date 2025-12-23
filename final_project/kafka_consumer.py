"""
Kafka Consumer - Đọc predictions từ Kafka và hiển thị
Đọc từ topic house_prediction và in ra kết quả dự đoán
"""
from kafka import KafkaConsumer
import json
import sys

# Configuration
KAFKA_BROKER = "192.168.80.51:9092"
TOPIC = "house_prediction"

def create_consumer():
    """Tạo Kafka consumer"""
    try:
        consumer = KafkaConsumer(
            TOPIC,
            bootstrap_servers=KAFKA_BROKER,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='latest',  # Chỉ đọc message mới
            enable_auto_commit=True,
            group_id='prediction_viewer'
        )
        print(f"✓ Connected to Kafka broker: {KAFKA_BROKER}")
        print(f"✓ Subscribed to topic: {TOPIC}")
        return consumer
    except Exception as e:
        print(f"❌ Cannot connect to Kafka: {e}")
        sys.exit(1)

def consume_predictions(consumer):
    """
    Đọc và hiển thị predictions từ Kafka
    """
    print(f"\n{'='*80}")
    print(f"KAFKA CONSUMER - REAL-TIME PREDICTIONS VIEWER")
    print(f"{'='*80}")
    print(f"Waiting for predictions from topic: {TOPIC}")
    print(f"Press Ctrl+C to stop")
    print(f"{'='*80}\n")
    
    count = 0
    try:
        for message in consumer:
            count += 1
            prediction = message.value
            
            print(f"\n{'─'*80}")
            print(f"[Prediction #{count}]")
            print(f"{'─'*80}")
            
            # Display input features
            if 'features' in prediction:
                print("📊 Input Features:")
                features = prediction['features']
                if isinstance(features, dict):
                    for key, value in features.items():
                        print(f"   {key}: {value}")
                else:
                    print(f"   {features}")
            
            # Display prediction
            if 'prediction' in prediction:
                print(f"\n💰 Predicted Price: ${prediction['prediction']:,.2f}")
            
            # Display timestamp
            if 'timestamp' in prediction:
                print(f"⏰ Timestamp: {prediction['timestamp']}")
            
            # Display full message
            print(f"\n📦 Full Message:")
            print(f"   {json.dumps(prediction, indent=2)}")
            
            print(f"{'─'*80}")
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Stopped by user")
    finally:
        consumer.close()
        print(f"\n✓ Consumer closed. Total predictions received: {count}")

if __name__ == "__main__":
    print("Starting Kafka Consumer...")
    consumer = create_consumer()
    consume_predictions(consumer)
