# Hướng Dẫn Setup Hệ Thống Phân Tán - Kiến Trúc 3 Máy

## Kiến Trúc

- **Nole1 (192.168.80.165)**: Spark Master + Worker
- **Nole2 (192.168.80.51)**: Kafka + Spark Worker
- **Nole3 (192.168.80.178)**: Airflow + Hadoop HDFS + RabbitMQ (máy chính)

## Celery Queues

- `spark_master` → Nole1
- `kafka_queue` → Nole2
- `hadoop_queue` → Nole3

---

## Setup Nole3 (Đã hoàn thành ✅)

Nole3 đã được setup với:
- ✅ RabbitMQ (port 5672, 15672)
- ✅ Hadoop HDFS (hdfs://nole3:8020)
- ✅ Airflow
- ✅ /etc/hosts configured
- ✅ Project code deployed

**Start Celery Worker:**
```bash
cd ~/Tuan/Project/BigData/final_project
celery -A mycelery.system_worker worker \
  --loglevel=info \
  --queues=hadoop_queue \
  --hostname=hadoop_worker@nole3 \
  --broker=pyamqp://guest@localhost//
```

---

## Setup Nole1 (Spark Master + Worker)

### 1. SSH và cấu hình /etc/hosts
```bash
ssh nole1@192.168.80.165

sudo nano /etc/hosts
# Thêm:
192.168.80.165  nole1
192.168.80.51   nole2
192.168.80.178  nole3
```

### 2. Test connectivity
```bash
ping nole3
telnet nole3 5672
```

### 3. Cài Java
```bash
sudo apt-get update
sudo apt-get install -y openjdk-11-jdk
```

### 4. Setup Spark 4.0.1
```bash
# Tìm Spark hiện có
find ~ -name "spark-4.0.1*" -type d

# Nếu chưa có:
cd ~
wget https://archive.apache.org/dist/spark/spark-4.0.1/spark-4.0.1-bin-hadoop3.tgz
tar -xzf spark-4.0.1-bin-hadoop3.tgz

# Add to ~/.bashrc
cat >> ~/.bashrc << 'EOF'
export SPARK_HOME=~/spark-4.0.1-bin-hadoop3
export PATH=$PATH:$SPARK_HOME/bin:$SPARK_HOME/sbin
EOF

source ~/.bashrc
```

### 5. Cấu hình Spark
```bash
cat > $SPARK_HOME/conf/spark-env.sh << 'EOF'
export SPARK_MASTER_HOST=nole1
export SPARK_MASTER_PORT=7077
export SPARK_MASTER_WEBUI_PORT=8080
export SPARK_WORKER_CORES=4
export SPARK_WORKER_MEMORY=4g
EOF

chmod +x $SPARK_HOME/conf/spark-env.sh

cat > $SPARK_HOME/conf/workers << 'EOF'
nole1
nole2
EOF
```

### 6. Start Spark
```bash
$SPARK_HOME/sbin/start-master.sh
$SPARK_HOME/sbin/start-worker.sh spark://nole1:7077
```

Verify: http://192.168.80.165:8080

### 7. Copy project code
```bash
# Từ Nole3:
scp -r ~/Tuan/Project/BigData/final_project nole1@192.168.80.165:~/Documents/bigdata/
```

### 8. Install dependencies
```bash
cd ~/Documents/bigdata/final_project
pip3 install --user pyspark==4.0.1 celery pika pandas scikit-learn kafka-python
pip3 install --user -r requirements.txt
```

### 9. Start Celery Worker
```bash
cd ~/Documents/bigdata/final_project
celery -A mycelery.system_worker worker \
  --loglevel=info \
  --queues=spark_master \
  --hostname=spark_worker@nole1 \
  --broker=pyamqp://guest@192.168.80.178//
```

---

## Setup Nole2 (Kafka + Spark Worker)

### 1. SSH và cấu hình /etc/hosts
```bash
ssh nole2@192.168.80.51

sudo nano /etc/hosts
# Thêm:
192.168.80.165  nole1
192.168.80.51   nole2
192.168.80.178  nole3
```

### 2. Test connectivity
```bash
ping nole1
ping nole3
telnet nole3 5672
telnet nole1 7077
```

### 3. Cài Docker
```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose
sudo usermod -aG docker $USER

# Logout và login lại
exit
ssh nole2@192.168.80.51
```

### 4. Setup Kafka
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

cd ~/kafka-cluster
docker-compose up -d

# Verify
docker ps
```

### 5. Cài Java và Spark
```bash
sudo apt-get install -y openjdk-11-jdk

# Copy từ Nole1
# Trên Nole1:
cd ~
tar -czf spark-4.0.1.tar.gz spark-4.0.1-bin-hadoop3/
scp spark-4.0.1.tar.gz nole2@192.168.80.51:~/

# Trên Nole2:
tar -xzf spark-4.0.1.tar.gz

cat >> ~/.bashrc << 'EOF'
export SPARK_HOME=~/spark-4.0.1-bin-hadoop3
export PATH=$PATH:$SPARK_HOME/bin:$SPARK_HOME/sbin
EOF

source ~/.bashrc
```

### 6. Start Spark Worker
```bash
$SPARK_HOME/sbin/start-worker.sh spark://nole1:7077
```

Verify: http://192.168.80.165:8080 (phải thấy 2 workers)

### 7. Copy project code
```bash
# Từ Nole3:
scp -r ~/Tuan/Project/BigData/final_project nole2@192.168.80.51:~/Documents/bigdata/
```

### 8. Install dependencies
```bash
cd ~/Documents/bigdata/final_project
pip3 install --user pyspark==4.0.1 celery pika kafka-python pandas scikit-learn
pip3 install --user -r requirements.txt
```

### 9. Start Celery Worker
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

### RabbitMQ (Nole3)
- Web UI: http://192.168.80.178:15672 (guest/guest)
- Phải thấy 3 queues và 3 consumers

### Spark (Nole1)
- Web UI: http://192.168.80.165:8080
- Phải thấy 2 workers (nole1 + nole2)

### Kafka (Nole2)
```bash
docker ps  # Phải thấy kafka và zookeeper
```

### HDFS (Nole3)
```bash
~/hadoop/bin/hdfs dfsadmin -report
```

---

## Start Airflow (Nole3)

```bash
# Terminal 1: Webserver
cd ~/Tuan/Project/BigData/final_project
airflow webserver --port 8080

# Terminal 2: Scheduler
airflow scheduler
```

Access: http://192.168.80.178:8080 (admin/admin)

---

## Troubleshooting

### Celery không kết nối RabbitMQ
```bash
# Test từ Nole1/Nole2
telnet 192.168.80.178 5672

# Check firewall trên Nole3
sudo ufw status
sudo ufw allow 5672/tcp
```

### Spark Worker không kết nối Master
```bash
# Check /etc/hosts
cat /etc/hosts | grep nole

# Test connectivity
ping nole1
telnet nole1 7077
```

Xem thêm: `MANUAL_SETUP_NOLE1_NOLE2.md` và `SETUP_WITH_SPARK_4.0.1.md`
