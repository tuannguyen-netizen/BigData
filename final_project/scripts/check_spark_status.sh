#!/bin/bash
# Script để kiểm tra Spark application status
# Usage: ./scripts/check_spark_status.sh

echo "=========================================="
echo "Kiểm tra Spark Application Status"
echo "=========================================="
echo ""

# Kiểm tra Spark Master
SPARK_MASTER="spark://worker3:7077"
echo "1. Kiểm tra Spark Master: $SPARK_MASTER"
if curl -s "http://worker3:8080" > /dev/null 2>&1; then
    echo "   ✓ Spark Master UI đang chạy: http://worker3:8080"
    echo "   💡 Truy cập để xem applications đang chạy"
else
    echo "   ❌ Không thể kết nối tới Spark Master UI"
fi
echo ""

# Kiểm tra Spark applications đang chạy
echo "2. Kiểm tra Spark Applications đang chạy:"
if command -v spark-submit >/dev/null 2>&1; then
    # Thử list applications (nếu có spark-submit)
    echo "   Đang kiểm tra..."
else
    echo "   ⚠️  spark-submit không có trong PATH"
    echo "   💡 Kiểm tra thủ công: http://worker3:8080"
fi
echo ""

# Kiểm tra HDFS data
echo "3. Kiểm tra dữ liệu trên HDFS:"
HDFS_NAMENODE="hdfs://worker1:8020"
HDFS_DATA_DIR="/bigdata/house_prices"
echo "   HDFS Namenode: $HDFS_NAMENODE"
echo "   Data Dir: $HDFS_DATA_DIR"
if command -v hdfs >/dev/null 2>&1; then
    echo "   Đang kiểm tra..."
    hdfs dfs -fs "$HDFS_NAMENODE" -ls "$HDFS_DATA_DIR" 2>&1 | head -10
else
    echo "   ⚠️  hdfs command không có trong PATH"
    echo "   💡 Kiểm tra thủ công trên máy Hadoop"
fi
echo ""

# Kiểm tra Celery worker
echo "4. Kiểm tra Celery worker trên máy Spark:"
echo "   💡 Trên máy Spark, chạy: ps aux | grep celery"
echo ""

echo "=========================================="
echo "Hướng dẫn Debug"
echo "=========================================="
echo ""
echo "1. Xem Spark UI:"
echo "   http://worker3:8080 - Spark Master UI"
echo "   http://worker3:4040 - Spark Application UI (nếu đang chạy)"
echo ""
echo "2. Xem logs của Spark job:"
echo "   - Trong Airflow UI: Xem log của task 'wait_train_model'"
echo "   - Trên máy Spark: Xem logs trong /tmp/spark-*"
echo ""
echo "3. Kiểm tra HDFS data:"
echo "   hdfs dfs -fs hdfs://worker1:8020 -ls /bigdata/house_prices"
echo ""
echo "4. Kiểm tra Celery worker:"
echo "   Trên máy Spark: ps aux | grep celery"
echo ""

