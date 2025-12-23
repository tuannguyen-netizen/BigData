#!/bin/bash
# Script để kiểm tra kết nối HDFS và tìm port đúng
# Usage: ./scripts/check_hdfs_connection.sh

echo "=========================================="
echo "Kiểm tra kết nối HDFS"
echo "=========================================="
echo ""

HADOOP_HOST="worker1"
HDFS_DATA_DIR="/bigdata/house_prices"

# 1. Kiểm tra network connectivity
echo "1. Kiểm tra network connectivity tới $HADOOP_HOST:"
if ping -c 2 $HADOOP_HOST >/dev/null 2>&1; then
    echo "   ✓ Ping thành công"
else
    echo "   ❌ Không ping được $HADOOP_HOST"
    echo "   💡 Kiểm tra /etc/hosts hoặc DNS"
fi
echo ""

# 2. Kiểm tra các ports HDFS thông thường
echo "2. Kiểm tra các ports HDFS:"
PORTS=(8020 9000 9870 50070)
for port in "${PORTS[@]}"; do
    echo -n "   Port $port: "
    if timeout 2 bash -c "echo > /dev/tcp/$HADOOP_HOST/$port" 2>/dev/null; then
        echo "✓ OPEN"
    else
        echo "✗ CLOSED hoặc không kết nối được"
    fi
done
echo ""

# 3. Kiểm tra HDFS Web UI
echo "3. Kiểm tra HDFS Web UI:"
if curl -s --connect-timeout 3 "http://$HADOOP_HOST:9870" >/dev/null 2>&1; then
    echo "   ✓ HDFS Web UI đang chạy: http://$HADOOP_HOST:9870"
    echo "   💡 Truy cập để xem thông tin NameNode"
else
    echo "   ❌ Không thể kết nối tới HDFS Web UI (port 9870)"
fi
echo ""

# 4. Thử kết nối với các port khác nhau
echo "4. Thử kết nối HDFS với các ports:"
for port in 8020 9000; do
    echo "   Thử port $port..."
    HDFS_NAMENODE="hdfs://$HADOOP_HOST:$port"
    if command -v hdfs >/dev/null 2>&1; then
        result=$(timeout 10 hdfs dfs -fs "$HDFS_NAMENODE" -ls / 2>&1)
        if [ $? -eq 0 ]; then
            echo "   ✓ Port $port hoạt động! Namenode: $HDFS_NAMENODE"
            echo "   Thử list $HDFS_DATA_DIR:"
            hdfs dfs -fs "$HDFS_NAMENODE" -ls "$HDFS_DATA_DIR" 2>&1 | head -5
            break
        else
            echo "   ✗ Port $port không hoạt động: $(echo $result | head -1)"
        fi
    else
        echo "   ⚠️  hdfs command không có trong PATH"
    fi
done
echo ""

# 5. Kiểm tra từ máy Hadoop (nếu có quyền SSH)
echo "5. Kiểm tra HDFS trên máy Hadoop:"
echo "   💡 Trên máy Hadoop ($HADOOP_HOST), chạy:"
echo "      hdfs dfsadmin -report"
echo "      netstat -tlnp | grep -E '8020|9000|9870'"
echo "      cat ~/hadoop/etc/hadoop/hdfs-site.xml | grep -A 2 dfs.namenode"
echo ""

echo "=========================================="
echo "Kết luận"
echo "=========================================="
echo ""
echo "Nếu tất cả ports đều CLOSED:"
echo "  1. Kiểm tra HDFS có đang chạy không:"
echo "     Trên máy Hadoop: ~/hadoop/sbin/start-dfs.sh"
echo ""
echo "  2. Kiểm tra firewall:"
echo "     sudo ufw status"
echo "     sudo ufw allow 8020/tcp"
echo "     sudo ufw allow 9000/tcp"
echo "     sudo ufw allow 9870/tcp"
echo ""
echo "  3. Kiểm tra cấu hình HDFS:"
echo "     Trên máy Hadoop: cat ~/hadoop/etc/hadoop/hdfs-site.xml"
echo ""

