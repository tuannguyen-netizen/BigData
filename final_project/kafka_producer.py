"""
Kafka Producer - Giả lập gửi dữ liệu house prices vào Kafka
Đọc từ stream_data.csv và gửi từng dòng vào topic house_input
"""
from kafka import KafkaProducer
import json
import time
import csv
import sys

# Configuration
KAFKA_BROKER = "192.168.80.51:9092"
TOPIC = "house_input"
DATA_FILE = "data/stream_data.csv"

def create_producer():
    """Tạo Kafka producer"""
    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BROKER,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            acks='all',
            retries=3
        )
        print(f"✓ Connected to Kafka broker: {KAFKA_BROKER}")
        return producer
    except Exception as e:
        print(f"❌ Cannot connect to Kafka: {e}")
        sys.exit(1)

def send_data(producer, interval=2):
    """
    Tự động generate và gửi house data vào Kafka (VÔ HẠN)
    Args:
        producer: Kafka producer instance
        interval: Thời gian chờ giữa các message (giây)
    """
    import random
    
    print(f"\n{'='*60}")
    print(f"KAFKA PRODUCER - HOUSE PRICE PREDICTION")
    print(f"{'='*60}")
    print(f"Topic: {TOPIC}")
    print(f"Mode: Auto-generate random house data (INFINITE)")
    print(f"Interval: {interval}s between messages")
    print(f"Press Ctrl+C to stop")
    print(f"{'='*60}\n")
    
    count = 0
    try:
        while True:  # Infinite loop
            # Generate random house data with CORRECT field names from training
            house_data = {
                "f_4012": round(random.uniform(1500, 6000), 2),
                "f_3": random.randint(2, 6),
                "f_12": round(random.uniform(1, 4), 1),
                "f_2016": random.randint(1990, 2024),
                "f_2_09809241489216": round(random.uniform(0.5, 5.0), 2),
                "f_15": random.randint(0, 3),
                "f_5": random.randint(1, 10)
            }
            
            # Send to Kafka
            try:
                future = producer.send(TOPIC, value=house_data)
                
                # Wait for confirmation
                record_metadata = future.get(timeout=10)
                count += 1
                
                print(f"\n{'─'*60}")
                print(f"[House #{count}] Sent to Kafka:")
                print(f"{'─'*60}")
                print(f"  🏠 Square Footage: {house_data['f_4012']:,.0f}")
                print(f"  🛏️  Bedrooms: {house_data['f_3']}")
                print(f"  🚿 Bathrooms: {house_data['f_12']}")
                print(f"  📅 Year Built: {house_data['f_2016']}")
                print(f"  🌳 Lot Size: {house_data['f_2_09809241489216']} acres")
                print(f"  🚗 Garage: {house_data['f_15']} cars")
                print(f"  ⭐ Neighborhood: {house_data['f_5']}/10")
                print(f"  📤 Partition: {record_metadata.partition}, Offset: {record_metadata.offset}")
                print(f"{'─'*60}")
                
                # Wait before sending next message
                print(f"⏳ Next house in {interval}s...")
                time.sleep(interval)
                    
            except Exception as e:
                print(f"❌ Failed to send house #{count+1}: {e}")
                time.sleep(1)  # Wait a bit before retry
                
    except KeyboardInterrupt:
        print("\n\n⚠️  Stopped by user")
    finally:
        producer.flush()
        producer.close()
        print(f"\n{'='*60}")
        print(f"✅ PRODUCER STOPPED")
        print(f"{'='*60}")
        print(f"Total houses sent: {count}")
        print(f"{'='*60}\n")

if __name__ == "__main__":
    print("Starting Kafka Producer...")
    print("Connecting to Kafka broker...")
    producer = create_producer()
    
    # Generate and send houses infinitely
    send_data(producer, interval=2)
