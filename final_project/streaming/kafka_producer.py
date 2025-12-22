"""
Chương trình mô phỏng streaming - gửi dữ liệu vào Kafka
Đọc dữ liệu từ HDFS
"""
import json
import os
import time
import pandas as pd
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable
import sys
import subprocess
import tempfile

def read_from_hdfs(hdfs_path):
    """
    Đọc file CSV từ HDFS và trả về DataFrame
    
    Args:
        hdfs_path: Đường dẫn HDFS (ví dụ: hdfs://worker1:8020/bigdata/house_prices/streaming_data.csv)
    
    Returns:
        pandas.DataFrame
    """
    # Tạo file tạm với tên unique để tránh conflict
    import uuid
    temp_path = os.path.join(tempfile.gettempdir(), f"hdfs_streaming_{uuid.uuid4().hex}.csv")
    
    try:
        # Xóa file tạm nếu đã tồn tại (để đảm bảo)
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        
        # Sử dụng hdfs dfs -get với flag -f để force overwrite
        cmd = ['hdfs', 'dfs', '-get', '-f', hdfs_path, temp_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            # Nếu flag -f không được hỗ trợ, thử lại không có flag
            if '-f' in result.stderr or 'Unknown command' in result.stderr:
                # Xóa file nếu tồn tại và thử lại không có -f
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                cmd = ['hdfs', 'dfs', '-get', hdfs_path, temp_path]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                raise Exception(
                    f"Không thể đọc file từ HDFS: {hdfs_path}\n"
                    f"Error: {result.stderr}\n"
                    f"Command: {' '.join(cmd)}"
                )
        
        # Kiểm tra file đã được download chưa
        if not os.path.exists(temp_path):
            raise Exception(f"File tạm không được tạo: {temp_path}")
        
        # Đọc file CSV từ local
        df = pd.read_csv(temp_path)
        print(f"✓ Đã đọc {len(df)} dòng từ HDFS: {hdfs_path}")
        
        return df
    
    finally:
        # Xóa file tạm
        if os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception:
                pass  # Ignore errors khi xóa file

def create_producer(max_retries=10):
    """Tạo Kafka producer với retry logic, dùng hostname hoặc env."""
    # Cho phép cấu hình qua env để tránh hard-code IP
    # Default là localhost:9092 (chạy trên máy Kafka)
    bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    servers = [s.strip() for s in bootstrap.split(",") if s.strip()]

    for i in range(max_retries):
        try:
            producer = KafkaProducer(
                bootstrap_servers=servers,
                value_serializer=lambda x: json.dumps(x).encode('utf-8'),
                api_version=(2, 5, 0)
            )
            print(f"✓ Đã kết nối đến Kafka broker: {servers}")
            return producer
        except NoBrokersAvailable:
            if i < max_retries - 1:
                print(f"⏳ Đang chờ Kafka khởi động... (thử lần {i+1}/{max_retries})")
                time.sleep(5)
            else:
                print("❌ Không thể kết nối đến Kafka sau nhiều lần thử")
                raise

def send_streaming_data(interval=2, num_records=None):
    """
    Gửi dữ liệu streaming vào Kafka
    
    Args:
        interval: Khoảng thời gian giữa các lần gửi (giây)
        num_records: Số lượng bản ghi gửi (None = gửi tất cả)
    """
    # Đọc dữ liệu từ HDFS (on Nole3)
    # Có thể override bằng environment variable
    hdfs_namenode = os.getenv("HDFS_NAMENODE", "hdfs://nole3:8020")
    hdfs_data_path = os.getenv(
        "HDFS_STREAMING_DATA_PATH",
        f"{hdfs_namenode}/bigdata/house_prices/streaming_data.csv"
    )
    
    print(f"📂 Đọc dữ liệu từ HDFS: {hdfs_data_path}")
    df = read_from_hdfs(hdfs_data_path)
    
    if num_records:
        df = df.head(num_records)
    
    print("=" * 60)
    print("KAFKA PRODUCER - MÔ PHỎNG STREAMING")
    print("=" * 60)
    print(f"Số lượng bản ghi sẽ gửi: {len(df)}")
    print(f"Khoảng thời gian: {interval} giây/bản ghi")
    print(f"Topic: house-prices-input")
    print("=" * 60)
    
    # Tạo producer
    producer = create_producer()
    
    try:
        for idx, row in df.iterrows():
            # Tạo message (không bao gồm target - để mô hình dự đoán)
            message = {
                'id': idx,
                'MedInc': float(row['MedInc']),
                'HouseAge': float(row['HouseAge']),
                'AveRooms': float(row['AveRooms']),
                'AveBedrms': float(row['AveBedrms']),
                'Population': float(row['Population']),
                'AveOccup': float(row['AveOccup']),
                'Latitude': float(row['Latitude']),
                'Longitude': float(row['Longitude']),
                'actual_price': float(row['target'])  # Giá thực tế để so sánh
            }
            
            # Gửi vào Kafka
            producer.send('house-prices-input', value=message)
            
            print(f"📤 Đã gửi bản ghi {idx+1}/{len(df)} | "
                  f"MedInc={message['MedInc']:.2f} | "
                  f"Actual Price=${message['actual_price']*100:.2f}K")
            
            time.sleep(interval)
        
        producer.flush()
        print("\n✓ Đã gửi tất cả dữ liệu!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Đã dừng streaming")
    finally:
        producer.close()
        print("✓ Đã đóng producer")

if __name__ == "__main__":
    # Có thể truyền tham số từ command line
    interval = float(sys.argv[1]) if len(sys.argv) > 1 else 2
    num_records = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    send_streaming_data(interval=interval, num_records=num_records)