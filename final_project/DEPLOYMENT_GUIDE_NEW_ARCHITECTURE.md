# DEPLOYMENT GUIDE - NEW ARCHITECTURE

## Architecture Overview

### Machine Configuration

| Machine | IP | Hostname | Services | Celery Queue |
|---------|-----|----------|----------|--------------|
| **Nole1** | 192.168.80.165 | nole1 | Spark Master + Worker | `spark_master` |
| **Nole2** | 192.168.80.51 | nole2 | Kafka + Spark Worker | `kafka_queue` |
| **Nole3** | 192.168.80.178 | nole3 | Airflow + Hadoop HDFS + RabbitMQ | `hadoop_queue` |

### Network Ports

| Service | Port | Machine | Access |
|---------|------|---------|--------|
| Spark Master | 7077 | Nole1 | RPC |
| Spark Master Web UI | 8080 | Nole1 | HTTP |
| Spark Worker | 8081+ | Nole1, Nole2 | HTTP |
| Kafka Broker | 9092 | Nole2 | TCP |
| HDFS Namenode | 8020 | Nole3 | RPC |
| HDFS Web UI | 9870 | Nole3 | HTTP |
| Airflow Web UI | 8080 | Nole3 | HTTP |
| RabbitMQ | 5672 | Nole3 | AMQP |
| RabbitMQ Management | 15672 | Nole3 | HTTP |

---

## Prerequisites

### All Machines

1. **Java 8 or 11** (for Spark and Hadoop)
```bash
java -version
```

2. **Python 3.9+**
```bash
python3 --version
```

3. **Network connectivity** between all machines
```bash
# Test from each machine
ping nole1
ping nole2
ping nole3
```

4. **Hostname resolution** (add to `/etc/hosts` on all machines)
```bash
# Add these lines to /etc/hosts
192.168.80.165  nole1
192.168.80.51   nole2
192.168.80.178  nole3
```

---

## Installation Steps

### Nole1 (Spark Master + Worker)

#### 1. Install Spark 4.0.0

```bash
cd ~
wget https://archive.apache.org/dist/spark/spark-4.0.0/spark-4.0.0-bin-hadoop3.tgz
tar -xzf spark-4.0.0-bin-hadoop3.tgz
```

#### 2. Configure Spark

Edit `~/spark-4.0.0-bin-hadoop3/conf/spark-env.sh`:
```bash
export SPARK_MASTER_HOST=nole1
export SPARK_MASTER_PORT=7077
export SPARK_MASTER_WEBUI_PORT=8080
export SPARK_WORKER_CORES=4
export SPARK_WORKER_MEMORY=4g
```

Edit `~/spark-4.0.0-bin-hadoop3/conf/workers`:
```
nole1
nole2
```

#### 3. Install Python Dependencies

```bash
pip3 install --user pyspark==4.0.0 celery pika
```

#### 4. Install Celery Worker

```bash
cd ~/Documents/bigdata/final_project
pip3 install --user -r requirements.txt
```

#### 5. Start Services

```bash
# Start Spark Master
~/spark-4.0.0-bin-hadoop3/sbin/start-master.sh

# Start Spark Worker (local)
~/spark-4.0.0-bin-hadoop3/sbin/start-worker.sh spark://nole1:7077
```

#### 6. Start Celery Worker

```bash
cd ~/Documents/bigdata/final_project
celery -A mycelery.system_worker worker \
  --loglevel=info \
  --queues=spark_master \
  --hostname=spark_worker@nole1 \
  --broker=pyamqp://guest@192.168.80.178//
```

---

### Nole2 (Kafka + Spark Worker)

#### 1. Install Docker and Docker Compose

```bash
# Install Docker
sudo apt-get update
sudo apt-get install -y docker.io docker-compose

# Add user to docker group
sudo usermod -aG docker $USER
# Logout and login again
```

#### 2. Setup Kafka

Create `~/kafka-cluster/docker-compose.yml`:
```yaml
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
```

#### 3. Start Kafka

```bash
cd ~/kafka-cluster
docker-compose up -d
```

#### 4. Install Spark Worker

