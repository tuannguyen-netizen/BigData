# HƯỚNG DẪN SETUP VỚI SPARK 4.0.1 ĐÃ CÓ SẴN

## NOLE1 - Spark Master + Worker

### Bước 1: SSH vào Nole1
```bash
ssh nole1@192.168.80.165
```

### Bước 2: Cài đặt Java (nếu chưa có)
```bash
sudo apt-get update
sudo apt-get install -y openjdk-11-jdk
java -version
```

### Bước 3: Cấu hình /etc/hosts
```bash
sudo nano /etc/hosts
```

Thêm các dòng (hoặc sửa nếu đã có):
```
192.168.80.165  nole1
192.168.80.51   nole2
192.168.80.178  nole3
```

Lưu (Ctrl+O, Enter, Ctrl+X)

### Bước 4: Tìm đường dẫn Spark hiện tại
```bash
# Tìm Spark
find ~ -name "spark-4.0.1*" -type d 2>/dev/null

# Hoặc kiểm tra biến môi trường
echo $SPARK_HOME
```

**Giả sử Spark ở:** `~/spark-4.0.1-bin-hadoop3`

### Bước 5: Cấu hình Spark

#### 5a. Thêm vào ~/.bashrc (nếu chưa có)
```bash
cat >> ~/.bashrc << 'EOF'
export SPARK_HOME=~/spark-4.0.1-bin-hadoop3
export PATH=$PATH:$SPARK_HOME/bin:$SPARK_HOME/sbin
EOF

source ~/.bashrc
```

#### 5b. Tạo spark-env.sh
```bash
cat > $SPARK_HOME/conf/spark-env.sh << 'EOF'
export SPARK_MASTER_HOST=nole1
export SPARK_MASTER_PORT=7077
export SPARK_MASTER_WEBUI_PORT=8080
export SPARK_WORKER_CORES=4
export SPARK_WORKER_MEMORY=4g
EOF

chmod +x $SPARK_HOME/conf/spark-env.sh
```

#### 5c. Tạo workers file
```bash
cat > $SPARK_HOME/conf/workers << 'EOF'
nole1
nole2
EOF
```

### Bước 6: Tạo thư mục project
```bash
mkdir -p ~/Documents/bigdata
```

### Bước 7: Cài đặt Python dependencies
```bash
# Cài pyspark 4.0.1 để match với Spark version
pip3 install --user pyspark==4.0.1 celery pika pandas scikit-learn kafka-python
```

### Bước 8: Start Spark Master
```bash
$SPARK_HOME/sbin/start-master.sh

# Kiểm tra
jps | grep Master
```

**Verify:** Mở browser http://192.168.80.165:8080

### Bước 9: Start Spark Worker (local)
```bash
$SPARK_HOME/sbin/start-worker.sh spark://nole1:7077

# Kiểm tra
jps | grep Worker
```

Refresh browser, phải thấy 1 worker đã kết nối.

### Bước 10: Copy project code (từ máy development)
```bash
# Chạy từ máy development (máy tuan_nguyen)
scp -r ~/Tuan/Project/BigData/final_project nole1@192.168.80.165:~/Documents/bigdata/
```

### Bước 11: Install project dependencies (trên Nole1)
```bash
cd ~/Documents/bigdata/final_project
pip3 install --user -r requirements.txt
```

### Bước 12: Start Celery Worker
```bash
cd ~/Documents/bigdata/final_project
celery -A mycelery.system_worker worker \
  --loglevel=info \
  --queues=spark_master \
  --hostname=spark_worker@nole1 \
  --broker=pyamqp://guest@192.168.80.178//
```

**Để chạy background:**
```bash
nohup celery -A mycelery.system_worker worker \
  --loglevel=info \
  --queues=spark_master \
  --hostname=spark_worker@nole1 \
  --broker=pyamqp://guest@192.168.80.178// \
  > celery_nole1.log 2>&1 &
```

---

## NOLE2 - Kafka + Spark Worker

### Bước 1: SSH vào Nole2
```bash
ssh nole2@192.168.80.51
```

### Bước 2: Cài đặt Docker (nếu chưa có)
```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose
sudo usermod -aG docker $USER

# Logout và login lại để áp dụng group
exit
ssh nole2@192.168.80.51

# Verify
docker --version
```

