# HƯỚNG DẪN CHẠY SETUP TỰ ĐỘNG

## Tổng quan

Bạn đang ở **máy development** (không phải Nole1, Nole2, hay Nole3).
Tất cả 3 máy Nole sẽ được setup tự động qua SSH.

### Kiến trúc:
- **Nole1 (192.168.80.165)**: Spark Master + Worker
- **Nole2 (192.168.80.51)**: Kafka + Spark Worker
- **Nole3 (192.168.80.178)**: Airflow + Hadoop + RabbitMQ

---

## Bước 1: Setup SSH Keys

Từ máy development, setup SSH keys cho cả 3 máy:

```bash
# Generate SSH key nếu chưa có
ssh-keygen -t rsa -b 4096

# Copy SSH key đến cả 3 máy
ssh-copy-id nole1@192.168.80.165
ssh-copy-id nole2@192.168.80.51
ssh-copy-id nole3@192.168.80.178

# Test kết nối
ssh nole1@192.168.80.165 exit
ssh nole2@192.168.80.51 exit
ssh nole3@192.168.80.178 exit
```

---

## Bước 2: Chạy Setup Tự Động

```bash
cd ~/Tuan/Project/BigData/final_project
chmod +x scripts/setup_*.sh
./scripts/setup_all.sh
```

Script sẽ tự động:
1. ✅ Setup Nole3 (RabbitMQ, Hadoop, Airflow) qua SSH
2. ✅ Setup Nole1 (Spark Master + Worker) qua SSH
3. ✅ Setup Nole2 (Kafka + Spark Worker) qua SSH
4. ✅ Upload dữ liệu lên HDFS trên Nole3

---

## Bước 3: Start Celery Workers

Sau khi setup xong, start Celery workers trên từng máy:

### Terminal 1: Nole3 (Hadoop queue)
```bash
ssh nole3@192.168.80.178
cd ~/Tuan/Project/BigData/final_project
celery -A mycelery.system_worker worker \
  --loglevel=info \
  --queues=hadoop_queue \
  --hostname=hadoop_worker@nole3 \
  --broker=pyamqp://guest@localhost//
```

### Terminal 2: Nole1 (Spark queue)
```bash
ssh nole1@192.168.80.165
cd ~/Documents/bigdata/final_project
celery -A mycelery.system_worker worker \
  --loglevel=info \
  --queues=spark_master \
  --hostname=spark_worker@nole1 \
  --broker=pyamqp://guest@192.168.80.178//
```

### Terminal 3: Nole2 (Kafka queue)
```bash
ssh nole2@192.168.80.51
cd ~/Documents/bigdata/final_project
celery -A mycelery.system_worker worker \
  --loglevel=info \
  --queues=kafka_queue \
  --hostname=kafka_worker@nole2 \
  --broker=pyamqp://guest@192.168.80.178//
```

---

## Bước 4: Start Airflow

### Terminal 4: Airflow Webserver
```bash
ssh nole3@192.168.80.178
cd ~/Tuan/Project/BigData/final_project
airflow webserver --port 8080
```

### Terminal 5: Airflow Scheduler
```bash
ssh nole3@192.168.80.178
cd ~/Tuan/Project/BigData/final_project
airflow scheduler
```

---

## Bước 5: Verify Services

### Check RabbitMQ
```bash
# Web UI
firefox http://192.168.80.178:15672
# Login: guest/guest
# Kiểm tra Queues tab: phải thấy 3 queues
```

### Check HDFS
```bash
# Web UI
firefox http://192.168.80.178:9870
```

### Check Spark
```bash
# Web UI
firefox http://192.168.80.165:8080
# Phải thấy 2 workers: nole1 và nole2
```

### Check Airflow
```bash
# Web UI
firefox http://192.168.80.178:8080
# Login: admin/admin
```

---

## Bước 6: Chạy Pipeline

1. Mở Airflow UI: http://192.168.80.178:8080
2. Enable và trigger DAG: `train_model_pipeline_fixed`
3. Đợi training hoàn thành
4. Enable và trigger DAG: `predict_streaming_pipeline`

---

## Troubleshooting

### Lỗi SSH
```bash
# Kiểm tra SSH config
cat ~/.ssh/config

# Test kết nối
ssh -v nole1@192.168.80.165
```

### Lỗi Celery không kết nối RabbitMQ
```bash
# Kiểm tra RabbitMQ trên Nole3
ssh nole3@192.168.80.178
sudo systemctl status rabbitmq-server
telnet localhost 5672
```

### Lỗi HDFS safe mode
```bash
ssh nole3@192.168.80.178
~/hadoop/bin/hdfs dfsadmin -safemode leave
```

---

## Scripts Riêng Lẻ

Nếu muốn setup từng máy riêng:

```bash
# Setup chỉ Nole3
./scripts/setup_nole3_ssh.sh

# Setup chỉ Nole1
./scripts/setup_nole1_ssh.sh

# Setup chỉ Nole2
./scripts/setup_nole2_ssh.sh
```

---

## Lưu ý

- Tất cả scripts đều chạy qua SSH từ máy development
- Không cần phải login vào từng máy để setup
- Project code sẽ được copy tự động đến đúng vị trí trên mỗi máy
- Các service sẽ được start tự động (trừ Airflow và Celery workers)
