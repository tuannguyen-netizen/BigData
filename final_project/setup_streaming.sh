#!/bin/bash
# Script để setup và test streaming pipeline

set -e

echo "=========================================="
echo "STREAMING PIPELINE SETUP"
echo "=========================================="
echo ""

# 1. Check Kafka is running on Nole2
echo "[1/4] Checking Kafka on Nole2..."
if ssh nole2@192.168.80.51 "docker ps | grep kafka" > /dev/null 2>&1; then
    echo "✓ Kafka is running"
else
    echo "⚠️  Kafka not running, starting..."
    ssh nole2@192.168.80.51 "cd ~/kafka_docker && docker-compose up -d"
    sleep 10
fi

# 2. Create Kafka topics
echo ""
echo "[2/4] Creating Kafka topics..."
ssh nole2@192.168.80.51 "docker exec kafka kafka-topics --create --if-not-exists --bootstrap-server localhost:9092 --replication-factor 1 --partitions 1 --topic house_input" || true
ssh nole2@192.168.80.51 "docker exec kafka kafka-topics --create --if-not-exists --bootstrap-server localhost:9092 --replication-factor 1 --partitions 1 --topic house_prediction" || true

# 3. Verify topics
echo ""
echo "[3/4] Verifying topics..."
ssh nole2@192.168.80.51 "docker exec kafka kafka-topics --list --bootstrap-server localhost:9092"

# 4. Check model exists on HDFS
echo ""
echo "[4/4] Checking model on HDFS..."
if ssh nole3@192.168.80.178 "~/hadoop/bin/hdfs dfs -test -d /bigdata/house_prices/model"; then
    echo "✓ Model exists on HDFS"
else
    echo "❌ Model not found! Run DAG 01 (Training) first!"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ SETUP COMPLETE"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Start Spark Streaming (trigger DAG 02 or run manually)"
echo "2. Run consumer: python3 kafka_consumer.py"
echo "3. Run producer: python3 kafka_producer.py"
echo ""
