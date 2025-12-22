#!/bin/bash
# Deploy spark_jobs to all Nole machines

set -e

PROJECT_DIR="$HOME/Tuan/Project/BigData/final_project"
SPARK_JOBS_DIR="$PROJECT_DIR/spark_jobs"

echo "=========================================="
echo "DEPLOYING SPARK JOBS TO NOLE MACHINES"
echo "=========================================="
echo ""

# Check if spark_jobs directory exists
if [ ! -d "$SPARK_JOBS_DIR" ]; then
    echo "❌ Error: $SPARK_JOBS_DIR not found"
    exit 1
fi

echo "📦 Files to deploy:"
ls -lh "$SPARK_JOBS_DIR"/*.py
echo ""

# ========================================
# NOLE1 (192.168.80.165) - Spark Master
# ========================================
echo "=========================================="
echo "Deploying to NOLE1 (Spark Master)"
echo "=========================================="

# Create directory on Nole1
ssh nole1@192.168.80.165 "mkdir -p ~/Tuan/Project/BigData/final_project/spark_jobs"

# Copy spark_jobs
scp -r "$SPARK_JOBS_DIR"/*.py nole1@192.168.80.165:~/Tuan/Project/BigData/final_project/spark_jobs/

# Verify
echo "✓ Verifying on Nole1:"
ssh nole1@192.168.80.165 "ls -lh ~/Tuan/Project/BigData/final_project/spark_jobs/"
echo ""

# ========================================
# NOLE2 (192.168.80.51) - Kafka + Spark Worker
# ========================================
echo "=========================================="
echo "Deploying to NOLE2 (Kafka + Spark Worker)"
echo "=========================================="

# Create directory on Nole2
ssh nole2@192.168.80.51 "mkdir -p ~/Tuan/Project/BigData/final_project/spark_jobs"

# Copy spark_jobs
scp -r "$SPARK_JOBS_DIR"/*.py nole2@192.168.80.51:~/Tuan/Project/BigData/final_project/spark_jobs/

# Verify
echo "✓ Verifying on Nole2:"
ssh nole2@192.168.80.51 "ls -lh ~/Tuan/Project/BigData/final_project/spark_jobs/"
echo ""

# ========================================
# NOLE3 (192.168.80.178) - Airflow + Hadoop
# ========================================
echo "=========================================="
echo "Deploying to NOLE3 (Airflow + Hadoop)"
echo "=========================================="

# Create directory on Nole3 (if not exists)
ssh nole3@192.168.80.178 "mkdir -p ~/Tuan/Project/BigData/final_project/spark_jobs"

# Copy spark_jobs
scp -r "$SPARK_JOBS_DIR"/*.py nole3@192.168.80.178:~/Tuan/Project/BigData/final_project/spark_jobs/

# Verify
echo "✓ Verifying on Nole3:"
ssh nole3@192.168.80.178 "ls -lh ~/Tuan/Project/BigData/final_project/spark_jobs/"
echo ""

echo "=========================================="
echo "✅ DEPLOYMENT COMPLETED"
echo "=========================================="
echo ""
echo "Spark jobs deployed to:"
echo "  - Nole1: ~/Tuan/Project/BigData/final_project/spark_jobs/"
echo "  - Nole2: ~/Tuan/Project/BigData/final_project/spark_jobs/"
echo "  - Nole3: ~/Tuan/Project/BigData/final_project/spark_jobs/"
echo ""
