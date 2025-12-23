# Hướng Dẫn Test DAG 02 - Streaming Pipeline

## Kiến Trúc
```
Producer (Nole3) → Kafka (Nole2) → Spark Streaming (Nole1) → Model (HDFS/Nole3) → Kafka (Nole2) → Consumer (Nole3)
```

## Bước 1: Chuẩn Bị (Trên Nole3)

### 1.1. Kiểm tra Kafka đang chạy trên Nole2
```bash
ssh nole2@192.168.80.51 "docker ps | grep kafka"
```

Nếu chưa chạy:
```bash
ssh nole2@192.168.80.51 "cd ~/kafka_docker && docker-compose up -d"
```

### 1.2. Tạo Kafka Topics
```bash
ssh nole2@192.168.80.51 "docker exec kafka kafka-topics --create --if-not-exists --bootstrap-server localhost:9092 --replication-factor 1 --partitions 1 --topic house_input"

ssh nole2@192.168.80.51 "docker exec kafka kafka-topics --create --if-not-exists --bootstrap-server localhost:9092 --replication-factor 1 --partitions 1 --topic house_prediction"
```

### 1.3. Verify Topics
```bash
ssh nole2@192.168.80.51 "docker exec kafka kafka-topics --list --bootstrap-server localhost:9092"
```

Phải thấy:
- house_input
- house_prediction

### 1.4. Kiểm tra Model đã train
```bash
~/hadoop/bin/hdfs dfs -ls /bigdata/house_prices/model/
```

Nếu chưa có → Chạy DAG 01 trước!

## Bước 2: Start Spark Streaming Job (Trên Nole1)

SSH vào Nole1:
```bash
ssh nole1@192.168.80.165
```

Submit Spark Streaming job:
```bash
~/spark/bin/spark-submit \
  --master spark://192.168.80.165:7077 \
  --deploy-mode client \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
  --conf spark.hadoop.fs.defaultFS=hdfs://192.168.80.178:8020 \
  --conf spark.driver.memory=2g \
  --conf spark.executor.memory=2g \
  ~/Tuan/Project/BigData/final_project/spark_code/spark_streaming.py
```

**Lưu ý:** Job này chạy liên tục, giữ terminal này mở!

## Bước 3: Start Consumer (Trên Nole3 - Terminal 1)

```bash
cd ~/Tuan/Project/BigData/final_project
python3 kafka_consumer.py
```

Consumer sẽ đợi predictions từ Kafka.

## Bước 4: Start Producer (Trên Nole3 - Terminal 2)

```bash
cd ~/Tuan/Project/BigData/final_project
python3 kafka_producer.py
```

Producer sẽ:
- Đọc `data/stream_data.csv`
- Gửi house features vào Kafka
- Mỗi 2 giây gửi 1 message

## Kết Quả Mong Đợi

**Terminal 1 (Consumer):**
```
[Prediction #1]
────────────────────────────────────────
📊 Input Features:
   square_footage: 4012.0
   num_bedrooms: 3.0
   num_bathrooms: 12.0
   year_built: 2016.0
   ...

💰 Predicted Price: $901,000.49

⏰ Timestamp: 2025-12-22 12:00:00
────────────────────────────────────────
```

**Terminal 2 (Producer):**
```
[1] Sent house data:
    Square Footage: 4012.0
    Bedrooms: 3.0
    Bathrooms: 12.0
    Year Built: 2016.0
    → Partition: 0, Offset: 0
```

## Troubleshooting

### Producer lỗi "KafkaTimeoutError"
```bash
# Check Kafka connectivity
telnet 192.168.80.51 9092

# Check topics exist
ssh nole2@192.168.80.51 "docker exec kafka kafka-topics --list --bootstrap-server localhost:9092"
```

### Spark Streaming không nhận data
```bash
# Check Spark UI
# http://192.168.80.165:4040

# Check Kafka có data
ssh nole2@192.168.80.51 "docker exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic house_input --from-beginning --max-messages 1"
```

### Consumer không nhận predictions
```bash
# Check output topic có data
ssh nole2@192.168.80.51 "docker exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic house_prediction --from-beginning --max-messages 1"
```

## Hoặc Dùng Airflow (Tự Động)

1. Mở Airflow UI: http://192.168.80.178:8080
2. Enable DAG: `02_Realtime_Streaming_Service`
3. Trigger DAG ▶️
4. Đợi Spark Streaming job start
5. Chạy Producer và Consumer như bước 3-4

---

**Luồng hoàn chỉnh:**
```
Producer → house_input (Kafka) → Spark Streaming → Load Model (HDFS) → Predict → house_prediction (Kafka) → Consumer
```
