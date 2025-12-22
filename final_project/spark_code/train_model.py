"""
Spark ML job để huấn luyện mô hình Random Forest
Đọc dữ liệu từ HDFS và lưu model lên HDFS
"""
from pyspark.sql import SparkSession
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.regression import RandomForestRegressor
from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml import Pipeline
import os
import sys
import time

# Cấu hình HDFS và Spark - NEW ARCHITECTURE
HDFS_NAMENODE = "hdfs://192.168.80.178:8020"
HDFS_TRAIN_DATA_PATH = f"{HDFS_NAMENODE}/bigdata/house_prices/train_data.csv"
HDFS_MODEL_PATH = f"{HDFS_NAMENODE}/bigdata/house_prices/model"

def log(msg):
    """Log với flush ngay để xem progress"""
    print(msg, flush=True)
    sys.stdout.flush()

def train_model():
    log("=" * 60)
    log("BẮT ĐẦU HUẤN LUYỆN MÔ HÌNH")
    log("=" * 60)
    log(f"HDFS Namenode: {HDFS_NAMENODE}")
    log(f"HDFS Train Data: {HDFS_TRAIN_DATA_PATH}")
    log(f"HDFS Model Path: {HDFS_MODEL_PATH}")
    
    # Create Spark session
    log("\n[STEP 1/7] Creating Spark session...")
    spark = SparkSession.builder \
        .appName("HousePriceModelTraining") \
        .config("spark.hadoop.fs.defaultFS", HDFS_NAMENODE) \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("ERROR")
    log(f"✓ Spark Session created. App ID: {spark.sparkContext.applicationId}")
    
    # Đọc dữ liệu từ HDFS
    log(f"\n[STEP 2/7] 📂 Đọc dữ liệu từ HDFS: {HDFS_TRAIN_DATA_PATH}")
    try:
        df = spark.read.csv(HDFS_TRAIN_DATA_PATH, header=True, inferSchema=True)
        log("✓ Đã load DataFrame")
    except Exception as e:
        log(f"❌ Lỗi khi đọc dữ liệu: {e}")
        spark.stop()
        sys.exit(1)
    
    # BƯỚC 1: Chuẩn hóa tên cột
    from pyspark.sql.functions import col as spark_col
    
    log("\nChuẩn hóa tên cột...")
    for c in df.columns:
        new_c = c.strip()
        new_c = new_c.replace(".", "_")
        new_c = new_c.replace(" ", "_")
        new_c = new_c.replace("-", "_")
        
        if new_c and new_c[0].isdigit():
            new_c = "f_" + new_c
        
        if new_c != c:
            df = df.withColumnRenamed(c, new_c)
    
    log("✓ Tên cột sau khi chuẩn hóa:")
    log(str(df.columns))
    
    # BƯỚC 2: Xác định cột label (price)
    if "price" in df.columns:
        label_col = "price"
        log("✓ Tìm thấy cột 'price'")
    else:
        # CSV không có header đúng, dùng cột cuối làm target
        label_col = df.columns[-1]
        log(f"⚠️  Không tìm thấy cột 'price', dùng cột cuối làm target: {label_col}")
        # Rename cột cuối thành 'price' để code phía sau dùng
        df = df.withColumnRenamed(label_col, "price")
        label_col = "price"
        log("✓ Đã rename cột target thành 'price'")
    
    log(f"✓ Label column: {label_col}")
    
    # Đếm số mẫu
    log(f"\n[STEP 3/7] Đếm số mẫu...")
    try:
        num_samples = df.count()
        log(f"✓ Đã đọc {num_samples} mẫu")
    except Exception as e:
        log(f"❌ Lỗi khi đếm: {e}")
        spark.stop()
        sys.exit(1)
    
    log("\nSchema:")
    df.printSchema()
    
    # BƯỚC 3: Chỉ lấy feature là số (numeric types)
    from pyspark.sql.types import NumericType
    
    feature_cols = [
        f.name for f in df.schema.fields
        if f.name != "price" and isinstance(f.dataType, NumericType)
    ]
    
    log(f"\nFeature columns ({len(feature_cols)}): {feature_cols}")
    
    assembler = VectorAssembler(
        inputCols=feature_cols,
        outputCol="features"
    )
    
    # Random Forest model
    rf = RandomForestRegressor(
        featuresCol="features",
        labelCol="price",
        numTrees=100,
        maxDepth=10,
        seed=42
    )
    
    # Pipeline
    pipeline = Pipeline(stages=[assembler, rf])
    
    # Chia train/test 80/20
    log(f"\n[STEP 4/7] Chia dữ liệu train/test (80/20)...")
    train_data, test_data = df.randomSplit([0.8, 0.2], seed=42)
    
    train_count = train_data.count()
    test_count = test_data.count()
    log(f"✓ Train samples: {train_count}")
    log(f"✓ Test samples: {test_count}")
    
    # Training
    log("\n[STEP 5/7] 🔄 Training Random Forest model...")
    log(f"   Trees: 100, Max depth: 10")
    log("   ⏳ Bắt đầu training (có thể mất vài phút)...")
    
    fit_start = time.time()
    try:
        model = pipeline.fit(train_data)
        fit_time = time.time() - fit_start
        log(f"✓ Training hoàn thành! ({fit_time:.2f}s)")
    except Exception as e:
        log(f"❌ Lỗi khi training: {e}")
        spark.stop()
        sys.exit(1)
    
    # Evaluation
    log("\n[STEP 6/7] Đánh giá mô hình...")
    predictions = model.transform(test_data)
    
    evaluator_rmse = RegressionEvaluator(
        labelCol="price",
        predictionCol="prediction",
        metricName="rmse"
    )
    
    evaluator_r2 = RegressionEvaluator(
        labelCol="price",
        predictionCol="prediction",
        metricName="r2"
    )
    
    evaluator_mae = RegressionEvaluator(
        labelCol="price",
        predictionCol="prediction",
        metricName="mae"
    )
    
    rmse = evaluator_rmse.evaluate(predictions)
    r2 = evaluator_r2.evaluate(predictions)
    mae = evaluator_mae.evaluate(predictions)
    
    log("\n" + "=" * 60)
    log("KẾT QUẢ ĐÁNH GIÁ MÔ HÌNH")
    log("=" * 60)
    log(f"RMSE: {rmse:.4f}")
    log(f"MAE:  {mae:.4f}")
    log(f"R²:   {r2:.4f}")
    log("=" * 60)
    
    # Lưu model lên HDFS
    log(f"\n[STEP 7/7] 💾 Lưu model lên HDFS: {HDFS_MODEL_PATH}")
    
    try:
        save_start = time.time()
        model.write().overwrite().save(HDFS_MODEL_PATH)
        save_time = time.time() - save_start
        log(f"✓ Đã lưu model vào HDFS ({save_time:.2f}s)")
    except Exception as e:
        log(f"❌ Lỗi khi lưu model: {e}")
        spark.stop()
        sys.exit(1)
    
    # Hiển thị một số predictions
    log("\nMột số dự đoán mẫu:")
    predictions.select("price", "prediction").show(10, truncate=False)
    
    log("\n✓ Dừng Spark Session...")
    spark.stop()
    
    log("\n" + "=" * 60)
    log("✓ HOÀN THÀNH HUẤN LUYỆN!")
    log("=" * 60)

if __name__ == "__main__":
    train_model()
