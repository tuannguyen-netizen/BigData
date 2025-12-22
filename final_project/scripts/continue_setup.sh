#!/bin/bash
# Quick setup script - chạy từ máy development

set -e

echo "=========================================="
echo "CONTINUING SETUP - Nole1 & Nole2"
echo "=========================================="
echo ""

# Setup Nole1
echo "=========================================="
echo "Setting up Nole1 (Spark Master + Worker)..."
echo "=========================================="
./scripts/setup_nole1_ssh.sh

echo ""
echo "=========================================="
echo "Setting up Nole2 (Kafka + Spark Worker)..."
echo "=========================================="
./scripts/setup_nole2_ssh.sh

echo ""
echo "=========================================="
echo "Uploading data to HDFS on Nole3..."
echo "=========================================="

# Prepare data locally
python3 data/prepare_data.py

# Copy to Nole3
scp data/train_data.csv data/streaming_data.csv nole3@192.168.80.178:~/Tuan/Project/BigData/final_project/data/

# Upload to HDFS
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
echo "1. Start Celery workers on all 3 machines"
echo "2. Start Airflow on Nole3"
echo "3. Run pipelines from Airflow UI"
echo ""
echo "See AUTOMATED_SETUP_GUIDE.md for details"
echo ""