### Bước 3: Cấu hình /etc/hosts
```bash
sudo nano /etc/hosts
```

Thêm các dòng:
```
192.168.80.165  nole1
192.168.80.51   nole2
192.168.80.178  nole3
```

### Bước 4: Setup Kafka
```bash
mkdir -p ~/kafka-cluster

cat > ~/kafka-cluster/docker-compose.yml << 'EOF'
version: '3'
services:
  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    hostname: zookeeper
    container_name: zookeeper
    ports:
      - "2181:2181"
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    hostname: kafka
    container_name: kafka
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
      - "29092:29092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: 'zookeeper:2181'
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:29092,PLAINTEXT_HOST://192.168.80.51:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 1
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
EOF
```

### Bước 5: Start Kafka
```bash
cd ~/kafka-cluster
docker-compose up -d

# Verify
docker ps
# Phải thấy 2 containers: kafka và zookeeper
```

### Bước 6: Tìm hoặc cài Spark

#### Option A: Nếu đã có Spark 4.0.1
```bash
find ~ -name "spark-4.0.1*" -type d 2>/dev/null
```

#### Option B: Nếu chưa có, copy từ Nole1
```bash
# Trên Nole1
cd ~
tar -czf spark-4.0.1.tar.gz spark-4.0.1-bin-hadoop3/

# Copy sang Nole2
scp spark-4.0.1.tar.gz nole2@192.168.80.51:~/

# Trên Nole2
tar -xzf spark-4.0.1.tar.gz
```

### Bước 7: Cấu hình Spark trên Nole2
```bash
# Thêm vào ~/.bashrc
cat >> ~/.bashrc << 'EOF'
export SPARK_HOME=~/spark-4.0.1-bin-hadoop3
export PATH=$PATH:$SPARK_HOME/bin:$SPARK_HOME/sbin
EOF

source ~/.bashrc
```

### Bước 8: Cài đặt Java (nếu chưa có)
```bash
sudo apt-get install -y openjdk-11-jdk
java -version
```

### Bước 9: Start Spark Worker
```bash
$SPARK_HOME/sbin/start-worker.sh spark://nole1:7077

# Kiểm tra
jps | grep Worker
```

**Verify:** Refresh http://192.168.80.165:8080 - phải thấy 2 workers (nole1 + nole2)

### Bước 10: Tạo thư mục project
```bash
mkdir -p ~/Documents/bigdata
```

### Bước 11: Cài đặt Python dependencies
```bash
pip3 install --user pyspark==4.0.1 celery pika kafka-python pandas scikit-learn
```

### Bước 12: Copy project code (từ máy development)
```bash
# Chạy từ máy development
scp -r ~/Tuan/Project/BigData/final_project nole2@192.168.80.51:~/Documents/bigdata/
```

### Bước 13: Install project dependencies (trên Nole2)
```bash
cd ~/Documents/bigdata/final_project
pip3 install --user -r requirements.txt
```

### Bước 14: Start Celery Worker
```bash
cd ~/Documents/bigdata/final_project
celery -A mycelery.system_worker worker \
  --loglevel=info \
  --queues=kafka_queue \
  --hostname=kafka_worker@nole2 \
  --broker=pyamqp://guest@192.168.80.178//
```

**Để chạy background:**
```bash
nohup celery -A mycelery.system_worker worker \
  --loglevel=info \
  --queues=kafka_queue \
  --hostname=kafka_worker@nole2 \
  --broker=pyamqp://guest@192.168.80.178// \
  > celery_nole2.log 2>&1 &
```

---

## NOLE3 - Upload Data & Start Airflow

### Bước 1: Upload data to HDFS

Từ máy development:
```bash
cd ~/Tuan/Project/BigData/final_project

# Prepare data
python3 data/prepare_data.py

# Copy to Nole3
scp data/train_data.csv data/streaming_data.csv nole3@192.168.80.178:~/Tuan/Project/BigData/final_project/data/
```

Trên Nole3:
```bash
ssh nole3@192.168.80.178
cd ~/Tuan/Project/BigData/final_project

# Upload to HDFS
export HDFS_NAMENODE=hdfs://nole3:8020
python3 data/upload_to_hdfs.py

# Verify
~/hadoop/bin/hdfs dfs -ls /bigdata/house_prices
```

