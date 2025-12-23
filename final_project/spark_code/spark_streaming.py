"""
Spark Streaming Job - Real-time House Price Prediction
Đọc từ Kafka topic house_input, predict với model từ HDFS, ghi vào house_prediction
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, struct, to_json
from pyspark.sql.types import StructType, StructField, DoubleType, StringType
from pyspark.ml import PipelineModel
import sys

# Configuration
KAFKA_BROKER = "192.168.80.51:9092"
INPUT_TOPIC = "house_input"
OUTPUT_TOPIC = "house_prediction"
HDFS_NAMENODE = "hdfs://192.168.80.178:8020"
MODEL_PATH = f"{HDFS_NAMENODE}/bigdata/house_prices/model"

def log(msg):
    """Log with flush"""
    print(msg, flush=True)
    sys.stdout.flush()

def main():
    log("=" * 60)
    log("SPARK STREAMING - REAL-TIME PREDICTION")
    log("=" * 60)
    log(f"Kafka Broker: {KAFKA_BROKER}")
    log(f"Input Topic: {INPUT_TOPIC}")
    log(f"Output Topic: {OUTPUT_TOPIC}")
    log(f"Model Path: {MODEL_PATH}")
    
    # Create Spark session
    log("\n[1/5] Creating Spark session...")
    spark = SparkSession.builder \
        .appName("HousePricePredictionStreaming") \
        .config("spark.hadoop.fs.defaultFS", HDFS_NAMENODE) \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    log("✓ Spark session created")
    
    # Load model from HDFS
    log(f"\n[2/5] Loading model from HDFS: {MODEL_PATH}")
    try:
        model = PipelineModel.load(MODEL_PATH)
        log("✓ Model loaded successfully")
    except Exception as e:
        log(f"❌ Failed to load model: {e}")
        spark.stop()
        sys.exit(1)
    
    # Define schema for input data (adjust based on your CSV columns)
    log("\n[3/5] Defining input schema...")
    # Schema should match your training data columns (excluding price)
    input_schema = StructType([
        StructField("f_4012", DoubleType(), True),
        StructField("f_3", DoubleType(), True),
        StructField("f_12", DoubleType(), True),
        StructField("f_2016", DoubleType(), True),
        StructField("f_2_09809241489216", DoubleType(), True),
        StructField("f_15", DoubleType(), True),
        StructField("f_5", DoubleType(), True),
    ])
    
    # Read from Kafka
    log(f"\n[4/5] Reading from Kafka topic: {INPUT_TOPIC}")
    df_stream = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BROKER) \
        .option("subscribe", INPUT_TOPIC) \
        .option("startingOffsets", "latest") \
        .load()
    
    log("✓ Connected to Kafka stream")
    
    # Parse JSON from Kafka
    df_parsed = df_stream.select(
        from_json(col("value").cast("string"), input_schema).alias("data")
    ).select("data.*")
    
    # Make predictions
    log("\n[5/5] Starting prediction stream...")
    df_predictions = model.transform(df_parsed)
    
    # Prepare output (features + prediction)
    df_output = df_predictions.select(
        to_json(struct("*")).alias("value")
    )
    
    # Write to Kafka output topic
    query = df_output \
        .writeStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BROKER) \
        .option("topic", OUTPUT_TOPIC) \
        .option("checkpointLocation", "/tmp/spark_streaming_checkpoint") \
        .outputMode("append") \
        .start()
    
    log("✓ Streaming started!")
    log(f"\n{'='*60}")
    log("STREAMING JOB IS RUNNING")
    log(f"{'='*60}")
    log(f"Reading from: {INPUT_TOPIC}")
    log(f"Writing to: {OUTPUT_TOPIC}")
    log("Press Ctrl+C to stop")
    log(f"{'='*60}\n")
    
    # Wait for termination
    query.awaitTermination()

if __name__ == "__main__":
    main()
