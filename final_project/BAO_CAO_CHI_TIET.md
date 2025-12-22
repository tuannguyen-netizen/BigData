# BÁO CÁO CHI TIẾT: HỆ THỐNG MACHINE LEARNING STREAMING VỚI SPARK, KAFKA VÀ AIRFLOW

## MỤC LỤC

1. [Tổng quan dự án](#1-tổng-quan-dự-án)
2. [Kiến trúc hệ thống](#2-kiến-trúc-hệ-thống)
3. [Phân tích chi tiết các thành phần](#3-phân-tích-chi-tiết-các-thành-phần)
4. [Luồng xử lý dữ liệu](#4-luồng-xử-lý-dữ-liệu)
5. [Kết quả và đánh giá](#5-kết-quả-và-đánh-giá)
6. [Kết luận](#6-kết-luận)

---

## 1. TỔNG QUAN DỰ ÁN

### 1.1. Mục tiêu

Dự án xây dựng một hệ thống Machine Learning streaming end-to-end để dự đoán giá nhà real-time sử dụng:
- **Apache Spark ML**: Huấn luyện và dự đoán với mô hình Random Forest
- **Apache Kafka**: Hệ thống message queue cho streaming data
- **Apache Airflow**: Orchestration và điều phối toàn bộ pipeline
- **RabbitMQ + Celery**: Điều khiển các node từ xa không cần SSH
- **HDFS**: Lưu trữ dữ liệu và model
- **Python**: Ngôn ngữ lập trình chính cho các thành phần

### 1.2. Kiến trúc phân tán

Hệ thống được triển khai trên kiến trúc phân tán gồm nhiều máy:
- **Machine Airflow (192.168.80.147)**: Airflow orchestrator, RabbitMQ broker
- **Machine Kafka/Hadoop (192.168.80.127/worker1)**: Kafka cluster, HDFS Namenode
- **Machine Spark (192.168.80.207/worker3)**: Spark Master và Workers

**Giao tiếp giữa các máy:**
- Sử dụng **RabbitMQ + Celery** để điều khiển từ xa (không cần SSH)
- Các Celery workers chạy trên từng máy và listen trên queues riêng
- Airflow chỉ cần biết queue names, không cần biết IP/hostname cụ thể

### 1.3. Dataset

Sử dụng **California Housing Dataset** từ scikit-learn với các đặc trưng:
- `MedInc`: Thu nhập trung bình
- `HouseAge`: Tuổi nhà
- `AveRooms`: Số phòng trung bình
- `AveBedrms`: Số phòng ngủ trung bình
- `Population`: Dân số
- `AveOccup`: Mật độ chiếm dụng trung bình
- `Latitude`: Vĩ độ
- `Longitude`: Kinh độ
- `target`: Giá nhà trung bình (đơn vị: $100,000)

---

## 2. KIẾN TRÚC HỆ THỐNG

### 2.1. Sơ đồ tổng quan

```
┌─────────────────────────────────────────────────────────┐
│              Airflow (192.168.80.147)                  │
│  ┌──────────────┐         ┌──────────────┐            │
│  │  Airflow DAG │────────▶│  RabbitMQ    │            │
│  └──────────────┘         └──────┬───────┘            │
└──────────────────────────────────┼─────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
        ┌───────────▼───┐  ┌───────▼──────┐  ┌───▼──────────┐
        │ Kafka Worker  │  │ Spark Worker │  │ Hadoop Worker│
        │ (node_57)     │  │ (spark)      │  │ (node_57)    │
        └───────┬───────┘  └──────┬───────┘  └───┬──────────┘
                │                 │              │
        ┌───────▼───────┐  ┌──────▼──────┐  ┌───▼──────────┐
        │ Kafka Cluster │  │ Spark Master │  │ HDFS         │
        │ (Docker)      │  │ + Workers    │  │ Namenode     │
        │ Port: 9092    │  │ Port: 7077   │  │ Port: 8020   │
        └───────────────┘  └──────────────┘  └──────────────┘
```

### 2.2. Luồng dữ liệu chính

```
1. Prepare Data → Upload to HDFS
2. Train Model (Spark ML) → Save Model to HDFS
3. Producer (read from HDFS) → Kafka → Spark Streaming → Kafka Output
4. Consumer → Visualization
```

### 2.3. Các thành phần chính

1. **Data Preparation** (`data/prepare_data.py`, `data/upload_to_hdfs.py`)
2. **Model Training** (`spark_jobs/train_model.py`)
3. **Streaming Prediction** (`spark_jobs/streaming_predict.py`)
4. **Kafka Producer** (`streaming/kafka_producer.py`) - Đọc từ HDFS
5. **Kafka Consumer & Visualization** (`visualization/kafka_consumer.py`)
6. **Web UI** (`ui.py`, `predict_service.py`) - Hỗ trợ load model từ HDFS
7. **Airflow Orchestration** (`dags/train_dag.py`, `dags/predict_dag.py`)
8. **Celery Workers** (`mycelery/system_worker.py`)

---

## 3. PHÂN TÍCH CHI TIẾT CÁC THÀNH PHẦN

### 3.1. Data Preparation

#### 3.1.1. `data/prepare_data.py`

**Mục đích:** Chuẩn bị và chia dữ liệu thành hai tập:
- **Training data**: 80% dữ liệu để huấn luyện mô hình
- **Streaming data**: 20% dữ liệu để mô phỏng streaming

**Chức năng:**
```python
def prepare_data():
    # Tải dataset California Housing
    housing = fetch_california_housing()
    df = pd.DataFrame(housing.data, columns=housing.feature_names)
    df['target'] = housing.target
    
    # Chia 80% train, 20% streaming
    train_df, streaming_df = train_test_split(df, test_size=0.2, random_state=42)
    
    # Lưu vào CSV
    train_df.to_csv('data/train_data.csv', index=False)
    streaming_df.to_csv('data/streaming_data.csv', index=False)
```

**Kết quả:**
- `data/train_data.csv`: ~16,512 mẫu (80%)
- `data/streaming_data.csv`: ~4,128 mẫu (20%)

#### 3.1.2. `data/upload_to_hdfs.py`

**Mục đích:** Upload dữ liệu từ local lên HDFS

**Cấu hình HDFS:**
- **HDFS Namenode**: `hdfs://worker1:8020` (hoặc `hdfs://192.168.80.127:8020`)
- **HDFS Data Directory**: `/bigdata/house_prices`
- **Training data path**: `hdfs://worker1:8020/bigdata/house_prices/train_data.csv`
- **Streaming data path**: `hdfs://worker1:8020/bigdata/house_prices/streaming_data.csv`

**Chức năng:**
- Tự động detect project directory
- Kiểm tra HDFS availability
- Upload cả `train_data.csv` và `streaming_data.csv` lên HDFS
- Verify upload thành công

---

### 3.2. Model Training (`spark_jobs/train_model.py`)

#### 3.2.1. Mục đích
Huấn luyện mô hình Random Forest Regressor để dự đoán giá nhà sử dụng Spark ML, đọc dữ liệu từ HDFS và lưu model lên HDFS.

#### 3.2.2. Cấu hình HDFS

```python
HDFS_NAMENODE = "hdfs://192.168.80.127:8020"  # Hoặc hdfs://worker1:8020
HDFS_TRAIN_DATA_PATH = "hdfs://192.168.80.127:8020/bigdata/house_prices/train_data.csv"
HDFS_MODEL_PATH = "hdfs://192.168.80.127:8020/bigdata/model"
```

#### 3.2.3. Kiến trúc mô hình

**Pipeline gồm 2 stages:**
1. **VectorAssembler**: Kết hợp các đặc trưng thành vector
2. **RandomForestRegressor**: Mô hình hồi quy Random Forest

**Tham số mô hình:**
- `numTrees`: 100 cây
- `maxDepth`: 10
- `seed`: 42 (đảm bảo reproducibility)

#### 3.2.4. Quy trình huấn luyện

```python
# 1. Khởi tạo Spark Session với HDFS config
spark = SparkSession.builder \
    .appName("HousePriceModelTraining") \
    .config("spark.hadoop.fs.defaultFS", HDFS_NAMENODE) \
    .getOrCreate()

# 2. Đọc dữ liệu từ HDFS
df = spark.read.csv(HDFS_TRAIN_DATA_PATH, header=True, inferSchema=True)

# 3. Tạo pipeline
pipeline = Pipeline(stages=[assembler, rf])

# 4. Chia train/test (80/20)
train_data, test_data = df.randomSplit([0.8, 0.2], seed=42)

# 5. Huấn luyện
model = pipeline.fit(train_data)

# 6. Đánh giá
predictions = model.transform(test_data)
evaluator_rmse = RegressionEvaluator(...)
rmse = evaluator_rmse.evaluate(predictions)

# 7. Lưu model lên HDFS
model.write().overwrite().save(HDFS_MODEL_PATH)
```

#### 3.2.5. Metrics đánh giá

Mô hình được đánh giá bằng 3 metrics:
- **RMSE** (Root Mean Squared Error): Sai số bình phương trung bình
- **MAE** (Mean Absolute Error): Sai số tuyệt đối trung bình
- **R²** (Coefficient of Determination): Hệ số xác định

#### 3.2.6. Lưu trữ mô hình

**HDFS Path:** `hdfs://192.168.80.127:8020/bigdata/model`

Cấu trúc thư mục trên HDFS:
```
/bigdata/model/
├── metadata/
│   └── part-00000-*.txt
└── stages/
    ├── 0_VectorAssembler_*/
    └── 1_RandomForestRegressor_*/
        ├── data/
        ├── metadata/
        └── treesMetadata/
```

#### 3.2.7. Logging và Progress Tracking

- **STEP 1/7**: Creating Spark session
- **STEP 2/7**: Reading data from HDFS
- **STEP 3/7**: Counting samples
- **STEP 4/7**: Splitting train/test data
- **STEP 5/7**: Training model (với progress logging mỗi 30s)
- **STEP 6/7**: Evaluating model
- **STEP 7/7**: Saving model to HDFS

Tất cả logs được flush ngay để theo dõi real-time.

---

### 3.3. Streaming Prediction (`spark_jobs/streaming_predict.py`)

#### 3.3.1. Mục đích
Đọc dữ liệu streaming từ Kafka, áp dụng mô hình đã huấn luyện (load từ HDFS) để dự đoán, và gửi kết quả về Kafka topic khác.

#### 3.3.2. Cấu hình

```python
HDFS_NAMENODE = "hdfs://worker1:8020"
HDFS_MODEL_PATH = "hdfs://worker1:8020/bigdata/model"
KAFKA_BOOTSTRAP_SERVERS = "192.168.80.127:9092"  # IP của máy Kafka
```

#### 3.3.3. Kiến trúc Spark Streaming

**Input:**
- Kafka topic: `house-prices-input`
- Format: JSON với schema định nghĩa sẵn

**Output:**
- Kafka topic: `house-prices-output`
- Format: JSON chứa id, actual_price, predicted_price, error, error_percentage

#### 3.3.4. Schema dữ liệu

```python
schema = StructType([
    StructField("id", IntegerType(), True),
    StructField("MedInc", DoubleType(), True),
    StructField("HouseAge", DoubleType(), True),
    StructField("AveRooms", DoubleType(), True),
    StructField("AveBedrms", DoubleType(), True),
    StructField("Population", DoubleType(), True),
    StructField("AveOccup", DoubleType(), True),
    StructField("Latitude", DoubleType(), True),
    StructField("Longitude", DoubleType(), True),
    StructField("actual_price", DoubleType(), True)
])
```

#### 3.3.5. Quy trình xử lý

```python
# 1. Khởi tạo Spark Session với HDFS
spark = SparkSession.builder \
    .appName("HousePriceStreamingPrediction") \
    .config("spark.hadoop.fs.defaultFS", HDFS_NAMENODE) \
    .config("spark.hadoop.fs.hdfs.impl", "org.apache.hadoop.hdfs.DistributedFileSystem") \
    .getOrCreate()

# 2. Load mô hình từ HDFS
model = PipelineModel.load(HDFS_MODEL_PATH)

# 3. Đọc stream từ Kafka
df_stream = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
    .option("subscribe", "house-prices-input") \
    .option("startingOffsets", "earliest") \
    .load()

# 4. Parse JSON và dự đoán
df_parsed = df_stream.select(
    from_json(col("value").cast("string"), schema).alias("data")
).select("data.*")

predictions = model.transform(df_parsed)

# 5. Tính toán metrics và gửi về Kafka
result = predictions.select(
    col("id"),
    col("actual_price"),
    col("prediction").alias("predicted_price"),
    (col("prediction") - col("actual_price")).alias("error"),
    ((col("prediction") - col("actual_price")) / col("actual_price") * 100).alias("error_percentage")
)

kafka_output = result.select(to_json(struct("*")).alias("value"))

query = kafka_output.writeStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
    .option("topic", "house-prices-output") \
    .option("checkpointLocation", "/tmp/checkpoint-house-prices-output") \
    .start()
```

#### 3.3.6. Tính năng đặc biệt

**Timeout mechanism:**
- Streaming job tự động dừng sau 120 giây (2 phút)
- Đảm bảo job không chạy vô hạn trong môi trường production

**Checkpoint:**
- Sử dụng checkpoint để đảm bảo exactly-once semantics
- Lưu tại `/tmp/checkpoint-house-prices-output`

**Console output:**
- Hiển thị kết quả dự đoán trên console để debug
- Format: append mode với truncate=False

**Model loading:**
- Load trực tiếp từ HDFS path
- Có fallback về local path nếu HDFS không khả dụng

---

### 3.4. Kafka Producer (`streaming/kafka_producer.py`)

#### 3.4.1. Mục đích
Mô phỏng nguồn dữ liệu streaming bằng cách đọc dữ liệu từ HDFS và gửi vào Kafka topic.

#### 3.4.2. Đọc dữ liệu từ HDFS

```python
def read_from_hdfs(hdfs_path):
    """Download file từ HDFS về local tạm và đọc bằng pandas"""
    # Tạo file tạm với UUID unique
    temp_path = os.path.join(tempfile.gettempdir(), f"hdfs_streaming_{uuid.uuid4().hex}.csv")
    
    # Download từ HDFS
    cmd = ['hdfs', 'dfs', '-get', '-f', hdfs_path, temp_path]
    result = subprocess.run(cmd, ...)
    
    # Đọc CSV bằng pandas
    df = pd.read_csv(temp_path)
    
    # Cleanup file tạm
    os.unlink(temp_path)
    return df
```

#### 3.4.3. Chức năng chính

```python
def send_streaming_data(interval=2, num_records=None):
    # Đọc dữ liệu từ HDFS
    hdfs_namenode = os.getenv("HDFS_NAMENODE", "hdfs://worker1:8020")
    hdfs_data_path = os.getenv(
        "HDFS_STREAMING_DATA_PATH",
        f"{hdfs_namenode}/bigdata/house_prices/streaming_data.csv"
    )
    
    df = read_from_hdfs(hdfs_data_path)
    
    # Tạo producer
    producer = create_producer()  # Kết nối đến localhost:9092 trên máy Kafka
    
    # Gửi từng record
    for idx, row in df.iterrows():
        message = {
            'id': idx,
            'MedInc': float(row['MedInc']),
            # ... các trường khác
            'actual_price': float(row['target'])
        }
        producer.send('house-prices-input', value=message)
        time.sleep(interval)
```

#### 3.4.4. Tính năng

**Retry logic:**
- Tự động retry kết nối đến Kafka nếu chưa sẵn sàng
- Max retries: 10 lần với delay 5 giây

**Cấu hình:**
- **Kafka Bootstrap**: `localhost:9092` (chạy trên máy Kafka)
- **Topic**: `house-prices-input`
- **HDFS Path**: Có thể override qua `HDFS_STREAMING_DATA_PATH`

**Tham số dòng lệnh:**
- `interval`: Khoảng thời gian giữa các message (mặc định: 2 giây)
- `num_records`: Số lượng records gửi (mặc định: tất cả)

---

### 3.5. Kafka Consumer & Visualization (`visualization/kafka_consumer.py`)

#### 3.5.1. Mục đích
Đọc kết quả dự đoán từ Kafka và hiển thị trực quan hóa real-time.

#### 3.5.2. Cấu hình

```python
KAFKA_BOOTSTRAP_SERVERS = "192.168.80.127:9092"  # IP của máy Kafka
```

#### 3.5.3. Kiến trúc Visualization

**Class: `RealtimeVisualizer`**

**Thành phần:**
- **Data structures**: Sử dụng `deque` với max length để lưu trữ dữ liệu
- **Matplotlib**: Hiển thị biểu đồ với animation
- **Kafka Consumer**: Đọc từ topic `house-prices-output`

#### 3.5.4. Biểu đồ hiển thị

**Plot 1: Actual vs Predicted Prices**
- Line chart so sánh giá thực tế và giá dự đoán
- X-axis: Sample Index
- Y-axis: Price ($1000s)
- Legend: Actual Price (blue), Predicted Price (red)

**Plot 2: Prediction Error**
- Bar chart hiển thị sai số tuyệt đối
- X-axis: Sample Index
- Y-axis: Absolute Error ($1000s)
- Color: Coral với alpha=0.7

**Metrics display:**
- MAE (Mean Absolute Error)
- RMSE (Root Mean Squared Error)
- Số lượng samples đã xử lý

#### 3.5.5. Tính năng

**Real-time updates:**
- Cập nhật biểu đồ mỗi 1 giây
- Sử dụng `FuncAnimation` từ matplotlib

**Data management:**
- Giới hạn số điểm hiển thị (max_points=100)
- Sử dụng deque để tự động loại bỏ dữ liệu cũ

**Error handling:**
- Validate message structure trước khi xử lý
- Continue khi có lỗi thay vì crash

---

### 3.6. Web UI (`ui.py`, `predict_service.py`)

#### 3.6.1. Mục đích
Cung cấp giao diện web để người dùng nhập dữ liệu và nhận kết quả dự đoán real-time.

#### 3.6.2. `predict_service.py`

**Hỗ trợ load model từ HDFS hoặc local:**

```python
class HousePricePredictor:
    def __init__(self, model_path=None):
        # Tự động detect: HDFS path hoặc local path
        if model_path.startswith('hdfs://'):
            # Download từ HDFS về local tạm
            local_model_path = self._download_from_hdfs(model_path)
        else:
            local_model_path = model_path
        
        # Spark session với file:// filesystem
        self.spark = SparkSession.builder \
            .config("spark.hadoop.fs.defaultFS", "file:///") \
            .getOrCreate()
        
        # Load model từ local path (với file:// prefix)
        self.model = PipelineModel.load(f"file://{os.path.abspath(local_model_path)}")
```

**Tính năng:**
- Tự động detect model path từ environment variables
- Hỗ trợ download model từ HDFS về local tạm
- Fallback về local path nếu HDFS không khả dụng
- Tự động cleanup thư mục tạm khi đóng

#### 3.6.3. `ui.py`

**Flask Web Application:**
- Route `/`: Form nhập liệu
- Route `/predict`: API endpoint để dự đoán
- Route `/health`: Health check endpoint

**Tính năng:**
- Form validation
- JSON API support
- Error handling
- Loading states

#### 3.6.4. `templates/index.html`

**Giao diện người dùng:**
- Form nhập 8 đặc trưng của nhà
- Real-time prediction
- Hiển thị kết quả với formatting đẹp
- Responsive design

---

### 3.7. Airflow Orchestration

#### 3.7.1. Kiến trúc Celery/RabbitMQ

**Thay vì SSH, hệ thống sử dụng:**
- **RabbitMQ**: Message broker chạy trên máy Airflow
- **Celery**: Distributed task queue
- **Celery Workers**: Chạy trên từng máy (Kafka, Spark, Hadoop) và listen trên queues riêng

**Queue mapping:**
- `node_57`: Queue cho máy Kafka và Hadoop
- `spark`: Queue cho máy Spark

**Lợi ích:**
- Không cần SSH keys
- Dễ dàng scale thêm workers
- Centralized message broker
- Better error handling và retry logic

#### 3.7.2. DAG: `train_model_pipeline_fixed`

**Mục đích:** Điều phối quá trình huấn luyện mô hình từ đầu đến cuối.

**Các phases:**

**Phase 1: Stop all services**
- `send_kafka_stop` → `wait_kafka_stop`
- `send_spark_stop` → `wait_spark_stop`
- `send_hadoop_stop` → `wait_hadoop_stop`

**Phase 2: Start all services**
- `send_kafka_start` → `wait_kafka_ready` (với health check)
- `send_spark_start` → `wait_spark_ready` (với health check)
- `send_hadoop_start` → `wait_hadoop_ready` (với health check)

**Phase 3: Data preparation**
- `prepare_data`: Chạy `data/prepare_data.py`
- `send_disable_safemode` → `wait_disable_safemode`: Tắt HDFS safe mode
- `send_upload_hdfs` → `wait_upload_hdfs`: Upload data lên HDFS và verify

**Phase 4: Training**
- `notify_training_start`: Gửi message qua RabbitMQ
- `send_train_model` → `wait_train_model`: Submit Spark job để train
- `notify_training_complete`: Gửi message hoàn thành

**Health checks:**
- `check_kafka_health`: Kiểm tra Kafka broker port 9092
- `check_spark_health`: Kiểm tra Spark Master port 7077 và Web UI port 8080
- `check_hdfs_health`: Kiểm tra HDFS Namenode port 8020

**Spark submission:**
```bash
~/spark-4.0.0-bin-hadoop3/bin/spark-submit \
  --master spark://worker3:7077 \
  --deploy-mode client \
  --conf spark.hadoop.fs.defaultFS=hdfs://192.168.80.127:8020 \
  spark_jobs/train_model.py
```

#### 3.7.3. DAG: `predict_streaming_pipeline`

**Mục đích:** Điều phối quá trình streaming prediction.

**Các phases:**

**Phase 1: Stop all services** (giống train_dag)

**Phase 2: Start all services** (giống train_dag)

**Phase 3: Ensure Kafka topics**
- `ensure_kafka_topics` → `wait_kafka_topics`: Tạo topics `house-prices-input` và `house-prices-output`

**Phase 4: Prediction pipeline**
- `notify_prediction_start`: Gửi message
- `send_streaming_data` → `wait_streaming_data`: Gửi dữ liệu vào Kafka (đọc từ HDFS)
- `send_streaming_job` → `wait_streaming_job`: Submit Spark Streaming job
- `notify_prediction_complete`: Gửi message hoàn thành

**Spark Streaming submission:**
```bash
~/spark-4.0.0-bin-hadoop3/bin/spark-submit \
  --master spark://worker3:7077 \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.0 \
  --conf spark.hadoop.fs.defaultFS=hdfs://worker1:8020 \
  spark_jobs/streaming_predict.py
```

#### 3.7.4. Celery Tasks (`mycelery/system_worker.py`)

**Các tasks chính:**

1. **`run_command`**: Chạy shell command trên worker machine
2. **`docker_compose_up/down`**: Quản lý Docker containers (cho Kafka)
3. **`check_kafka_health`**: Health check Kafka broker
4. **`check_spark_health`**: Health check Spark Master (RPC port 7077 và Web UI port 8080)
5. **`check_hdfs_health`**: Health check HDFS Namenode (port 8020)
6. **`verify_hdfs_file`**: Verify file tồn tại trên HDFS

**Health check improvements:**
- `check_spark_health` kiểm tra cả RPC port và Web UI port
- Parse HTML từ Web UI để lấy số lượng workers
- Trả về thông tin chi tiết về cluster status

---

## 4. LUỒNG XỬ LÝ DỮ LIỆU

### 4.1. Luồng tổng quan

```
1. Airflow DAG được trigger
   ↓
2. Khởi động Kafka cluster (Machine Kafka) - Qua Celery
   ↓
3. Khởi động Spark cluster (Machine Spark) - Qua Celery
   ↓
4. Khởi động HDFS (Machine Hadoop) - Qua Celery
   ↓
5. Chuẩn bị dữ liệu (chia train/streaming)
   ↓
6. Upload dữ liệu lên HDFS
   ↓
7. Huấn luyện mô hình Random Forest (Spark ML)
   ↓
8. Lưu mô hình vào HDFS: hdfs://worker1:8020/bigdata/model
   ↓
9. Producer đọc streaming data từ HDFS và gửi vào Kafka
   ↓
10. Spark Streaming đọc từ Kafka, load model từ HDFS, dự đoán
   ↓
11. Gửi kết quả vào Kafka topic: house-prices-output
   ↓
12. Consumer đọc kết quả và hiển thị visualization
```

### 4.2. Luồng dữ liệu chi tiết

**Stage 1: Data Preparation**
```
California Housing Dataset
    ↓
prepare_data.py
    ↓
train_data.csv (80%)    streaming_data.csv (20%)
    ↓
upload_to_hdfs.py
    ↓
HDFS: /bigdata/house_prices/train_data.csv
HDFS: /bigdata/house_prices/streaming_data.csv
```

**Stage 2: Model Training**
```
HDFS: /bigdata/house_prices/train_data.csv
    ↓
Spark ML Pipeline (train_model.py)
    ├── VectorAssembler
    └── RandomForestRegressor
    ↓
Trained Model
    ↓
HDFS: /bigdata/model
```

**Stage 3: Streaming Prediction**
```
HDFS: /bigdata/house_prices/streaming_data.csv
    ↓
kafka_producer.py (đọc từ HDFS)
    ↓
Kafka Topic: house-prices-input
    ↓
Spark Streaming (streaming_predict.py)
    ├── Load Model từ HDFS: /bigdata/model
    ├── Parse JSON từ Kafka
    ├── Predict
    └── Calculate Metrics
    ↓
Kafka Topic: house-prices-output
    ↓
kafka_consumer.py
    ↓
Real-time Visualization
```

**Stage 4: Web UI Prediction**
```
User Input (Web Form)
    ↓
ui.py → predict_service.py
    ├── Load Model từ HDFS (download về local tạm)
    ├── Predict
    └── Return Result
    ↓
Web UI Display
```

### 4.3. Data formats

**Input to Kafka (house-prices-input):**
```json
{
  "id": 0,
  "MedInc": 8.3252,
  "HouseAge": 41.0,
  "AveRooms": 6.984127,
  "AveBedrms": 1.023810,
  "Population": 322.0,
  "AveOccup": 2.555556,
  "Latitude": 37.88,
  "Longitude": -122.23,
  "actual_price": 4.526
}
```

**Output from Kafka (house-prices-output):**
```json
{
  "id": 0,
  "actual_price": 4.526,
  "predicted_price": 4.4523,
  "error": -0.0737,
  "error_percentage": -1.63
}
```

---

## 5. KẾT QUẢ VÀ ĐÁNH GIÁ

### 5.1. Metrics mô hình

Sau khi huấn luyện, mô hình Random Forest được đánh giá bằng các metrics:
- **RMSE**: Root Mean Squared Error (càng thấp càng tốt)
- **MAE**: Mean Absolute Error (càng thấp càng tốt)
- **R²**: Coefficient of Determination (càng gần 1 càng tốt)

### 5.2. Streaming performance

**Throughput:**
- Producer gửi với interval 1-2 giây/record
- Spark Streaming xử lý real-time với latency thấp
- Consumer hiển thị kết quả với update rate 1 giây

**Scalability:**
- Hệ thống hỗ trợ distributed processing
- Spark cluster có thể scale thêm workers
- Kafka hỗ trợ multiple partitions và replication

### 5.3. Visualization insights

**Biểu đồ hiển thị:**
- So sánh trực quan giữa giá thực tế và giá dự đoán
- Phân tích sai số dự đoán theo từng sample
- Metrics tổng hợp (MAE, RMSE) được cập nhật real-time

### 5.4. Độ tin cậy hệ thống

**Fault tolerance:**
- Kafka checkpoint đảm bảo exactly-once semantics
- Spark Streaming có khả năng recover từ checkpoint
- Airflow retry logic cho các tasks
- Celery task retry và error handling

**Error handling:**
- Producer có retry logic khi Kafka chưa sẵn sàng
- Spark Streaming có failOnDataLoss=false để tránh crash
- Airflow có cleanup tasks để dọn dẹp resources
- Health checks đảm bảo services sẵn sàng trước khi sử dụng

---

## 6. KẾT LUẬN

### 6.1. Thành tựu đạt được

1. **Xây dựng thành công pipeline ML streaming end-to-end**
   - Từ chuẩn bị dữ liệu đến visualization
   - Tự động hóa hoàn toàn với Airflow
   - Hỗ trợ HDFS cho data và model storage

2. **Triển khai trên kiến trúc phân tán**
   - 3 máy riêng biệt cho các services
   - Distributed processing với Spark cluster
   - Centralized orchestration với Airflow + Celery

3. **Real-time prediction**
   - Streaming data processing với Spark Structured Streaming
   - Low latency prediction pipeline
   - Model được load từ HDFS

4. **Visualization real-time**
   - Biểu đồ cập nhật liên tục
   - Metrics được tính toán và hiển thị động

5. **Web UI**
   - Giao diện web để dự đoán real-time
   - Hỗ trợ load model từ HDFS hoặc local
   - User-friendly interface

### 6.2. Công nghệ sử dụng

- **Apache Spark 4.0.0**: Distributed computing và ML
- **Apache Kafka**: Message queue cho streaming
- **Apache Airflow**: Workflow orchestration
- **RabbitMQ + Celery**: Distributed task queue
- **HDFS**: Distributed file system cho data và model storage
- **Python**: Ngôn ngữ lập trình chính
- **Matplotlib**: Visualization
- **Flask**: Web framework
- **Docker**: Containerization cho Kafka

### 6.3. Cấu hình hệ thống

**HDFS:**
- Namenode: `hdfs://worker1:8020` (hoặc `hdfs://192.168.80.127:8020`)
- Web UI: `http://worker1:9870`
- Data path: `/bigdata/house_prices/`
- Model path: `/bigdata/model`

**Kafka:**
- Bootstrap servers: `192.168.80.127:9092` (từ máy Spark)
- Bootstrap servers: `localhost:9092` (trên máy Kafka)
- Topics: `house-prices-input`, `house-prices-output`

**Spark:**
- Master: `spark://worker3:7077`
- Installation: `/home/nindang/spark-4.0.0-bin-hadoop3`
- Start script: `~/spark-4.0.0-bin-hadoop3/sbin/start-all.sh`
- Stop script: `~/spark-4.0.0-bin-hadoop3/sbin/stop-all.sh`

**RabbitMQ/Celery:**
- Broker: `amqp://guest:guest@master:5672//`
- Backend: `db+postgresql://airflow:airflow@master/airflow`
- Queues: `node_57` (Kafka/Hadoop), `spark` (Spark)

### 6.4. Ứng dụng thực tế

Hệ thống này có thể được áp dụng cho:
- **Real-time price prediction**: Dự đoán giá nhà, giá cổ phiếu
- **IoT data processing**: Xử lý dữ liệu từ sensors
- **Recommendation systems**: Hệ thống gợi ý real-time
- **Fraud detection**: Phát hiện gian lận trong giao dịch

### 6.5. Hạn chế và cải thiện

**Hạn chế hiện tại:**
- Model được huấn luyện offline, chưa có online learning
- Visualization chỉ hiển thị trên local machine
- Chưa có monitoring và alerting system
- Web UI chỉ hỗ trợ single prediction, chưa có batch prediction

**Hướng cải thiện:**
- Thêm model versioning và A/B testing
- Triển khai visualization trên web dashboard
- Tích hợp monitoring tools (Prometheus, Grafana)
- Thêm data validation và quality checks
- Implement model retraining pipeline tự động
- Thêm authentication và authorization cho Web UI
- Optimize HDFS model loading (caching)

### 6.6. Kết luận

Dự án đã thành công xây dựng một hệ thống Machine Learning streaming hoàn chỉnh với các công nghệ Big Data hiện đại. Hệ thống có khả năng xử lý dữ liệu real-time, scale được và có độ tin cậy cao. Việc sử dụng Celery/RabbitMQ thay vì SSH giúp hệ thống linh hoạt và dễ quản lý hơn. Đây là một foundation tốt để phát triển các ứng dụng ML production-ready.

---

## PHỤ LỤC

### A. Cấu trúc thư mục dự án

```
final_project/
├── dags/
│   ├── train_dag.py              # Training pipeline DAG
│   └── predict_dag.py            # Streaming prediction DAG
├── data/
│   ├── prepare_data.py           # Chia dữ liệu train/streaming
│   ├── upload_to_hdfs.py         # Upload data lên HDFS
│   ├── train_data.csv            # Dữ liệu huấn luyện
│   └── streaming_data.csv        # Dữ liệu streaming
├── spark_jobs/
│   ├── train_model.py            # Huấn luyện mô hình Spark ML
│   └── streaming_predict.py      # Spark Streaming dự đoán
├── streaming/
│   └── kafka_producer.py         # Producer đọc từ HDFS và gửi vào Kafka
├── visualization/
│   └── kafka_consumer.py         # Consumer và trực quan hóa kết quả
├── mycelery/
│   └── system_worker.py          # Celery workers cho remote execution
├── utils/
│   └── rabbitmq_client.py        # RabbitMQ client utilities
├── templates/
│   └── index.html                # Web UI template
├── ui.py                         # Flask Web UI
├── predict_service.py            # Prediction service (hỗ trợ HDFS)
├── requirements.txt              # Python dependencies
└── README.md                     # Hướng dẫn sử dụng
```

### B. Dependencies chính

**Python packages:**
- `pyspark==4.0.0`
- `kafka-python`
- `pandas`
- `scikit-learn`
- `matplotlib`
- `apache-airflow==2.7.0`
- `celery`
- `pika` (RabbitMQ client)
- `flask`

**Spark packages:**
- `org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.0`

### C. Cấu hình hệ thống chi tiết

**HDFS:**
- Namenode: `hdfs://worker1:8020` hoặc `hdfs://192.168.80.127:8020`
- Web UI: `http://worker1:9870`
- RPC Port: 8020
- Data directory: `/bigdata/house_prices/`
- Model path: `/bigdata/model`

**Kafka:**
- Bootstrap servers: `192.168.80.127:9092` (từ máy Spark)
- Bootstrap servers: `localhost:9092` (trên máy Kafka)
- Topics: 
  - `house-prices-input` (input cho Spark Streaming)
  - `house-prices-output` (output từ Spark Streaming)

**Spark:**
- Master: `spark://worker3:7077`
- Web UI: `http://worker3:8080`
- Installation path: `/home/nindang/spark-4.0.0-bin-hadoop3`
- Start command: `~/spark-4.0.0-bin-hadoop3/sbin/start-all.sh`
- Stop command: `~/spark-4.0.0-bin-hadoop3/sbin/stop-all.sh`

**RabbitMQ/Celery:**
- Broker URL: `amqp://guest:guest@master:5672//`
- Result Backend: `db+postgresql://airflow:airflow@master/airflow`
- Queues:
  - `node_57`: Cho máy Kafka và Hadoop
  - `spark`: Cho máy Spark

**Airflow:**
- Web server port: 8080
- DAGs:
  - `train_model_pipeline_fixed`: Training pipeline
  - `predict_streaming_pipeline`: Streaming prediction pipeline

### D. Environment Variables

**Cho Spark jobs:**
- `HDFS_NAMENODE`: HDFS Namenode URL (default: `hdfs://worker1:8020`)
- `HDFS_TRAIN_DATA_PATH`: Full path đến training data trên HDFS
- `HDFS_MODEL_PATH`: Full path đến model trên HDFS
- `HDFS_STREAMING_DATA_PATH`: Full path đến streaming data trên HDFS
- `KAFKA_BOOTSTRAP_SERVERS`: Kafka bootstrap servers
- `SPARK_HOST`: Hostname của máy Spark
- `PYTHONUNBUFFERED`: Set to `1` để unbuffer output

**Cho Web UI:**
- `MODEL_PATH`: Path đến model (HDFS hoặc local)
- `HDFS_NAMENODE`: HDFS Namenode để download model
- `HDFS_MODEL_PATH`: Full path đến model trên HDFS

---

**Tài liệu được cập nhật:** 2025-12-22  
**Phiên bản:** 2.0  
**Trạng thái:** Production-ready với HDFS integration và Celery/RabbitMQ architecture
