"""
Realtime Streaming Prediction Pipeline - Improved Architecture
- Tách biệt hoàn toàn với Training DAG
- Tự động kiểm tra và load model mới nhất
- Graceful shutdown cho streaming job
- Health check và monitoring
"""
from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.empty import EmptyOperator  # Changed from dummy to empty
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
KAFKA_BROKER = "192.168.80.51:9092"
KAFKA_QUEUE = "nole2"
SPARK_QUEUE = "nole1"
HADOOP_QUEUE = "nole3"

# Model configuration
MODEL_BASE_PATH = "/bigdata/house_prices/models"  # Thay đổi để lưu nhiều versions
CURRENT_MODEL_LINK = "/bigdata/house_prices/model_current"  # Symbolic link to latest model

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
    '02_Realtime_Streaming_Service',
    default_args=default_args,
    description='Realtime Streaming Prediction Pipeline (Improved)',
    schedule=None,  # Manual trigger hoặc schedule theo nhu cầu
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['streaming', 'prediction', 'production'],
) as dag:

    # ========================================
    # PHASE 0: PRE-CHECK - Model Availability
    # ========================================
    
    def check_and_get_model(**context):
        """
        Kiểm tra model trên HDFS, nếu không có thì tìm từ model base path
        Return: 'continue_setup' nếu tìm thấy model, raise Exception nếu không
        """
        print("🔍 Step 1: Checking if model exists at current link...")
        
        # Try to find model at current link first
        try:
            result = run_command.apply_async(
                args=[f"~/hadoop/bin/hdfs dfs -ls {CURRENT_MODEL_LINK}/"],
                queue=HADOOP_QUEUE
            )
            output = wait_for_task(result, timeout=30)
            
            # Handle dict response
            if isinstance(output, dict):
                output = output.get('stdout', '') or output.get('output', '')
            
            output_str = str(output) if output else ""
            
            if "metadata" in output_str.lower() or "data" in output_str.lower():
                print(f"✅ Model found at {CURRENT_MODEL_LINK}")
                print(f"Model contents:\n{output_str}")
                context['task_instance'].xcom_push(key='model_path', value=CURRENT_MODEL_LINK)
                return 'continue_setup'
        except Exception as e:
            print(f"⚠️  No model at current link: {str(e)}")
        
        # If not found, try to find latest version
        print("🔍 Step 2: Searching for latest model version in base path...")
        try:
            result = run_command.apply_async(
                args=[f"~/hadoop/bin/hdfs dfs -ls {MODEL_BASE_PATH}/ | grep version_ | tail -1"],
                queue=HADOOP_QUEUE
            )
            output = wait_for_task(result, timeout=30)
            
            # Handle dict response
            if isinstance(output, dict):
                output = output.get('stdout', '') or output.get('output', '')
            
            output_str = str(output) if output else ""
            
            if output_str and "version_" in output_str:
                # Extract model path from ls output
                model_path = output_str.strip().split()[-1]
                print(f"✅ Found latest model: {model_path}")
                
                # Update symbolic link to point to latest model
                print(f"🔗 Creating link from {CURRENT_MODEL_LINK} to {model_path}")
                update_link_cmd = f"""
                ~/hadoop/bin/hdfs dfs -rm -r {CURRENT_MODEL_LINK} 2>/dev/null || true && \
                ~/hadoop/bin/hdfs dfs -cp {model_path} {CURRENT_MODEL_LINK}
                """
                result = run_command.apply_async(args=[update_link_cmd], queue=HADOOP_QUEUE)
                wait_for_task(result, timeout=30)
                
                context['task_instance'].xcom_push(key='model_path', value=CURRENT_MODEL_LINK)
                print(f"✅ Model link created successfully")
                return 'continue_setup'
        except Exception as e:
            print(f"❌ Error finding latest model: {str(e)}")
        
        # If still not found, check for legacy model path
        print("🔍 Step 3: Checking legacy model path...")
        try:
            legacy_path = "/bigdata/house_prices/model"
            result = run_command.apply_async(
                args=[f"~/hadoop/bin/hdfs dfs -ls {legacy_path}/"],
                queue=HADOOP_QUEUE
            )
            output = wait_for_task(result, timeout=30)
            
            # Handle dict response
            if isinstance(output, dict):
                output = output.get('stdout', '') or output.get('output', '')
            
            output_str = str(output) if output else ""
            
            if "metadata" in output_str.lower() or "data" in output_str.lower():
                print(f"✅ Found model at legacy path: {legacy_path}")
                context['task_instance'].xcom_push(key='model_path', value=legacy_path)
                return 'continue_setup'
        except Exception as e:
            print(f"⚠️  No model at legacy path: {str(e)}")
        
        # No model found anywhere - fail the DAG
        print("=" * 60)
        print("❌ FATAL ERROR: NO TRAINED MODEL FOUND!")
        print("=" * 60)
        print("Searched locations:")
        print(f"  1. Current link: {CURRENT_MODEL_LINK}")
        print(f"  2. Model versions: {MODEL_BASE_PATH}/version_*")
        print(f"  3. Legacy path: /bigdata/house_prices/model")
        print("\n⚠️  ACTION REQUIRED:")
        print("Please run the Training DAG (01_Train_Model) first to train a model.")
        print("=" * 60)
        raise Exception("No trained model available. Run training DAG first.")
    
    check_model = BranchPythonOperator(
        task_id='check_and_get_model',
        python_callable=check_and_get_model,
    )
    
    continue_setup = EmptyOperator(task_id='continue_setup')

    # ========================================
    # PHASE 1: KAFKA SETUP
    # ========================================
    
    def check_kafka_status(**context):
        """Check if Kafka is already running"""
        print("🔍 Checking Kafka status...")
        try:
            result = run_command.apply_async(
                args=["docker ps | grep kafka"],
                queue=KAFKA_QUEUE
            )
            output = wait_for_task(result, timeout=30)
            
            # Handle dict response
            if isinstance(output, dict):
                output = output.get('stdout', '') or output.get('output', '')
            
            output_str = str(output) if output else ""
            
            if output_str and "kafka" in output_str.lower():
                print("✅ Kafka is already running")
                return 'kafka_running'
            else:
                print("⚠️  Kafka is not running")
                return 'kafka_not_running'
        except:
            print("⚠️  Kafka is not running")
            return 'kafka_not_running'
    
    def stop_kafka_task(**context):
        print("🛑 Stopping Kafka...")
        result = docker_compose_down.apply_async(
            args=["~/kafka_docker/docker-compose.yml"],
            queue=KAFKA_QUEUE
        )
        wait_for_task(result, timeout=60)
        print("✅ Kafka stopped")

    def start_kafka_task(**context):
        print("🚀 Starting Kafka...")
        result = docker_compose_up.apply_async(
            args=["~/kafka_docker/docker-compose.yml"],
            kwargs={"detach": True},
            queue=KAFKA_QUEUE
        )
        wait_for_task(result, timeout=120)
        time.sleep(15)  # Wait for Kafka to be fully ready
        print("✅ Kafka started")
    
    def setup_kafka_topics(**context):
        """Create topics with proper configuration"""
        print("📋 Setting up Kafka topics...")
        topics = [
            {
                "name": "house_input",
                "partitions": 3,  # Increased for better parallelism
                "replication": 1,
                "config": "retention.ms=86400000"  # 24 hours retention
            },
            {
                "name": "house_prediction",
                "partitions": 3,
                "replication": 1,
                "config": "retention.ms=86400000"
            }
        ]
        
        for topic in topics:
            cmd = f"""docker exec kafka kafka-topics \
                --create --if-not-exists \
                --bootstrap-server localhost:9092 \
                --replication-factor {topic['replication']} \
                --partitions {topic['partitions']} \
                --topic {topic['name']} \
                --config {topic['config']}"""
            
            result = run_command.apply_async(args=[cmd], queue=KAFKA_QUEUE)
            wait_for_task(result, timeout=30)
            print(f"✅ Topic '{topic['name']}' configured")
    
    def verify_kafka_health(**context):
        """Verify Kafka is healthy and topics exist"""
        print("🏥 Verifying Kafka health...")
        
        # List topics
        result = run_command.apply_async(
            args=["docker exec kafka kafka-topics --list --bootstrap-server localhost:9092"],
            queue=KAFKA_QUEUE
        )
        topics = wait_for_task(result, timeout=30)
        
        # Handle dict response
        if isinstance(topics, dict):
            topics = topics.get('stdout', '') or topics.get('output', '')
        
        print(f"📋 Available topics:\n{topics}")
        
        # Check broker status
        result = run_command.apply_async(
            args=["docker exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092 2>&1 | head -5"],
            queue=KAFKA_QUEUE
        )
        broker_info = wait_for_task(result, timeout=30)
        
        # Handle dict response
        if isinstance(broker_info, dict):
            broker_info = broker_info.get('stdout', '') or broker_info.get('output', '')
        
        print(f"🔧 Broker status: OK")
        print("✅ Kafka health check passed")
    
    check_kafka = BranchPythonOperator(
        task_id='check_kafka_status',
        python_callable=check_kafka_status,
    )
    
    kafka_running = EmptyOperator(task_id='kafka_running')
    kafka_not_running = EmptyOperator(task_id='kafka_not_running')
    
    stop_kafka = PythonOperator(
        task_id='stop_kafka',
        python_callable=stop_kafka_task,
    )
    
    start_kafka = PythonOperator(
        task_id='start_kafka',
        python_callable=start_kafka_task,
    )
    
    setup_topics = PythonOperator(
        task_id='setup_kafka_topics',
        python_callable=setup_kafka_topics,
        trigger_rule='none_failed',
    )
    
    verify_kafka = PythonOperator(
        task_id='verify_kafka_health',
        python_callable=verify_kafka_health,
    )

    # ========================================
    # PHASE 2: SPARK STREAMING JOB MANAGEMENT
    # ========================================
    
    def check_streaming_job_status(**context):
        """Check if streaming job is already running"""
        print("🔍 Checking existing streaming jobs...")
        try:
            result = run_command.apply_async(
                args=["pgrep -f spark_streaming.py"],
                queue=SPARK_QUEUE
            )
            output = wait_for_task(result, timeout=30)
            
            # Handle dict response
            if isinstance(output, dict):
                output = output.get('stdout', '') or output.get('output', '')
            
            output_str = str(output).strip() if output else ""
            
            if output_str:
                print(f"⚠️  Found existing streaming job(s): PID {output_str}")
                return 'streaming_running'
            else:
                print("✅ No existing streaming jobs found")
                return 'streaming_not_running'
        except:
            print("✅ No existing streaming jobs found")
            return 'streaming_not_running'
    
    def stop_streaming_job_gracefully(**context):
        """Gracefully stop existing streaming job"""
        print("🛑 Stopping existing Spark Streaming jobs...")
        
        # Send SIGTERM for graceful shutdown
        result = run_command.apply_async(
            args=["pkill -15 -f spark_streaming.py || true"],
            queue=SPARK_QUEUE
        )
        wait_for_task(result, timeout=30)
        
        # Wait for graceful shutdown
        time.sleep(10)
        
        # Force kill if still running
        result = run_command.apply_async(
            args=["pkill -9 -f spark_streaming.py || true"],
            queue=SPARK_QUEUE
        )
        wait_for_task(result, timeout=30)
        
        print("✅ Streaming jobs stopped")

    def start_streaming_job_task(**context):
        """Start Spark Streaming job with model path from XCom"""
        print("🚀 Starting Spark Streaming job...")
        
        # Get model path from XCom
        model_path = context['task_instance'].xcom_pull(
            task_ids='check_and_get_model',
            key='model_path'
        )
        
        print(f"📦 Using model from: {model_path}")
        
        # Updated spark-submit with better configuration
        spark_submit_cmd = f"""
        nohup ~/spark/bin/spark-submit \
          --master {SPARK_MASTER} \
          --deploy-mode client \
          --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
          --conf spark.hadoop.fs.defaultFS={HDFS_NAMENODE} \
          --conf spark.driver.memory=2g \
          --conf spark.executor.memory=2g \
          --conf spark.executor.cores=2 \
          --conf spark.cores.max=4 \
          --conf spark.streaming.kafka.maxRatePerPartition=100 \
          --conf spark.sql.streaming.checkpointLocation=/tmp/spark_checkpoint \
          ~/Tuan/Project/BigData/final_project/spark_code/spark_streaming.py \
          --model-path {model_path} \
          --kafka-broker {KAFKA_BROKER} \
          > /tmp/spark_streaming.log 2>&1 &
        """
        
        result = run_command.apply_async(
            args=[spark_submit_cmd],
            queue=SPARK_QUEUE
        )
        
        # Don't wait for completion - streaming job runs continuously
        print(f"✅ Streaming job submitted. Task ID: {result.id}")
        print("📊 Check logs at: /tmp/spark_streaming.log")
        print(f"🌐 Spark UI: http://{SPARK_MASTER.replace('spark://', '').split(':')[0]}:4040")
        
        # Wait a bit and verify job started
        time.sleep(15)
        
    def verify_streaming_job(**context):
        """Verify streaming job is running properly"""
        print("🏥 Verifying streaming job health...")
        
        # Check if process is running
        result = run_command.apply_async(
            args=["pgrep -f spark_streaming.py"],
            queue=SPARK_QUEUE
        )
        
        try:
            output = wait_for_task(result, timeout=30)
            
            # Handle both dict and string responses
            if isinstance(output, dict):
                output = output.get('stdout', '') or output.get('output', '')
            
            output_str = str(output).strip() if output else ""
            
            if output_str:
                print(f"✅ Streaming job is running (PID: {output_str})")
                
                # Check logs for errors
                result = run_command.apply_async(
                    args=["tail -50 /tmp/spark_streaming.log 2>/dev/null || echo 'Log file not found'"],
                    queue=SPARK_QUEUE
                )
                logs = wait_for_task(result, timeout=30)
                
                # Handle dict response for logs
                if isinstance(logs, dict):
                    logs = logs.get('stdout', '') or logs.get('output', '')
                
                logs_str = str(logs) if logs else ""
                
                if "error" in logs_str.lower() or "exception" in logs_str.lower():
                    print("⚠️  Warning: Errors detected in logs")
                    print(f"Recent logs:\n{logs_str[:500]}")  # Limit log output
                else:
                    print("✅ No errors in recent logs")
                    
                return True
            else:
                raise Exception("Streaming job process not found")
        except Exception as e:
            print(f"❌ Streaming job verification failed: {str(e)}")
            raise
    
    check_streaming = BranchPythonOperator(
        task_id='check_streaming_status',
        python_callable=check_streaming_job_status,
    )
    
    streaming_running = EmptyOperator(task_id='streaming_running')
    streaming_not_running = EmptyOperator(task_id='streaming_not_running')
    
    stop_streaming = PythonOperator(
        task_id='stop_streaming_gracefully',
        python_callable=stop_streaming_job_gracefully,
    )
    
    start_streaming = PythonOperator(
        task_id='start_streaming_job',
        python_callable=start_streaming_job_task,
        trigger_rule='none_failed',
    )
    
    verify_streaming = PythonOperator(
        task_id='verify_streaming_health',
        python_callable=verify_streaming_job,
    )

    # ========================================
    # PHASE 3: FINAL STATUS REPORT
    # ========================================
    
    def final_status_report(**context):
        """Generate final status report"""
        print("\n" + "=" * 80)
        print("🎉 STREAMING PREDICTION SERVICE - STATUS REPORT")
        print("=" * 80)
        
        model_path = context['task_instance'].xcom_pull(
            task_ids='check_and_get_model',
            key='model_path'
        )
        
        print(f"""
✅ Service Status: RUNNING
📦 Model Path: {model_path}
🔧 Kafka Broker: {KAFKA_BROKER}
⚡ Spark Master: {SPARK_MASTER}

📊 Monitoring:
   - Spark UI: http://{SPARK_MASTER.replace('spark://', '').split(':')[0]}:4040
   - Logs: /tmp/spark_streaming.log
   - Kafka Topics: house_input, house_prediction

📝 Usage:
   1. Send input data to Kafka topic 'house_input'
   2. Predictions will be available in 'house_prediction' topic
   3. Monitor logs for any issues

⚠️  To stop the service, run the Cleanup DAG or manually kill the process
        """)
        print("=" * 80 + "\n")
    
    status_report = PythonOperator(
        task_id='final_status_report',
        python_callable=final_status_report,
        trigger_rule='none_failed',
    )

    # ========================================
    # DEPENDENCY GRAPH
    # ========================================
    
    # Phase 0: Check model (single task, no cycle)
    check_model >> continue_setup
    
    # Phase 1: Setup Kafka
    continue_setup >> check_kafka >> [kafka_running, kafka_not_running]
    kafka_not_running >> stop_kafka >> start_kafka >> setup_topics
    kafka_running >> setup_topics
    setup_topics >> verify_kafka
    
    # Phase 2: Setup Streaming
    verify_kafka >> check_streaming >> [streaming_running, streaming_not_running]
    streaming_running >> stop_streaming
    streaming_not_running >> stop_streaming
    stop_streaming >> start_streaming >> verify_streaming
    
    # Phase 3: Final report
    verify_streaming >> status_report