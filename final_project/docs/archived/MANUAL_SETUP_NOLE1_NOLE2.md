# HƯỚNG DẪN SETUP THỦ CÔNG - NOLE1 & NOLE2

## NOLE1 - Spark Master + Worker

### Bước 1: SSH vào Nole1
```bash
ssh nole1@192.168.80.165
```

### Bước 2: Cài đặt Java
```bash
sudo apt-get update
sudo apt-get install -y openjdk-11-jdk
java -version
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

### Bước 4: Tìm hoặc Download Spark 4.0.1

**Option A: Nếu đã có Spark 4.0.1**
```bash
# Tìm Spark hiện có
find ~ -name "spark-4.0.1*" -type d 2>/dev/null

# Hoặc kiểm tra biến môi trường
echo $SPARK_HOME
```

**Option B: Download Spark 4.0.1**
```bash
cd ~
wget https://archive.apache.org/dist/spark/spark-4.0.1/spark-4.0.1-bin-hadoop3.tgz
tar -xzf spark-4.0.1-bin-hadoop3.tgz
```

### Bước 5: Cấu hình Spark
```bash
# Thêm vào ~/.bashrc
cat >> ~/.bashrc << 'EOF'
export SPARK_HOME=~/spark-4.0.1-bin-hadoop3
export PATH=$PATH:$SPARK_HOME/bin:$SPARK_HOME/sbin
EOF

source ~/.bashrc

# Tạo spark-env.sh
cat > ~/spark-4.0.1-bin-hadoop3/conf/spark-env.sh << 'EOF'
export SPARK_MASTER_HOST=nole1
export SPARK_MASTER_PORT=7077
export SPARK_MASTER_WEBUI_PORT=8080
export SPARK_WORKER_CORES=4
export SPARK_WORKER_MEMORY=4g
EOF

chmod +x ~/spark-4.0.1-bin-hadoop3/conf/spark-env.sh

# Tạo workers file
cat > ~/spark-4.0.1-bin-hadoop3/conf/workers << 'EOF'
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
pip3 install --user pyspark==4.0.1 celery pika pandas scikit-learn kafka-python
```

### Bước 8: Start Spark Master
```bash
~/spark-4.0.1-bin-hadoop3/sbin/start-master.sh
# Hoặc nếu đã set SPARK_HOME:
$SPARK_HOME/sbin/start-master.sh
```

Verify: http://192.168.80.165:8080

### Bước 9: Start Spark Worker
```bash
~/spark-4.0.1-bin-hadoop3/sbin/start-worker.sh spark://nole1:7077
# Hoặc:
$SPARK_HOME/sbin/start-worker.sh spark://nole1:7077
```

### Bước 10: Copy project code (từ máy development)
```bash
# Chạy từ máy development
scp -r ~/Tuan/Project/BigData/final_project nole1@192.168.80.165:~/Documents/bigdata/
```

### Bước 11: Install project dependencies
```bash
# Trên Nole1
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

---

## NOLE2 - Kafka + Spark Worker

### Bước 1: SSH vào Nole2
```bash
ssh nole2@192.168.80.51
```

### Bước 2: Cài đặt Docker
```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose
sudo usermod -aG docker $USER

# Logout và login lại
exit
ssh nole2@192.168.80.51
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
```

### Bước 6: Cài đặt Java và Spark
```bash
sudo apt-get install -y openjdk-11-jdk

# Option A: Nếu đã có Spark 4.0.1
find ~ -name "spark-4.0.1*" -type d 2>/dev/null

# Option B: Copy từ Nole1
# Trên Nole1:
cd ~
tar -czf spark-4.0.1.tar.gz spark-4.0.1-bin-hadoop3/
scp spark-4.0.1.tar.gz nole2@192.168.80.51:~/

# Trên Nole2:
tar -xzf spark-4.0.1.tar.gz

# Option C: Download mới
cd ~
wget https://archive.apache.org/dist/spark/spark-4.0.1/spark-4.0.1-bin-hadoop3.tgz
tar -xzf spark-4.0.1-bin-hadoop3.tgz

# Thêm vào ~/.bashrc
cat >> ~/.bashrc << 'EOF'
export SPARK_HOME=~/spark-4.0.1-bin-hadoop3
export PATH=$PATH:$SPARK_HOME/bin:$SPARK_HOME/sbin
EOF

source ~/.bashrc
```

### Bước 7: Tạo thư mục project
```bash
mkdir -p ~/Documents/bigdata
```

### Bước 8: Start Spark Worker
```bash
~/spark-4.0.1-bin-hadoop3/sbin/start-worker.sh spark://nole1:7077
# Hoặc:
$SPARK_HOME/sbin/start-worker.sh spark://nole1:7077
```

### Bước 9: Cài đặt Python dependencies
```bash
pip3 install --user pyspark==4.0.1 celery pika kafka-python pandas scikit-learn
```

### Bước 10: Copy project code (từ máy development)
```bash
# Chạy từ máy development
scp -r ~/Tuan/Project/BigData/final_project nole2@192.168.80.51:~/Documents/bigdata/
```

### Bước 11: Install project dependencies
```bash
# Trên Nole2
cd ~/Documents/bigdata/final_project
pip3 install --user -r requirements.txt
```

### Bước 12: Start Celery Worker
```bash
cd ~/Documents/bigdata/final_project
celery -A mycelery.system_worker worker \
  --loglevel=info \
  --queues=kafka_queue \
  --hostname=kafka_worker@nole2 \
  --broker=pyamqp://guest@192.168.80.178//
```

---

## Verification

### Check Spark (từ browser)
- Spark Master: http://192.168.80.165:8080
- Phải thấy 2 workers: nole1 và nole2

### Check Kafka (trên Nole2)
```bash
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list
```

### Check RabbitMQ (từ browser)
- http://192.168.80.178:15672 (guest/guest)
- Phải thấy 3 queues: hadoop_queue, kafka_queue, spark_master

---

## Upload Data to HDFS

Từ máy development:
```bash
cd ~/Tuan/Project/BigData/final_project
python3 data/prepare_data.py
scp data/train_data.csv data/streaming_data.csv nole3@192.168.80.178:~/Tuan/Project/BigData/final_project/data/

ssh nole3@192.168.80.178
cd ~/Tuan/Project/BigData/final_project
export HDFS_NAMENODE=hdfs://nole3:8020
python3 data/upload_to_hdfs.py
```

---

## Start Airflow (trên Nole3)

```bash
ssh nole3@192.168.80.178

# Terminal 1: Celery Worker
cd ~/Tuan/Project/BigData/final_project
celery -A mycelery.system_worker worker \
  --loglevel=info \
  --queues=hadoop_queue \
  --hostname=hadoop_worker@nole3 \
  --broker=pyamqp://guest@localhost//

# Terminal 2: Airflow Webserver
cd ~/Tuan/Project/BigData/final_project
airflow webserver --port 8080

# Terminal 3: Airflow Scheduler
cd ~/Tuan/Project/BigData/final_project
airflow scheduler
```

Access: http://192.168.80.178:8080 (admin/admin)
