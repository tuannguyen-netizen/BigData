#!/bin/bash
# Script di chuyển từ Airflow cũ (~/airflow) sang Airflow mới (project directory)
# Usage: ./scripts/migrate_airflow.sh

set -e

echo "=========================================="
echo "Di Chuyển Airflow Từ ~/airflow Sang Project"
echo "=========================================="

OLD_AIRFLOW_HOME="$HOME/airflow"
NEW_AIRFLOW_HOME="/home/haminhchien/Documents/bigdata/final_project"
ENV_FILE="$NEW_AIRFLOW_HOME/.airflow_env"

# Kiểm tra Airflow cũ có tồn tại không
if [ ! -d "$OLD_AIRFLOW_HOME" ]; then
    echo "✓ Không có Airflow cũ tại $OLD_AIRFLOW_HOME"
    echo "Có thể tiếp tục setup mới."
    exit 0
fi

echo ""
echo "Phát hiện Airflow cũ tại: $OLD_AIRFLOW_HOME"
echo "Sẽ di chuyển sang: $NEW_AIRFLOW_HOME"
echo ""

# 1. Backup Airflow cũ
echo "1. Backup Airflow cũ..."
BACKUP_DIR="$OLD_AIRFLOW_HOME.backup.$(date +%Y%m%d_%H%M%S)"
if [ -d "$OLD_AIRFLOW_HOME" ]; then
    echo "   Đang backup sang: $BACKUP_DIR"
    cp -r "$OLD_AIRFLOW_HOME" "$BACKUP_DIR" 2>/dev/null || {
        echo "   ⚠️  Không thể backup, có thể do permission"
        echo "   Bạn có muốn tiếp tục? (yes/no)"
        read confirm
        if [ "$confirm" != "yes" ]; then
            exit 1
        fi
    }
    echo "   ✓ Đã backup"
else
    echo "   ✓ Không có gì để backup"
fi

# 2. Dừng các process Airflow cũ
echo ""
echo "2. Dừng các process Airflow cũ..."
pkill -f "airflow webserver" 2>/dev/null && echo "   ✓ Đã dừng webserver" || echo "   ✓ Không có webserver đang chạy"
pkill -f "airflow scheduler" 2>/dev/null && echo "   ✓ Đã dừng scheduler" || echo "   ✓ Không có scheduler đang chạy"
pkill -f "celery.*worker" 2>/dev/null && echo "   ✓ Đã dừng celery workers" || echo "   ✓ Không có celery workers đang chạy"

# 3. Đổi tên thư mục Airflow cũ
echo ""
echo "3. Đổi tên thư mục Airflow cũ..."
if [ -d "$OLD_AIRFLOW_HOME" ]; then
    OLD_AIRFLOW_RENAMED="$OLD_AIRFLOW_HOME.old.$(date +%Y%m%d)"
    if [ ! -d "$OLD_AIRFLOW_RENAMED" ]; then
        mv "$OLD_AIRFLOW_HOME" "$OLD_AIRFLOW_RENAMED"
        echo "   ✓ Đã đổi tên thành: $OLD_AIRFLOW_RENAMED"
    else
        echo "   ⚠️  Thư mục $OLD_AIRFLOW_RENAMED đã tồn tại"
        echo "   Giữ nguyên $OLD_AIRFLOW_HOME"
    fi
fi

# 4. Đảm bảo file .airflow_env tồn tại
echo ""
echo "4. Kiểm tra file .airflow_env..."
if [ ! -f "$ENV_FILE" ]; then
    echo "   Tạo file .airflow_env..."
    cat > "$ENV_FILE" << 'EOF'
# Airflow Environment Variables
export AIRFLOW_HOME=/home/haminhchien/Documents/bigdata/final_project
export AIRFLOW_CONFIG=/home/haminhchien/Documents/bigdata/final_project/config/airflow.cfg
export AIRFLOW__CORE__DAGS_FOLDER=/home/haminhchien/Documents/bigdata/final_project/dags
export AIRFLOW__CORE__PLUGINS_FOLDER=/home/haminhchien/Documents/bigdata/final_project/plugins
export AIRFLOW__LOGGING__BASE_LOG_FOLDER=/home/haminhchien/Documents/bigdata/final_project/logs
export PYTHONPATH=/home/haminhchien/Documents/bigdata/final_project:$PYTHONPATH
EOF
    echo "   ✓ Đã tạo file .airflow_env"
else
    echo "   ✓ File .airflow_env đã tồn tại"
fi

# 5. Tạo alias trong bashrc để luôn load biến môi trường
echo ""
echo "5. Cấu hình tự động load biến môi trường..."
BASHRC="$HOME/.bashrc"
if ! grep -q "source.*\.airflow_env" "$BASHRC" 2>/dev/null; then
    echo "" >> "$BASHRC"
    echo "# Auto-load Airflow environment for project" >> "$BASHRC"
    echo "if [ -f \"$ENV_FILE\" ]; then" >> "$BASHRC"
    echo "    source \"$ENV_FILE\"" >> "$BASHRC"
    echo "fi" >> "$BASHRC"
    echo "   ✓ Đã thêm vào ~/.bashrc"
else
    echo "   ✓ Đã có trong ~/.bashrc"
fi

# 6. Tạo wrapper script để đảm bảo luôn dùng đúng Airflow
echo ""
echo "6. Tạo wrapper script..."
WRAPPER_SCRIPT="$NEW_AIRFLOW_HOME/airflow_wrapper.sh"
cat > "$WRAPPER_SCRIPT" << 'EOF'
#!/bin/bash
# Wrapper script để đảm bảo luôn dùng Airflow trong project
source "$(dirname "$0")/.airflow_env"
exec airflow "$@"
EOF
chmod +x "$WRAPPER_SCRIPT"
echo "   ✓ Đã tạo $WRAPPER_SCRIPT"

# 7. Tóm tắt
echo ""
echo "=========================================="
echo "Hoàn Tất!"
echo "=========================================="
echo ""
echo "Các thay đổi:"
echo "  ✓ Airflow cũ đã được backup/đổi tên"
echo "  ✓ File .airflow_env đã được tạo/cập nhật"
echo "  ✓ Đã thêm auto-load vào ~/.bashrc"
echo "  ✓ Đã tạo wrapper script: airflow_wrapper.sh"
echo ""
echo "Cách sử dụng:"
echo ""
echo "1. Load biến môi trường (mỗi terminal mới):"
echo "   source $ENV_FILE"
echo ""
echo "2. Hoặc dùng wrapper script:"
echo "   $WRAPPER_SCRIPT dags list"
echo ""
echo "3. Hoặc mở terminal mới (sẽ tự động load)"
echo ""
echo "4. Kiểm tra đang dùng Airflow nào:"
echo "   echo \$AIRFLOW_HOME"
echo "   # Phải hiển thị: $NEW_AIRFLOW_HOME"
echo ""
echo "5. Setup Airflow mới:"
echo "   source $ENV_FILE"
echo "   airflow db init"
echo "   airflow users create --username admin --firstname Admin --lastname User --role Admin --email admin@example.com --password admin"
echo ""