```bash
cd ~
wget https://archive.apache.org/dist/spark/spark-4.0.0/spark-4.0.0-bin-hadoop3.tgz
tar -xzf spark-4.0.0-bin-hadoop3.tgz
```

#### 5. Start Spark Worker

```bash
~/spark-4.0.0-bin-hadoop3/sbin/start-worker.sh spark://nole1:7077
```

#### 6. Install Python Dependencies

```bash
pip3 install --user celery pika kafka-python
```

#### 7. Start Celery Worker

```bash
cd ~/Documents/bigdata/final_project
celery -A mycelery.system_worker worker \
  --loglevel=info \
  --queues=kafka_queue \
  --hostname=kafka_worker@nole2 \
  --broker=pyamqp://guest@192.168.80.178//
```

---

### Nole3 (Airflow + Hadoop + RabbitMQ)

#### 1. Install RabbitMQ

```bash
sudo apt-get update
sudo apt-get install -y rabbitmq-server

# Start RabbitMQ
sudo systemctl start rabbitmq-server
sudo systemctl enable rabbitmq-server

# Enable management plugin
sudo rabbitmq-plugins enable rabbitmq_management

# Verify
telnet localhost 5672
```

#### 2. Install Hadoop

```bash
cd ~
wget https://downloads.apache.org/hadoop/common/hadoop-3.3.6/hadoop-3.3.6.tar.gz
tar -xzf hadoop-3.3.6.tar.gz
ln -s hadoop-3.3.6 hadoop
```

Configure Hadoop (edit `~/hadoop/etc/hadoop/core-site.xml`):
```xml
<configuration>
    <property>
        <name>fs.defaultFS</name>
        <value>hdfs://nole3:8020</value>
    </property>
</configuration>
```

Configure HDFS (edit `~/hadoop/etc/hadoop/hdfs-site.xml`):
```xml
<configuration>
    <property>
        <name>dfs.replication</name>
        <value>1</value>
    </property>
    <property>
        <name>dfs.namenode.name.dir</name>
        <value>file:///home/nole3/hadoop_data/namenode</value>
    </property>
    <property>
        <name>dfs.datanode.data.dir</name>
        <value>file:///home/nole3/hadoop_data/datanode</value>
    </property>
</configuration>
```

Format namenode (first time only):
```bash
~/hadoop/bin/hdfs namenode -format
```

#### 3. Install Airflow

```bash
pip3 install --user apache-airflow==3.1.3
pip3 install --user apache-airflow-providers-celery

# Initialize database
airflow db init

# Create admin user
airflow users create \
  --username admin \
  --firstname Admin \
  --lastname User \
  --role Admin \
  --email admin@example.com \
  --password admin
```

#### 4. Install Project Dependencies

```bash
cd ~/Documents/bigdata/final_project
pip3 install --user -r requirements.txt
```

#### 5. Configure Airflow

Set environment variables (add to `~/.bashrc`):
```bash
export AIRFLOW_HOME=~/Documents/bigdata/final_project
export AIRFLOW__CORE__DAGS_FOLDER=~/Documents/bigdata/final_project/dags
export AIRFLOW__CORE__LOAD_EXAMPLES=False
export PYTHONPATH=~/Documents/bigdata/final_project:$PYTHONPATH
```

#### 6. Start Celery Worker (for Hadoop tasks)

```bash
cd ~/Documents/bigdata/final_project
celery -A mycelery.system_worker worker \
  --loglevel=info \
  --queues=hadoop_queue \
  --hostname=hadoop_worker@nole3 \
  --broker=pyamqp://guest@localhost//
```

#### 7. Start Airflow

```bash
# Terminal 1: Webserver
airflow webserver --port 8080

# Terminal 2: Scheduler
airflow scheduler
```

---

## Verification

### 1. Check RabbitMQ (on Nole3)

```bash
# Check service
sudo systemctl status rabbitmq-server

# Check port
telnet localhost 5672

# Web UI
# Open browser: http://192.168.80.178:15672
# Login: guest/guest
```

### 2. Check Hadoop (on Nole3)

