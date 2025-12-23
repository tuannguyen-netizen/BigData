#!/bin/bash
# Script để sửa lỗi Airflow không cập nhật DAG
# Nguyên nhân: Airflow đang chạy với AIRFLOW_HOME sai (final_project_recovered thay vì final_project)

set -e

echo "=========================================="
echo "Sửa lỗi Airflow không cập nhật DAG"
echo "=========================================="

PROJECT_DIR="/home/haminhchien/Documents/bigdata/final_project"
ENV_FILE="$PROJECT_DIR/.airflow_env"

# 1. Kiểm tra file .airflow_env
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Không tìm thấy file .airflow_env"
    echo "   Đang tạo file .airflow_env..."
    cat > "$ENV_FILE" << EOF
# Airflow Environment Variables
export AIRFLOW_HOME=$PROJECT_DIR
export AIRFLOW_CONFIG=$PROJECT_DIR/config/airflow.cfg
export AIRFLOW__CORE__DAGS_FOLDER=$PROJECT_DIR/dags
export AIRFLOW__CORE__PLUGINS_FOLDER=$PROJECT_DIR/plugins
export AIRFLOW__LOGGING__BASE_LOG_FOLDER=$PROJECT_DIR/logs
export PYTHONPATH=$PROJECT_DIR:\$PYTHONPATH
EOF
    echo "✓ Đã tạo file .airflow_env"
fi

# 2. Kiểm tra Airflow đang chạy
echo ""
echo "2. Kiểm tra Airflow đang chạy..."
AIRFLOW_PIDS=$(pgrep -f "airflow.*standalone|airflow.*scheduler|airflow.*webserver" || true)

if [ -n "$AIRFLOW_PIDS" ]; then
    echo "⚠️  Phát hiện Airflow đang chạy (PIDs: $AIRFLOW_PIDS)"
    echo ""
    echo "   Để sửa lỗi, bạn cần:"
    echo "   1. Dừng Airflow hiện tại (Ctrl+C trong terminal đang chạy airflow standalone)"
    echo "   2. Hoặc kill process: kill $AIRFLOW_PIDS"
    echo "   3. Load biến môi trường đúng: source $ENV_FILE"
    echo "   4. Khởi động lại: airflow standalone"
    echo ""
    read -p "   Bạn có muốn tự động dừng Airflow và khởi động lại? (yes/no): " restart_choice
    
    if [ "$restart_choice" = "yes" ]; then
        echo "   Đang dừng Airflow..."
        kill $AIRFLOW_PIDS 2>/dev/null || true
        sleep 3
        
        # Kiểm tra lại
        REMAINING=$(pgrep -f "airflow.*standalone|airflow.*scheduler|airflow.*webserver" || true)
        if [ -n "$REMAINING" ]; then
            echo "   ⚠️  Một số process vẫn còn, đang force kill..."
            kill -9 $REMAINING 2>/dev/null || true
            sleep 2
        fi
        echo "   ✓ Đã dừng Airflow"
    else
        echo "   Bỏ qua, bạn sẽ tự dừng Airflow"
    fi
else
    echo "✓ Airflow không đang chạy"
fi

# 3. Kiểm tra biến môi trường hiện tại
echo ""
echo "3. Kiểm tra biến môi trường..."
CURRENT_AIRFLOW_HOME=${AIRFLOW_HOME:-"chưa set"}
echo "   AIRFLOW_HOME hiện tại: $CURRENT_AIRFLOW_HOME"
echo "   AIRFLOW_HOME đúng: $PROJECT_DIR"

if [ "$CURRENT_AIRFLOW_HOME" != "$PROJECT_DIR" ]; then
    echo "   ⚠️  Biến môi trường không đúng!"
else
    echo "   ✓ Biến môi trường đúng"
fi

# 4. Kiểm tra DAG folder
echo ""
echo "4. Kiểm tra thư mục DAG..."
if [ -d "$PROJECT_DIR/dags" ]; then
    DAG_COUNT=$(find "$PROJECT_DIR/dags" -name "*.py" -type f | wc -l)
    echo "   ✓ Thư mục DAG tồn tại: $PROJECT_DIR/dags"
    echo "   ✓ Số file DAG: $DAG_COUNT"
    find "$PROJECT_DIR/dags" -name "*.py" -type f | while read dag; do
        echo "     - $(basename $dag)"
    done
else
    echo "   ❌ Thư mục DAG không tồn tại: $PROJECT_DIR/dags"
    exit 1
fi

# 5. Kiểm tra config file
echo ""
echo "5. Kiểm tra config file..."
if [ -f "$PROJECT_DIR/config/airflow.cfg" ]; then
    CONFIG_DAGS_FOLDER=$(grep "^dags_folder" "$PROJECT_DIR/config/airflow.cfg" | cut -d'=' -f2 | tr -d ' ')
    echo "   ✓ Config file tồn tại"
    echo "   dags_folder trong config: $CONFIG_DAGS_FOLDER"
    if [ "$CONFIG_DAGS_FOLDER" != "$PROJECT_DIR/dags" ]; then
        echo "   ⚠️  dags_folder trong config không đúng!"
    else
        echo "   ✓ dags_folder trong config đúng"
    fi
else
    echo "   ❌ Config file không tồn tại: $PROJECT_DIR/config/airflow.cfg"
    exit 1
fi

# 6. Hướng dẫn khởi động lại
echo ""
echo "=========================================="
echo "Hướng dẫn khởi động lại Airflow"
echo "=========================================="
echo ""
echo "Để Airflow cập nhật DAG đúng cách, làm theo các bước sau:"
echo ""
echo "1. Load biến môi trường đúng:"
echo "   source $ENV_FILE"
echo ""
echo "2. Kiểm tra biến môi trường:"
echo "   echo \$AIRFLOW_HOME"
echo "   # Phải hiển thị: $PROJECT_DIR"
echo ""
echo "3. Kiểm tra DAG folder trong config:"
echo "   airflow config get-value core dags_folder"
echo "   # Phải hiển thị: $PROJECT_DIR/dags"
echo ""
echo "4. Khởi động Airflow:"
echo "   airflow standalone"
echo ""
echo "5. Kiểm tra DAGs đã được load:"
echo "   airflow dags list | grep -E 'train_model_pipeline|predict_streaming_pipeline'"
echo ""
echo "=========================================="
echo "Lưu ý quan trọng:"
echo "=========================================="
echo "- Nếu Airflow đang chạy với AIRFLOW_HOME sai, nó sẽ KHÔNG thấy DAGs mới"
echo "- Luôn load .airflow_env TRƯỚC KHI chạy airflow standalone"
echo "- Kiểm tra \$AIRFLOW_HOME trước khi khởi động Airflow"
echo ""

