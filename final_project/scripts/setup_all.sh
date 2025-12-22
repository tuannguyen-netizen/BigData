#!/bin/bash
# Master script để setup toàn bộ hệ thống
# Chạy từ Nole3

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=========================================="
echo "AUTOMATED SETUP - BIG DATA CLUSTER"
echo "=========================================="
echo "Nole1 (192.168.80.165): Spark Master + Worker"
echo "Nole2 (192.168.80.51): Kafka + Spark Worker"
echo "Nole3 (192.168.80.178): Airflow + Hadoop + RabbitMQ"
echo "=========================================="
echo ""

# Kiểm tra SSH connectivity cho tất cả 3 máy
echo "Checking SSH connectivity..."
if ! ssh -o BatchMode=yes -o ConnectTimeout=5 nole1@192.168.80.165 exit 2>/dev/null; then
    echo "❌ Cannot connect to Nole1 via SSH"
    echo "Please setup SSH keys first:"
    echo "  ssh-copy-id nole1@192.168.80.165"
    exit 1
fi

if ! ssh -o BatchMode=yes -o ConnectTimeout=5 nole2@192.168.80.51 exit 2>/dev/null; then
    echo "❌ Cannot connect to Nole2 via SSH"
    echo "Please setup SSH keys first:"
    echo "  ssh-copy-id nole2@192.168.80.51"
    exit 1
fi

if ! ssh -o BatchMode=yes -o ConnectTimeout=5 nole3@192.168.80.178 exit 2>/dev/null; then
    echo "❌ Cannot connect to Nole3 via SSH"
    echo "Please setup SSH keys first:"
    echo "  ssh-copy-id nole3@192.168.80.178"
    exit 1
fi

echo "✓ SSH connectivity OK for all machines"
echo ""

# ==========================================
# STEP 1: Setup Nole3 (via SSH)
# ==========================================
echo "=========================================="
echo "STEP 1/3: Setting up Nole3 (via SSH)..."
echo "=========================================="
bash "$SCRIPT_DIR/setup_nole3_ssh.sh"
echo ""

# ==========================================
# STEP 2: Setup Nole1 (via SSH)
# ==========================================
echo "=========================================="
echo "STEP 2/3: Setting up Nole1 (via SSH)..."
echo "=========================================="
bash "$SCRIPT_DIR/setup_nole1_ssh.sh"
echo ""

# ==========================================
# STEP 3: Setup Nole2 (via SSH)
# ==========================================
echo "=========================================="
echo "STEP 3/3: Setting up Nole2 (via SSH)..."
echo "=========================================="
bash "$SCRIPT_DIR/setup_nole2_ssh.sh"
echo ""

# ==========================================
# STEP 4: Upload data to HDFS (on Nole3)
# ==========================================
echo "=========================================="
echo "STEP 4/4: Uploading data to HDFS..."
echo "=========================================="

# Prepare data locally first
echo "Preparing data locally..."
cd "$PROJECT_DIR"
python3 data/prepare_data.py

# Copy data files to Nole3
echo "Copying data files to Nole3..."
scp data/train_data.csv data/streaming_data.csv nole3@192.168.80.178:~/Tuan/Project/BigData/final_project/data/

# Upload to HDFS on Nole3
echo "Uploading to HDFS on Nole3..."
ssh nole3@192.168.80.178 << 'EOFSSH'
export HDFS_NAMENODE=hdfs://nole3:8020
cd ~/Tuan/Project/BigData/final_project
python3 data/upload_to_hdfs.py
EOFSSH

echo ""
echo "=========================================="
echo "✓ SETUP COMPLETE!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Start Celery workers on all machines:"
echo ""
echo "   Nole3 (Hadoop queue):"
echo "   cd ~/Tuan/Project/BigData/final_project"
echo "   celery -A mycelery.system_worker worker --loglevel=info --queues=hadoop_queue --hostname=hadoop_worker@nole3 --broker=pyamqp://guest@localhost//"
echo ""
echo "   Nole1 (Spark queue):"
echo "   ssh nole1@192.168.80.165"
echo "   cd ~/Documents/bigdata/final_project"
echo "   celery -A mycelery.system_worker worker --loglevel=info --queues=spark_master --hostname=spark_worker@nole1 --broker=pyamqp://guest@192.168.80.178//"
echo ""
echo "   Nole2 (Kafka queue):"
echo "   ssh nole2@192.168.80.51"
echo "   cd ~/Documents/bigdata/final_project"
echo "   celery -A mycelery.system_worker worker --loglevel=info --queues=kafka_queue --hostname=kafka_worker@nole2 --broker=pyamqp://guest@192.168.80.178//"
echo ""
echo "2. Start Airflow on Nole3:"
echo "   Terminal 1: airflow webserver --port 8080"
echo "   Terminal 2: airflow scheduler"
echo ""
echo "3. Access Web UIs:"
echo "   - Airflow: http://192.168.80.178:8080 (admin/admin)"
echo "   - Spark Master: http://192.168.80.165:8080"
echo "   - HDFS: http://192.168.80.178:9870"
echo "   - RabbitMQ: http://192.168.80.178:15672 (guest/guest)"
echo ""
echo "4. Run pipelines from Airflow UI"
echo ""
