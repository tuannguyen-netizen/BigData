#!/bin/bash
# Script dọn dẹp Airflow cũ
# Usage: ./scripts/cleanup_airflow.sh

set -e

echo "=========================================="
echo "Dọn Dẹp Airflow Cũ"
echo "=========================================="
echo ""
echo "⚠️  CẢNH BÁO: Script này sẽ xóa:"
echo "   - Database Airflow cũ"
echo "   - Logs cũ"
echo "   - Các process Airflow đang chạy"
echo ""
read -p "Bạn có chắc muốn tiếp tục? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Đã hủy."
    exit 0
fi

# 1. Dừng các process Airflow đang chạy
echo ""
echo "1. Dừng các process Airflow đang chạy..."

# Tìm và kill webserver
WEBSERVER_PIDS=$(ps aux | grep "airflow webserver" | grep -v grep | awk '{print $2}' || true)
if [ ! -z "$WEBSERVER_PIDS" ]; then
    echo "   Đang dừng webserver (PIDs: $WEBSERVER_PIDS)..."
    echo "$WEBSERVER_PIDS" | xargs kill -9 2>/dev/null || true
    echo "   ✓ Webserver đã dừng"
else
    echo "   ✓ Không có webserver đang chạy"
fi

# Tìm và kill scheduler
SCHEDULER_PIDS=$(ps aux | grep "airflow scheduler" | grep -v grep | awk '{print $2}' || true)
if [ ! -z "$SCHEDULER_PIDS" ]; then
    echo "   Đang dừng scheduler (PIDs: $SCHEDULER_PIDS)..."
    echo "$SCHEDULER_PIDS" | xargs kill -9 2>/dev/null || true
    echo "   ✓ Scheduler đã dừng"
else
    echo "   ✓ Không có scheduler đang chạy"
fi

# Tìm và kill celery worker
CELERY_PIDS=$(ps aux | grep "celery.*worker" | grep -v grep | awk '{print $2}' || true)
if [ ! -z "$CELERY_PIDS" ]; then
    echo "   Đang dừng celery workers (PIDs: $CELERY_PIDS)..."
    echo "$CELERY_PIDS" | xargs kill -9 2>/dev/null || true
    echo "   ✓ Celery workers đã dừng"
else
    echo "   ✓ Không có celery workers đang chạy"
fi

# 2. Xóa database cũ trong project directory
echo ""
echo "2. Xóa database cũ trong project..."
PROJECT_DIR="/home/haminhchien/Documents/bigdata/final_project"
if [ -f "$PROJECT_DIR/airflow.db" ]; then
    rm -f "$PROJECT_DIR/airflow.db"
    echo "   ✓ Đã xóa $PROJECT_DIR/airflow.db"
else
    echo "   ✓ Không có database trong project directory"
fi

# 3. Xóa database cũ trong ~/airflow (nếu có)
echo ""
echo "3. Xóa database cũ trong ~/airflow (nếu có)..."
OLD_AIRFLOW_HOME="/home/haminhchien/Documents/bigdata/final_project"
if [ -f "$OLD_AIRFLOW_HOME/airflow.db" ]; then
    read -p "   Xóa database trong $OLD_AIRFLOW_HOME/airflow.db? (yes/no): " del_old
    if [ "$del_old" = "yes" ]; then
        rm -f "$OLD_AIRFLOW_HOME/airflow.db"
        echo "   ✓ Đã xóa $OLD_AIRFLOW_HOME/airflow.db"
    else
        echo "   ⏭️  Giữ lại database cũ"
    fi
else
    echo "   ✓ Không có database trong ~/airflow"
fi

# 4. Xóa logs cũ (tùy chọn)
echo ""
read -p "4. Xóa logs cũ? (yes/no): " del_logs
if [ "$del_logs" = "yes" ]; then
    if [ -d "$PROJECT_DIR/logs" ]; then
        rm -rf "$PROJECT_DIR/logs/*"
        echo "   ✓ Đã xóa logs trong $PROJECT_DIR/logs"
    fi
    if [ -d "$OLD_AIRFLOW_HOME/logs" ]; then
        rm -rf "$OLD_AIRFLOW_HOME/logs/*"
        echo "   ✓ Đã xóa logs trong $OLD_AIRFLOW_HOME/logs"
    fi
else
    echo "   ⏭️  Giữ lại logs"
fi

# 5. Tóm tắt
echo ""
echo "=========================================="
echo "Dọn Dẹp Hoàn Tất!"
echo "=========================================="
echo ""
echo "Các bước tiếp theo:"
echo "  1. Chạy script setup: ./scripts/setup_airflow.sh"
echo "  2. Hoặc setup thủ công theo AIRFLOW_SETUP_GUIDE.md"
echo ""