```bash
# Start HDFS
~/hadoop/sbin/start-dfs.sh

# Check status
~/hadoop/bin/hdfs dfsadmin -report

# Web UI
# Open browser: http://192.168.80.178:9870
```

### 3. Check Spark (on Nole1)

```bash
# Check master
jps | grep Master

# Web UI
# Open browser: http://192.168.80.165:8080
# Should see 2 workers (nole1 and nole2)
```

### 4. Check Kafka (on Nole2)

```bash
# Check containers
docker ps

# List topics
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list

# Create test topic
docker exec kafka kafka-topics --bootstrap-server localhost:9092 \
  --create --topic test --replication-factor 1 --partitions 1
```

### 5. Check Celery Workers

On Nole3, check RabbitMQ management UI:
- http://192.168.80.178:15672
- Go to "Queues" tab
- Should see: `spark_master`, `kafka_queue`, `hadoop_queue`

### 6. Check Airflow (on Nole3)

```bash
# Web UI
# Open browser: http://192.168.80.178:8080
# Login: admin/admin

# Check DAGs
airflow dags list | grep -E 'train_model|predict_streaming'
```

---

## Running the Pipeline

### 1. Upload Data to HDFS

```bash
cd ~/Documents/bigdata/final_project

# Prepare data
python3 data/prepare_data.py

# Upload to HDFS
export HDFS_NAMENODE=hdfs://nole3:8020
python3 data/upload_to_hdfs.py
```

### 2. Run Training Pipeline

Via Airflow UI:
1. Go to http://192.168.80.178:8080
2. Find DAG: `train_model_pipeline_fixed`
3. Enable the DAG
4. Click "Trigger DAG"

### 3. Run Prediction Pipeline

Via Airflow UI:
1. Find DAG: `predict_streaming_pipeline`
2. Enable the DAG
3. Click "Trigger DAG"

### 4. View Results

```bash
# On any machine with Python
cd ~/Documents/bigdata/final_project
export KAFKA_BOOTSTRAP_SERVERS=192.168.80.51:9092
python3 visualization/kafka_consumer.py
```

---

## Troubleshooting

### Celery Workers Not Connecting

```bash
# Check RabbitMQ is running on Nole3
sudo systemctl status rabbitmq-server

# Check network connectivity
ping 192.168.80.178
telnet 192.168.80.178 5672

# Restart worker with verbose logging
celery -A mycelery.system_worker worker --loglevel=debug
```

### HDFS Connection Issues

```bash
# Check HDFS is running
~/hadoop/bin/hdfs dfsadmin -report

# Check safe mode
~/hadoop/bin/hdfs dfsadmin -safemode get

# Leave safe mode if needed
~/hadoop/bin/hdfs dfsadmin -safemode leave
```

### Spark Job Failures

```bash
# Check Spark Master logs
tail -f ~/spark-4.0.0-bin-hadoop3/logs/spark-*-master-*.out

# Check worker logs
tail -f ~/spark-4.0.0-bin-hadoop3/logs/spark-*-worker-*.out
```

### Kafka Connection Issues

```bash
# Check Kafka is running
docker ps | grep kafka

# Check logs
docker logs kafka

# Restart Kafka
cd ~/kafka-cluster
docker-compose restart
```

---

## Maintenance

### Stop All Services

**Nole1:**
```bash
~/spark-4.0.0-bin-hadoop3/sbin/stop-all.sh
```

**Nole2:**
```bash
~/spark-4.0.0-bin-hadoop3/sbin/stop-worker.sh
cd ~/kafka-cluster
docker-compose down
```

**Nole3:**
```bash
~/hadoop/sbin/stop-dfs.sh
# Stop Airflow (Ctrl+C in terminals)
# Stop Celery worker (Ctrl+C)
```

### Start All Services

Follow the "Start Services" sections for each machine above.

---

## Notes

- All machines must have the project code at: `~/Documents/bigdata/final_project`
- Ensure `/etc/hosts` has hostname mappings on all machines
- RabbitMQ on Nole3 must be accessible from all machines
- HDFS on Nole3 must be accessible from Spark jobs
- Kafka on Nole2 must be accessible from all machines
