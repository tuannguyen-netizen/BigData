#!/bin/bash
# Script để start Celery worker cho Spark trên máy Spark
# Usage: ./start_spark_worker.sh <HOSTNAME_AIRFLOW>

if [ $# -ne 1 ]; then
    echo "Usage: $0 <HOSTNAME_AIRFLOW>"
    echo "Example: $0 airflow-master"
    exit 1
fi

HOSTNAME_AIRFLOW=$1
# Tự động detect project directory từ script location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=========================================="
echo "Start Celery Worker cho Spark"
echo "=========================================="
echo "RabbitMQ Host: $HOSTNAME_AIRFLOW"
echo "Queue: spark"
echo ""

# Set broker URL
export CELERY_BROKER_URL="amqp://guest:guest@${HOSTNAME_AIRFLOW}:5672//"

# Test kết nối
echo "Test kết nối tới RabbitMQ..."
if ! timeout 5 bash -c "echo > /dev/tcp/${HOSTNAME_AIRFLOW}/5672" 2>/dev/null; then
    echo "❌ Không thể kết nối tới $HOSTNAME_AIRFLOW:5672"
    echo "Kiểm tra:"
    echo "  1. /etc/hosts đã có entry cho $HOSTNAME_AIRFLOW chưa?"
    echo "  2. RabbitMQ đang chạy trên máy Airflow chưa?"
    echo "  3. Firewall đã mở port 5672 chưa?"
    exit 1
fi

echo "✓ Kết nối thành công!"

# ✅ FIX: Tự động detect và set SPARK_HOME
if [ -z "$SPARK_HOME" ]; then
    # Thử các vị trí thông thường
    if [ -d "/opt/spark" ] && [ -f "/opt/spark/bin/spark-submit" ]; then
        export SPARK_HOME="/opt/spark"
    elif [ -d "$HOME/spark" ] && [ -f "$HOME/spark/bin/spark-submit" ]; then
        export SPARK_HOME="$HOME/spark"
    elif [ -d "/usr/local/spark" ] && [ -f "/usr/local/spark/bin/spark-submit" ]; then
        export SPARK_HOME="/usr/local/spark"
    elif [ -d "/opt/spark-4.0.0-bin-hadoop3" ]; then
        export SPARK_HOME="/opt/spark-4.0.0-bin-hadoop3"
    fi
fi

if [ -n "$SPARK_HOME" ]; then
    export PATH="$SPARK_HOME/bin:$PATH"
    echo "✓ SPARK_HOME: $SPARK_HOME"
    echo "✓ spark-submit: $(which spark-submit 2>/dev/null || echo 'not in PATH')"
else
    echo "⚠️  SPARK_HOME not set, script will try to find spark-submit automatically"
fi

# Chuyển đến thư mục project
cd "$PROJECT_DIR" || {
    echo "❌ Không tìm thấy thư mục: $PROJECT_DIR"
    echo "Vui lòng sửa PROJECT_DIR trong script này"
    exit 1
}

# ✅ FIX: Kiểm tra và cài đặt Python dependencies
echo ""
echo "📦 Kiểm tra Python dependencies..."
if [ -f "$PROJECT_DIR/requirements.txt" ]; then
    # Kiểm tra numpy (dependency quan trọng nhất cho PySpark ML)
    if ! python3 -c "import numpy" 2>/dev/null; then
        echo "⚠️  numpy chưa được cài, đang cài đặt dependencies từ requirements.txt..."
        pip3 install --user -r "$PROJECT_DIR/requirements.txt" 2>&1 | tail -10 || {
            echo "⚠️  Cài đặt dependencies có thể đã thất bại hoặc một số đã được cài"
            echo "   Kiểm tra: pip3 list | grep -E 'numpy|pandas|scikit-learn'"
        }
    else
        echo "✓ Python dependencies đã được cài đặt (numpy found)"
    fi
else
    echo "⚠️  Không tìm thấy requirements.txt, cài đặt numpy cơ bản..."
    pip3 install --user numpy>=1.21.0 2>&1 | tail -5 || echo "⚠️  Cài đặt numpy có thể đã thất bại"
fi

# Start worker
echo ""
echo "Đang start Celery worker..."
celery -A mycelery.system_worker worker \
  -Q spark \
  -n spark@%h \
  --loglevel=INFO

