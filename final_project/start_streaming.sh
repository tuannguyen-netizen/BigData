#!/bin/bash
# Start Spark Streaming Job - Fixed for Spark 4.0.1

echo "Starting Spark Streaming Job..."
echo "Spark Version: 4.0.1 (Scala 2.13)"
echo ""

~/spark/bin/spark-submit \
  --master spark://192.168.80.165:7077 \
  --deploy-mode client \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.0 \
  --conf spark.hadoop.fs.defaultFS=hdfs://192.168.80.178:8020 \
  --conf spark.driver.memory=2g \
  --conf spark.executor.memory=2g \
  ~/Tuan/Project/BigData/final_project/spark_code/spark_streaming.py
