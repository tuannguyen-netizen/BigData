#!/bin/bash

# Script kiểm tra Spark Workers và dừng workers không cần thiết

echo "🔍 Kiểm tra Spark Workers đang chạy..."
echo ""

# Kiểm tra trên máy hiện tại
echo "📍 Máy hiện tại: $(hostname)"
echo "IP: $(hostname -I | awk '{print $1}')"
echo ""

# Kiểm tra Spark workers
echo "🔎 Tìm Spark Workers:"
ps aux | grep -i "spark.*worker" | grep -v grep || echo "  Không tìm thấy Spark worker trên máy này"
echo ""

# Kiểm tra Java processes
echo "☕ Java processes (có thể là Spark workers):"
jps 2>/dev/null | grep -i worker || echo "  Không tìm thấy worker process"
echo ""

# Kiểm tra Spark Master UI
echo "🌐 Kiểm tra Spark Master UI:"
SPARK_MASTER="worker3"
echo "  URL: http://${SPARK_MASTER}:8080"
echo ""

# Kiểm tra workers qua API (nếu có curl)
if command -v curl &> /dev/null; then
    echo "📊 Workers từ Spark Master API:"
    curl -s "http://${SPARK_MASTER}:8080/api/v1/applications" 2>/dev/null | python3 -m json.tool 2>/dev/null | head -20 || echo "  Không thể kết nối đến Spark Master"
    echo ""
fi

# Hướng dẫn dừng workers
echo "⚠️  Nếu có Spark worker trên máy Airflow (192.168.80.147):"
echo "  1. SSH vào máy Airflow:"
echo "     ssh user@192.168.80.147"
echo ""
echo "  2. Dừng Spark workers:"
echo "     pkill -f 'spark.*worker'"
echo "     # Hoặc"
echo "     jps | grep Worker | awk '{print \$1}' | xargs kill"
echo ""
echo "  3. Nếu dùng docker-compose:"
echo "     cd ~/docker-spark && docker-compose down"
echo ""

