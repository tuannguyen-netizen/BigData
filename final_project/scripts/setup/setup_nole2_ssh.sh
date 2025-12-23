#!/bin/bash
# Script tự động setup Nole2 (Kafka + Spark Worker) qua SSH
# Chạy từ Nole3

set -e

NOLE2_USER="nole2"
NOLE2_HOST="192.168.80.51"

echo "=========================================="
echo "SETUP NOLE2 - Kafka + Spark Worker"
echo "=========================================="

# Tạo script để chạy trên Nole2
cat > /tmp/setup_nole2_remote.sh << 'EOFREMOTE'
#!/bin/bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}[1/9] Cài đặt Docker...${NC}"
if ! command -v docker &> /dev/null; then
    sudo apt-get update
    sudo apt-get install -y docker.io docker-compose
    sudo usermod -aG docker $USER
    echo -e "${GREEN}✓ Docker đã cài đặt (cần logout/login để áp dụng)${NC}"
else
    echo -e "${GREEN}✓ Docker đã tồn tại${NC}"
fi

echo -e "${YELLOW}[2/9] Cấu hình /etc/hosts...${NC}"
if ! grep -q "nole1" /etc/hosts; then
    sudo bash -c 'cat >> /etc/hosts << EOF
192.168.80.165  nole1
192.168.80.51   nole2
192.168.80.178  nole3
EOF'
    echo -e "${GREEN}✓ Hostname mapping đã thêm${NC}"
else
    echo -e "${GREEN}✓ Hostname mapping đã tồn tại${NC}"
fi

echo -e "${YELLOW}[3/9] Setup Kafka...${NC}"
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

echo -e "${GREEN}✓ Kafka config đã tạo${NC}"

echo -e "${YELLOW}[4/9] Start Kafka...${NC}"
cd ~/kafka-cluster
docker-compose down 2>/dev/null || true
docker-compose up -d
sleep 10
echo -e "${GREEN}✓ Kafka đã start${NC}"

echo -e "${YELLOW}[5/9] Cài đặt Java...${NC}"
sudo apt-get install -y openjdk-11-jdk
echo -e "${GREEN}✓ Java đã cài đặt${NC}"

echo -e "${YELLOW}[6/9] Download Spark...${NC}"
if [ ! -d ~/spark-4.0.0-bin-hadoop3 ]; then
    cd ~
    if [ ! -f spark-4.0.0-bin-hadoop3.tgz ]; then
        wget https://archive.apache.org/dist/spark/spark-4.0.0/spark-4.0.0-bin-hadoop3.tgz
    fi
    tar -xzf spark-4.0.0-bin-hadoop3.tgz
    echo -e "${GREEN}✓ Spark đã download${NC}"
else
    echo -e "${GREEN}✓ Spark đã tồn tại${NC}"
fi

# Thêm vào ~/.bashrc
if ! grep -q "SPARK_HOME" ~/.bashrc; then
    cat >> ~/.bashrc << 'EOF'
export SPARK_HOME=~/spark-4.0.0-bin-hadoop3
export PATH=$PATH:$SPARK_HOME/bin:$SPARK_HOME/sbin
EOF
fi
source ~/.bashrc

echo -e "${YELLOW}[7/9] Tạo thư mục project...${NC}"
mkdir -p ~/Documents/bigdata
echo -e "${GREEN}✓ Thư mục đã tạo${NC}"

echo -e "${YELLOW}[8/9] Cài đặt Python dependencies...${NC}"
pip3 install --user celery pika kafka-python pandas scikit-learn pyspark==4.0.0
echo -e "${GREEN}✓ Dependencies đã cài đặt${NC}"

echo -e "${YELLOW}[9/9] Start Spark Worker...${NC}"
~/spark-4.0.0-bin-hadoop3/sbin/start-worker.sh spark://nole1:7077
sleep 3
echo -e "${GREEN}✓ Spark Worker đã start${NC}"

echo ""
echo "=========================================="
echo -e "${GREEN}SETUP NOLE2 HOÀN TẤT!${NC}"
echo "=========================================="
echo "Kafka: localhost:9092"
echo "Spark Worker: Connected to spark://nole1:7077"
echo ""
EOFREMOTE

# Copy script lên Nole2
echo "Copying setup script to Nole2..."
scp /tmp/setup_nole2_remote.sh ${NOLE2_USER}@${NOLE2_HOST}:/tmp/

# Chạy script trên Nole2
echo "Running setup on Nole2..."
ssh ${NOLE2_USER}@${NOLE2_HOST} "bash /tmp/setup_nole2_remote.sh"

# Copy project code
echo "Copying project code to Nole2..."
scp -r ~/Tuan/Project/BigData/final_project ${NOLE2_USER}@${NOLE2_HOST}:~/Documents/bigdata/

# Install project dependencies
echo "Installing project dependencies on Nole2..."
ssh ${NOLE2_USER}@${NOLE2_HOST} "cd ~/Documents/bigdata/final_project && pip3 install --user -r requirements.txt"

echo ""
echo "=========================================="
echo "NOLE2 SETUP COMPLETE!"
echo "=========================================="
echo ""
echo "Để start Celery worker trên Nole2:"
echo "  ssh ${NOLE2_USER}@${NOLE2_HOST}"
echo "  cd ~/Documents/bigdata/final_project"
echo "  celery -A mycelery.system_worker worker --loglevel=info --queues=kafka_queue --hostname=kafka_worker@nole2 --broker=pyamqp://guest@192.168.80.178//"
echo ""
