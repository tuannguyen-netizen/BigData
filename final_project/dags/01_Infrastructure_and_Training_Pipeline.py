"""
Complete Training Pipeline DAG - Using Celery Workers
- Stop all services (Kafka, Spark, Hadoop) via Celery
- Start all services in order via Celery
- Upload training data to HDFS
- Train model with Spark
- Save model to HDFS
"""
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import time
from mycelery.system_worker import run_command, docker_compose_down, docker_compose_up

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

# Configuration
HDFS_NAMENODE = "hdfs://192.168.80.178:8020"
SPARK_MASTER = "spark://192.168.80.165:7077"
KAFKA_QUEUE = "nole2"
SPARK_QUEUE = "nole1"
HADOOP_QUEUE = "nole3"

def wait_for_task(result, timeout=300):
    """Wait for Celery task to complete"""
    elapsed = 0
    while elapsed < timeout:
        if result.ready():
            if result.successful():
                return result.result
            else:
                raise Exception(f"Task failed: {result.info}")
        time.sleep(2)
        elapsed += 2
    raise TimeoutError(f"Task timeout after {timeout}s")

with DAG(
    '01_Infrastructure_and_Training_Pipeline',
    default_args=default_args,
    description='Complete Infrastructure + Training Pipeline (Celery)',
    schedule=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['infrastructure', 'training', 'celery'],
) as dag:

    # ========================================
    # PHASE 1: STOP ALL SERVICES (via Celery)
    # ========================================
    
    def stop_kafka_task(**context):
        print("Stopping Kafka via Celery...")
        result = docker_compose_down.apply_async(
            args=["~/kafka_docker/docker-compose.yml"],
            queue=KAFKA_QUEUE
        )
        wait_for_task(result, timeout=60)
        print("✓ Kafka stopped")
    
    def stop_spark_task(**context):
        print("Stopping Spark via Celery...")
        result = run_command.apply_async(
            args=["~/spark/sbin/stop-all.sh"],
            queue=SPARK_QUEUE
        )
        wait_for_task(result, timeout=60)
        print("✓ Spark stopped")
    
    def stop_hadoop_task(**context):
        print("Stopping Hadoop via Celery...")
        result = run_command.apply_async(
            args=["~/hadoop/sbin/stop-dfs.sh"],
            queue=HADOOP_QUEUE
        )
        wait_for_task(result, timeout=60)
        print("✓ Hadoop stopped")
    
    stop_kafka = PythonOperator(task_id='stop_kafka', python_callable=stop_kafka_task)
    stop_spark = PythonOperator(task_id='stop_spark', python_callable=stop_spark_task)
    stop_hadoop = PythonOperator(task_id='stop_hadoop', python_callable=stop_hadoop_task)

    # ========================================
    # PHASE 2: START ALL SERVICES (via Celery)
    # ========================================
    
    def start_hadoop_task(**context):
        print("Starting Hadoop via Celery...")
        result = run_command.apply_async(
            args=["~/hadoop/sbin/start-dfs.sh"],
            queue=HADOOP_QUEUE
        )
        wait_for_task(result, timeout=120)
        time.sleep(10)
        
        # Disable safe mode
        result = run_command.apply_async(
            args=["~/hadoop/bin/hdfs dfsadmin -safemode leave"],
            queue=HADOOP_QUEUE
        )
        wait_for_task(result, timeout=30)
        print("✓ Hadoop started")
    
    def start_spark_task(**context):
        print("Starting Spark Master via Celery...")
        # Start Master
        result_master = run_command.apply_async(
            args=["~/spark/sbin/start-master.sh"],
            queue=SPARK_QUEUE
        )
        wait_for_task(result_master, timeout=60)
        time.sleep(10)

        print("Starting Spark Worker via Celery...")
        # Start Worker
        result_worker = run_command.apply_async(
            args=[f"~/spark/sbin/start-worker.sh {SPARK_MASTER}"],
            queue=SPARK_QUEUE
        )
        wait_for_task(result_worker, timeout=60)
        time.sleep(5)
        print("✓ Spark started (Master + Worker)")
    
    def start_kafka_task(**context):
        print("Starting Kafka via Celery...")
        result = docker_compose_up.apply_async(
            args=["~/kafka_docker/docker-compose.yml"],
            kwargs={"detach": True},
            queue=KAFKA_QUEUE
        )
        wait_for_task(result, timeout=120)
        time.sleep(10)
        print("✓ Kafka started")
    
    start_hadoop = PythonOperator(task_id='start_hadoop', python_callable=start_hadoop_task)
    start_spark = PythonOperator(task_id='start_spark', python_callable=start_spark_task)
    start_kafka = PythonOperator(task_id='start_kafka', python_callable=start_kafka_task)

    # ========================================
    # PHASE 3: UPLOAD DATA TO HDFS (via Celery)
    # ========================================
    
    def create_hdfs_dirs_task(**context):
        print("Creating HDFS directories via Celery...")
        commands = [
            "~/hadoop/bin/hdfs dfs -mkdir -p /bigdata/house_prices",
            "~/hadoop/bin/hdfs dfs -chmod -R 777 /bigdata/house_prices"
        ]
        for cmd in commands:
            result = run_command.apply_async(args=[cmd], queue=HADOOP_QUEUE)
            wait_for_task(result, timeout=30)
        print("✓ HDFS directories created")
    
    def upload_train_data_task(**context):
        print("Uploading train_data.csv via Celery...")
        result = run_command.apply_async(
            args=["~/hadoop/bin/hdfs dfs -put -f ~/Tuan/Project/BigData/final_project/data/train_data.csv /bigdata/house_prices/"],
            queue=HADOOP_QUEUE
        )
        wait_for_task(result, timeout=120)
        print("✓ train_data.csv uploaded")
    
    def upload_stream_data_task(**context):
        print("Uploading stream_data.csv via Celery...")
        result = run_command.apply_async(
            args=["~/hadoop/bin/hdfs dfs -put -f ~/Tuan/Project/BigData/final_project/data/stream_data.csv /bigdata/house_prices/"],
            queue=HADOOP_QUEUE
        )
        wait_for_task(result, timeout=120)
        print("✓ predict_data.csv uploaded")
    
    def verify_data_task(**context):
        print("Verifying uploaded data via Celery...")
        result = run_command.apply_async(
            args=["~/hadoop/bin/hdfs dfs -ls /bigdata/house_prices/"],
            queue=HADOOP_QUEUE
        )
        output = wait_for_task(result, timeout=30)
        print(f"✓ Data verified:\n{output}")
    
    def waiting_trainning_task(**context):
        print("Waiting for services to stabilize before training...")
        time.sleep(30)
        print("✓ Ready for training")

    create_hdfs_dirs = PythonOperator(task_id='create_hdfs_dirs', python_callable=create_hdfs_dirs_task)
    upload_train_data = PythonOperator(task_id='upload_train_data', python_callable=upload_train_data_task)
    upload_stream_data = PythonOperator(task_id='upload_stream_data', python_callable=upload_stream_data_task)
    verify_data = PythonOperator(task_id='verify_data', python_callable=verify_data_task)
    waiting_trainning = PythonOperator(task_id='waiting_trainning', python_callable=waiting_trainning_task)

    # ========================================
    # PHASE 4: TRAIN MODEL WITH SPARK (via Celery)
    # ========================================
    
    def train_model_task(**context):
        print("Training model with Spark via Celery...")
        spark_submit_cmd = f"""
        ~/spark/bin/spark-submit \
          --master {SPARK_MASTER} \
          --deploy-mode client \
          --conf spark.hadoop.fs.defaultFS={HDFS_NAMENODE} \
          --conf spark.driver.memory=2g \
          --conf spark.executor.memory=2g \
          ~/Tuan/Project/BigData/final_project/spark_code/train_model.py
        """
        result = run_command.apply_async(
            args=[spark_submit_cmd],
            queue=SPARK_QUEUE
        )
        output = wait_for_task(result, timeout=1800)  # 30 min timeout
        print(f"✓ Training completed:\n{output}")
    
    def verify_model_task(**context):
        print("Verifying model saved to HDFS via Celery...")
        result = run_command.apply_async(
            args=["~/hadoop/bin/hdfs dfs -ls /bigdata/house_prices/model/"],
            queue=HADOOP_QUEUE
        )
        output = wait_for_task(result, timeout=30)
        print(f"✓ Model verified:\n{output}")
    
    train_model = PythonOperator(task_id='train_model', python_callable=train_model_task)
    verify_model = PythonOperator(task_id='verify_model', python_callable=verify_model_task)

    # ========================================
    # DEPENDENCIES
    # ========================================
    
    # Stop all services in parallel
    [stop_kafka, stop_spark, stop_hadoop]
    
    # Start services sequentially
    [stop_kafka, stop_spark, stop_hadoop] >> start_hadoop >> start_spark >> start_kafka
    
    # Upload data
    start_kafka >> create_hdfs_dirs >> [upload_train_data, upload_stream_data] >> verify_data
    
    # Train model
    verify_data >> train_model >> waiting_trainning >> verify_model