### Bước 2: Start Celery Worker (Nole3)
```bash
cd ~/Tuan/Project/BigData/final_project

# Foreground (để test)
celery -A mycelery.system_worker worker \
  --loglevel=info \
  --queues=hadoop_queue \
  --hostname=hadoop_worker@nole3 \
  --broker=pyamqp://guest@localhost//

# Background
nohup celery -A mycelery.system_worker worker \
  --loglevel=info \
  --queues=hadoop_queue \
  --hostname=hadoop_worker@nole3 \
  --broker=pyamqp://guest@localhost// \
  > celery_nole3.log 2>&1 &
```

### Bước 3: Start Airflow

#### Terminal 1: Webserver
```bash
cd ~/Tuan/Project/BigData/final_project
export AIRFLOW_HOME=~/Tuan/Project/BigData/final_project
airflow webserver --port 8080
```

#### Terminal 2: Scheduler
```bash
cd ~/Tuan/Project/BigData/final_project
export AIRFLOW_HOME=~/Tuan/Project/BigData/final_project
airflow scheduler
```

**Access:** http://192.168.80.178:8080 (admin/admin)

---

## Verification Checklist

### ✅ Spark Cluster
- [ ] Spark Master Web UI: http://192.168.80.165:8080
- [ ] 2 workers hiển thị (nole1 + nole2)
- [ ] Cả 2 workers đều ở trạng thái ALIVE

### ✅ Kafka
```bash
# Trên Nole2
docker ps
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list
```

### ✅ HDFS
```bash
# Trên Nole3
~/hadoop/bin/hdfs dfsadmin -report
~/hadoop/bin/hdfs dfs -ls /bigdata/house_prices
```

### ✅ RabbitMQ
- [ ] Web UI: http://192.168.80.178:15672 (guest/guest)
- [ ] 3 queues visible: `hadoop_queue`, `kafka_queue`, `spark_master`
- [ ] 3 consumers connected (1 per queue)

### ✅ Airflow
- [ ] Web UI: http://192.168.80.178:8080
- [ ] 2 DAGs visible: `train_model_pipeline_fixed`, `predict_streaming_pipeline`
- [ ] Login works: admin/admin

---

## Chạy Pipeline

### 1. Training Pipeline
1. Mở Airflow UI: http://192.168.80.178:8080
2. Tìm DAG: `train_model_pipeline_fixed`
3. Enable DAG (toggle switch)
4. Click "Trigger DAG" (▶️)
5. Theo dõi trong Graph view

### 2. Prediction Pipeline
1. Đợi training hoàn thành
2. Tìm DAG: `predict_streaming_pipeline`
3. Enable DAG
4. Click "Trigger DAG"

### 3. View Results
```bash
# Trên bất kỳ máy nào
cd ~/Documents/bigdata/final_project  # hoặc ~/Tuan/Project/BigData/final_project
export KAFKA_BOOTSTRAP_SERVERS=192.168.80.51:9092
python3 visualization/kafka_consumer.py
```

---

## Troubleshooting

### Spark Worker không kết nối được Master
```bash
# Kiểm tra /etc/hosts
cat /etc/hosts | grep nole

# Kiểm tra network
ping nole1

# Restart worker
$SPARK_HOME/sbin/stop-worker.sh
$SPARK_HOME/sbin/start-worker.sh spark://nole1:7077
```

### Celery không kết nối RabbitMQ
```bash
# Kiểm tra RabbitMQ
telnet 192.168.80.178 5672

# Kiểm tra firewall
sudo ufw status
```

### HDFS safe mode
```bash
~/hadoop/bin/hdfs dfsadmin -safemode leave
```

---

## Lưu ý quan trọng

1. **Spark version phải match:** Đảm bảo pyspark==4.0.1 trên tất cả máy
2. **Hostname resolution:** Tất cả máy phải resolve được nole1, nole2, nole3
3. **RabbitMQ:** Phải chạy trên Nole3 và accessible từ Nole1, Nole2
4. **HDFS:** Phải start trước khi upload data
5. **Celery workers:** Phải start trước khi trigger DAGs
