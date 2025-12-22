from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, to_json, struct
from pyspark.sql.types import StructType, StructField, IntegerType, DoubleType
from pyspark.ml import PipelineModel

import os

# --- CẤU HÌNH ---
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "192.168.80.51:29092")   # Nole2
INPUT_TOPIC = "house_input"
OUTPUT_TOPIC = "house_prediction"
NAMENODE_IP = os.getenv("NAMENODE_IP", "192.168.80.178")         # Nole3
MODEL_PATH = f"hdfs://{NAMENODE_IP}:9000/user/project/final/model/house_price_model"

# --- CẬP NHẬT IP MỚI CỦA NOLE1 ---
SPARK_MASTER_IP = os.getenv("SPARK_MASTER_IP", "192.168.80.165")    # Nole1

def main():
    # Auto-detect driver IP (máy đang chạy script này)
    import socket
    driver_ip = socket.gethostbyname(socket.gethostname())
    
    # Kết nối về Spark Master
    spark = SparkSession.builder \
        .appName("HousePriceStreaming") \
        .master(f"spark://{SPARK_MASTER_IP}:7077") \
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.0") \
        .config("spark.driver.host", driver_ip) \
        .config("spark.driver.bindAddress", "0.0.0.0") \
        .config("spark.sql.shuffle.partitions", "2") \
        .getOrCreate()
    
    print(f">>> Driver IP: {driver_ip}, Spark Master: {SPARK_MASTER_IP}")
    
    spark.sparkContext.setLogLevel("WARN")

    # (Các phần dưới giữ nguyên không đổi)
    print(f">>> Đang tải Model từ HDFS: {MODEL_PATH}")
    try:
        model = PipelineModel.load(MODEL_PATH)
        print(">>> Tải Model thành công!")
    except Exception as e:
        print(f"LỖI TẢI MODEL: {e}")
        return

    print(f">>> Đang kết nối Kafka Input ({INPUT_TOPIC})...")
    df_raw = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BROKER) \
        .option("subscribe", INPUT_TOPIC) \
        .option("startingOffsets", "latest") \
        .load()

    schema = StructType([
        StructField("Square_Footage", IntegerType()),
        StructField("Num_Bedrooms", IntegerType()),
        StructField("Num_Bathrooms", IntegerType()),
        StructField("Year_Built", IntegerType()),
        StructField("Lot_Size", DoubleType()),
        StructField("Garage_Size", IntegerType()),
        StructField("Neighborhood_Quality", IntegerType()),
        StructField("House_Price", DoubleType())  # Thêm cột giá thực tế để so sánh
    ])

    df_parsed = df_raw.select(from_json(col("value").cast("string"), schema).alias("data")).select("data.*")

    predictions = model.transform(df_parsed)

    kafka_output = predictions.select(to_json(struct("*")).alias("value"))

    print(f">>> Đang chuyển tiếp kết quả sang Topic: {OUTPUT_TOPIC}")
    
    query = kafka_output.writeStream \
        .outputMode("append") \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BROKER) \
        .option("topic", OUTPUT_TOPIC) \
        .option("checkpointLocation", "/tmp/spark_checkpoint_cluster_final_v2") \
        .start()

    print(f">>> MASTER ĐANG CHẠY TẠI: {SPARK_MASTER_IP}")
    query.awaitTermination()

if __name__ == "__main__":
    main()
