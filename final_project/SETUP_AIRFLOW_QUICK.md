# Setup Airflow Nhanh - 3 Bước

## Cách 1: Dùng Script Tự Động (Khuyến Nghị)

```bash
cd /home/haminhchien/Documents/bigdata/final_project_recovered
chmod +x scripts/setup_airflow.sh
./scripts/setup_airflow.sh
```

Sau đó load biến môi trường và khởi động:

```bash
source .airflow_env
airflow webserver -p 8080  # Terminal 1
airflow scheduler           # Terminal 2
```

## Cách 2: Setup Thủ Công

### Bước 1: Cài Dependencies

```bash
pip3 install --user celery pika apache-airflow
```

### Bước 2: Tạo Biến Môi Trường

```bash
cat > /home/haminhchien/Documents/bigdata/final_project_recovered/.airflow_env << 'EOF'
export AIRFLOW_HOME=/home/haminhchien/Documents/bigdata/final_project_recovered
export AIRFLOW_CONFIG=/home/haminhchien/Documents/bigdata/final_project_recovered/config/airflow.cfg
export AIRFLOW__CORE__DAGS_FOLDER=/home/haminhchien/Documents/bigdata/final_project_recovered/dags
export AIRFLOW__CORE__PLUGINS_FOLDER=/home/haminhchien/Documents/bigdata/final_project_recovered/plugins
export AIRFLOW__LOGGING__BASE_LOG_FOLDER=/home/haminhchien/Documents/bigdata/final_project_recovered/logs
export PYTHONPATH=/home/haminhchien/Documents/bigdata/final_project_recovered:$PYTHONPATH
EOF

source /home/haminhchien/Documents/bigdata/final_project_recovered/.airflow_env
```

### Bước 3: Khởi Tạo Database

```bash
# Khởi tạo database
airflow db init
```

### Bước 4: Khởi Động Airflow (Standalone)

```bash
# Load biến môi trường
source .airflow_env

# Khởi động Airflow (tự động chạy webserver + scheduler + tạo user admin)
airflow standalone
```

**Lưu ý**: `airflow standalone` sẽ tự động:
- Tạo user admin (username: admin)
- Hiển thị password trong logs
- Chạy webserver trên port 8080
- Chạy scheduler

## Truy Cập

- **URL**: http://localhost:8080
- **Username**: admin
- **Password**: Xem trong logs khi chạy `airflow standalone` (thường là `admin` hoặc được generate tự động)

## Kiểm Tra

```bash
source .airflow_env
airflow dags list | grep -E "train_model_pipeline|predict_streaming_pipeline"
```

## Xem Hướng Dẫn Chi Tiết

Xem file `AIRFLOW_SETUP_GUIDE.md` để biết thêm chi tiết và troubleshooting.

