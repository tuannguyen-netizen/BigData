#!/bin/bash
# Script tự động setup Nole1 (Spark Master + Worker) qua SSH
# Chạy từ Nole3

set -e

NOLE1_USER="nole1"
NOLE1_HOST="192.168.80.165"

echo "=========================================="
echo "SETUP NOLE1 - Spark Master + Worker"
echo "=========================================="

# Tạo script để chạy trên Nole1
cat > /tmp/setup_nole1_remote.sh << 'EOFREMOTE'
#!/bin/bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}[1/8] Cài đặt Java...${NC}"
sudo apt-get update
sudo apt-get install -y openjdk-11-jdk
echo -e "${GREEN}✓ Java đã cài đặt${NC}"

echo -e "${YELLOW}[2/8] Cấu hình /etc/hosts...${NC}"
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

echo -e "${YELLOW}[3/8] Download Spark...${NC}"
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

echo -e "${YELLOW}[4/8] Cấu hình Spark...${NC}"
# Thêm vào ~/.bashrc
if ! grep -q "SPARK_HOME" ~/.bashrc; then
    cat >> ~/.bashrc << 'EOF'
export SPARK_HOME=~/spark-4.0.0-bin-hadoop3
export PATH=$PATH:$SPARK_HOME/bin:$SPARK_HOME/sbin
EOF
fi
source ~/.bashrc

# Tạo spark-env.sh
cat > ~/spark-4.0.0-bin-hadoop3/conf/spark-env.sh << 'EOF'
export SPARK_MASTER_HOST=nole1
export SPARK_MASTER_PORT=7077
export SPARK_MASTER_WEBUI_PORT=8080
export SPARK_WORKER_CORES=4
export SPARK_WORKER_MEMORY=4g
EOF

# Tạo workers file
cat > ~/spark-4.0.0-bin-hadoop3/conf/workers << 'EOF'
nole1
nole2
EOF

chmod +x ~/spark-4.0.0-bin-hadoop3/conf/spark-env.sh
echo -e "${GREEN}✓ Spark đã cấu hình${NC}"

echo -e "${YELLOW}[5/8] Tạo thư mục project...${NC}"
mkdir -p ~/Documents/bigdata
echo -e "${GREEN}✓ Thư mục đã tạo${NC}"

echo -e "${YELLOW}[6/8] Cài đặt Python dependencies...${NC}"
pip3 install --user pyspark==4.0.0 celery pika pandas scikit-learn kafka-python
echo -e "${GREEN}✓ Dependencies đã cài đặt${NC}"

echo -e "${YELLOW}[7/8] Start Spark Master...${NC}"
~/spark-4.0.0-bin-hadoop3/sbin/start-master.sh
sleep 5
echo -e "${GREEN}✓ Spark Master đã start${NC}"

echo -e "${YELLOW}[8/8] Start Spark Worker...${NC}"
~/spark-4.0.0-bin-hadoop3/sbin/start-worker.sh spark://nole1:7077
sleep 3
echo -e "${GREEN}✓ Spark Worker đã start${NC}"

echo ""
echo "=========================================="
echo -e "${GREEN}SETUP NOLE1 HOÀN TẤT!${NC}"
echo "=========================================="
echo "Spark Master Web UI: http://192.168.80.165:8080"
echo ""
EOFREMOTE

# Copy script lên Nole1
echo "Copying setup script to Nole1..."
scp /tmp/setup_nole1_remote.sh ${NOLE1_USER}@${NOLE1_HOST}:/tmp/

# Chạy script trên Nole1
echo "Running setup on Nole1..."
ssh ${NOLE1_USER}@${NOLE1_HOST} "bash /tmp/setup_nole1_remote.sh"

# Copy project code
echo "Copying project code to Nole1..."
scp -r ~/Tuan/Project/BigData/final_project ${NOLE1_USER}@${NOLE1_HOST}:~/Documents/bigdata/

# Install project dependencies
echo "Installing project dependencies on Nole1..."
ssh ${NOLE1_USER}@${NOLE1_HOST} "cd ~/Documents/bigdata/final_project && pip3 install --user -r requirements.txt"

echo ""
echo "=========================================="
echo "NOLE1 SETUP COMPLETE!"
echo "=========================================="
echo ""
echo "Để start Celery worker trên Nole1:"
echo "  ssh ${NOLE1_USER}@${NOLE1_HOST}"
echo "  cd ~/Documents/bigdata/final_project"
echo "  celery -A mycelery.system_worker worker --loglevel=info --queues=spark_master --hostname=spark_worker@nole1 --broker=pyamqp://guest@192.168.80.178//"
echo ""
