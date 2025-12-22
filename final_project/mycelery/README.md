# MyCelery - Celery Worker System

## Tổng Quan

Thư mục này chứa **Celery worker** để điều khiển các máy từ xa qua RabbitMQ.

## File Quan Trọng

### `system_worker.py` - **KHÔNG THỂ XÓA**

File này là **core** của hệ thống phân tán:

1. **Định nghĩa Celery tasks**:
   - `docker_compose_up`: Start Docker containers (Kafka, Spark)
   - `run_command`: Chạy shell commands (tạo Kafka topics, etc.)
   - `docker_run`, `docker_stop`, `docker_compose_down`, etc.

2. **Được sử dụng trong DAGs**:
   - `dags/predict_dag.py`: Import `docker_compose_up`, `run_command`
   - `dags/ml_pipeline_dag.py`: Import `docker_compose_up`, `run_command`

3. **Chạy như worker trên các máy**:
   - Máy Kafka: `celery -A mycelery.system_worker worker -Q node_57`
   - Máy Spark: `celery -A mycelery.system_worker worker -Q spark`

## Cách Hoạt Động

```
Máy Airflow (DAG)
    │
    │ Gửi task vào RabbitMQ queue
    ▼
RabbitMQ (Broker)
    │
    │ Phân phối task tới worker
    ▼
Máy Kafka/Spark (Celery Worker)
    │
    │ Thực thi task (docker-compose up, run command)
    ▼
Kafka/Spark được start
```

## Setup

### Trên Máy Airflow

File này được import trong DAGs, không cần chạy worker riêng (trừ khi có queue `system`).

### Trên Máy Kafka/Spark

1. Copy file `system_worker.py` lên máy
2. Cài dependencies: `pip install celery pika`
3. Chạy worker:

```bash
# Máy Kafka
export CELERY_BROKER_URL="amqp://guest:guest@airflow-master:5672//"
celery -A mycelery.system_worker worker -Q node_57 -n kafka@%h --loglevel=INFO

# Máy Spark  
export CELERY_BROKER_URL="amqp://guest:guest@airflow-master:5672//"
celery -A mycelery.system_worker worker -Q spark -n spark@%h --loglevel=INFO
```

Hoặc dùng scripts:
- `scripts/start_kafka_worker.sh`
- `scripts/start_spark_worker.sh`

## Tasks Available

- `docker_compose_up`: Start Docker Compose services
- `docker_compose_down`: Stop Docker Compose services
- `run_command`: Execute shell command
- `docker_run`: Run Docker container
- `docker_stop`: Stop Docker container
- `docker_ps`: List Docker containers
- `docker_compose_ps`: List Docker Compose services
- `docker_compose_logs`: Get Docker Compose logs

## Lưu Ý

- **Broker URL**: Default là `localhost` (chỉ đúng trên máy Airflow)
- **Override**: Khi chạy worker trên máy khác, dùng `CELERY_BROKER_URL` env var
- **Queues**: Mỗi máy lắng nghe queue riêng (`node_57` cho Kafka, `spark` cho Spark)
- **Không xóa**: File này là phần core của hệ thống phân tán

