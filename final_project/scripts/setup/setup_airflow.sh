#!/bin/bash
# Script setup Airflow từ đầu
# Usage: ./scripts/setup_airflow.sh

set -e  # Dừng nếu có lỗi

echo "=========================================="
echo "Setup Airflow từ đầu"
echo "=========================================="

# Lấy đường dẫn project
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "Project directory: $PROJECT_DIR"
cd "$PROJECT_DIR"

# 1. Tạo thư mục cần thiết
echo ""
echo "1. Tạo các thư mục cần thiết..."
mkdir -p "$PROJECT_DIR/logs"
mkdir -p "$PROJECT_DIR/plugins"
mkdir -p "$HOME/airflow/logs"
mkdir -p "$HOME/airflow/plugins"

# 2. Set biến môi trường
echo ""
echo "2. Thiết lập biến môi trường..."

# Tạo file .env nếu chưa có
ENV_FILE="$PROJECT_DIR/.airflow_env"
cat > "$ENV_FILE" << EOF
# Airflow Environment Variables
export AIRFLOW_HOME=$PROJECT_DIR
export AIRFLOW_CONFIG=$PROJECT_DIR/config/airflow.cfg
export AIRFLOW__CORE__DAGS_FOLDER=$PROJECT_DIR/dags
export AIRFLOW__CORE__PLUGINS_FOLDER=$PROJECT_DIR/plugins
export AIRFLOW__LOGGING__BASE_LOG_FOLDER=$PROJECT_DIR/logs
export PYTHONPATH=$PROJECT_DIR:\$PYTHONPATH
EOF

echo "✓ Đã tạo file $ENV_FILE"
echo ""
echo "Để sử dụng, chạy:"
echo "  source $ENV_FILE"
echo ""

# 3. Load biến môi trường
source "$ENV_FILE"

# 4. Kiểm tra và cài đặt dependencies
echo ""
echo "3. Kiểm tra dependencies..."

# Kiểm tra Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 chưa được cài đặt"
    exit 1
fi
echo "✓ Python3: $(python3 --version)"

# Kiểm tra pip
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 chưa được cài đặt"
    exit 1
fi
echo "✓ pip3: $(pip3 --version)"

# Cài đặt dependencies cần thiết
echo ""
echo "4. Cài đặt dependencies..."
pip3 install --user celery pika apache-airflow 2>&1 | grep -E "(Requirement|Successfully|ERROR)" || true

# Kiểm tra Airflow
if ! command -v airflow &> /dev/null; then
    echo "⚠️  Airflow chưa có trong PATH, thử với python3 -m airflow"
    AIRFLOW_CMD="python3 -m airflow"
else
    AIRFLOW_CMD="airflow"
fi

# 5. Khởi tạo database (nếu chưa có)
echo ""
echo "5. Khởi tạo Airflow database..."
if [ ! -f "$PROJECT_DIR/airflow.db" ] && [ ! -f "$HOME/airflow/airflow.db" ]; then
    echo "Khởi tạo database mới..."
    $AIRFLOW_CMD db init 2>&1 | tail -5
    echo "✓ Database đã được khởi tạo"
else
    echo "✓ Database đã tồn tại"
fi

# 6. Lưu ý về user admin (Airflow 3.1.3 dùng standalone)
echo ""
echo "6. Lưu ý về user admin..."
echo "   ✓ Airflow 3.1.3 sẽ tự động tạo user admin khi chạy 'airflow standalone'"
echo "   ✓ Username: admin"
echo "   ✓ Password: admin (hoặc xem trong logs khi chạy standalone)"

# 7. Kiểm tra DAGs
echo ""
echo "7. Kiểm tra DAGs..."
$AIRFLOW_CMD dags list 2>&1 | grep -E "(train_model_pipeline|predict_streaming_pipeline|dag_id)" | head -5 || echo "⚠️  Chưa thấy DAGs, có thể cần cài thêm dependencies"

# 8. Tóm tắt
echo ""
echo "=========================================="
echo "Setup hoàn tất!"
echo "=========================================="
echo ""
echo "Để sử dụng Airflow:"
echo "  1. Load biến môi trường:"
echo "     source $ENV_FILE"
echo ""
echo "  2. Khởi động Airflow (standalone - tự động chạy webserver + scheduler):"
echo "     airflow standalone"
echo ""
echo "  3. Truy cập UI:"
echo "     http://localhost:8080"
echo "     Username: admin"
echo "     Password: admin (hoặc xem trong logs khi chạy standalone)"
echo ""
echo "  4. Kiểm tra DAGs (terminal khác):"
echo "     source $ENV_FILE"
echo "     airflow dags list | grep -E 'train_model_pipeline|predict_streaming_pipeline'"
echo ""
echo "Lưu ý: 'airflow standalone' sẽ tự động:"
echo "  - Tạo user admin nếu chưa có"
echo "  - Chạy webserver trên port 8080"
echo "  - Chạy scheduler"
echo "  - Hiển thị password trong logs"
echo ""

