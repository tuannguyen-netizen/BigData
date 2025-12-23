"""
Service để load Spark ML model và thực hiện dự đoán giá nhà
Hỗ trợ load từ HDFS hoặc local
"""
from pyspark.sql import SparkSession
from pyspark.ml import PipelineModel
from pyspark.sql.types import StructType, StructField, DoubleType
from pyspark.sql import Row
import os
import subprocess
import tempfile
import shutil

class HousePricePredictor:
    def __init__(self, model_path=None):
        # Có thể override bằng environment variable
        if model_path is None:
            model_path = os.getenv("MODEL_PATH", "models/house_price_model")
        
        # Nếu là HDFS path, sẽ download về local tạm
        self.model_path = model_path
        self.hdfs_model_path = None
        self.temp_model_dir = None
        self.spark = None
        self.model = None
        self._initialize()
    
    def _download_from_hdfs(self, hdfs_path):
        """Download model từ HDFS về local"""
        # Tạo thư mục tạm
        temp_dir = tempfile.mkdtemp(prefix="spark_model_")
        self.temp_model_dir = temp_dir
        
        try:
            # Download toàn bộ thư mục model từ HDFS
            cmd = ['hdfs', 'dfs', '-get', hdfs_path, temp_dir]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                raise Exception(
                    f"Không thể download model từ HDFS: {hdfs_path}\n"
                    f"Error: {result.stderr}\n"
                    f"Command: {' '.join(cmd)}"
                )
            
            # Tìm đường dẫn model trong temp_dir
            # HDFS get sẽ tạo thư mục với tên cuối cùng của path
            model_name = os.path.basename(hdfs_path.rstrip('/'))
            local_model_path = os.path.join(temp_dir, model_name)
            
            if not os.path.exists(local_model_path):
                # Thử tìm trong temp_dir
                contents = os.listdir(temp_dir)
                if contents:
                    local_model_path = os.path.join(temp_dir, contents[0])
            
            print(f"✓ Đã download model từ HDFS: {hdfs_path} → {local_model_path}")
            return local_model_path
            
        except Exception as e:
            # Cleanup nếu lỗi
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
            raise
    
    def _initialize(self):
        """Khởi tạo Spark session và load model"""
        try:
            # Kiểm tra xem model_path có phải HDFS path không
            is_hdfs = self.model_path.startswith('hdfs://')
            
            if is_hdfs:
                self.hdfs_model_path = self.model_path
                # Download từ HDFS về local
                local_model_path = self._download_from_hdfs(self.hdfs_model_path)
                # Đảm bảo dùng absolute path với file:// prefix
                local_model_path = os.path.abspath(local_model_path)
                if not local_model_path.startswith('file://'):
                    local_model_path = f"file://{local_model_path}"
            else:
                # Load từ local
                local_model_path = self.model_path
                if not os.path.exists(local_model_path):
                    raise FileNotFoundError(f"Model không tồn tại tại: {local_model_path}")
                # Đảm bảo dùng absolute path với file:// prefix
                local_model_path = os.path.abspath(local_model_path)
                if not local_model_path.startswith('file://'):
                    local_model_path = f"file://{local_model_path}"
            
            # Spark session cho local filesystem (luôn dùng file:// khi load model)
            self.spark = SparkSession.builder \
                .appName("HousePricePredictionService") \
                .config("spark.hadoop.fs.defaultFS", "file:///") \
                .config("spark.local.dir", "/tmp/spark_local") \
                .config("spark.driver.memory", "2g") \
                .config("spark.executor.memory", "2g") \
                .config("spark.sql.execution.arrow.pyspark.enabled", "true") \
                .getOrCreate()
            
            self.spark.sparkContext.setLogLevel("ERROR")
            
            # Load model với file:// path
            print(f"📂 Đang load model từ: {local_model_path}")
            self.model = PipelineModel.load(local_model_path)
            print(f"✓ Đã tải model thành công từ: {self.model_path}")
            
        except Exception as e:
            print(f"❌ Lỗi khi khởi tạo predictor: {e}")
            import traceback
            print(f"   Traceback: {traceback.format_exc()}")
            raise
    
    def predict(self, med_inc, house_age, ave_rooms, ave_bedrms, 
                population, ave_occup, latitude, longitude):
        """
        Dự đoán giá nhà dựa trên các đặc trưng
        
        Args:
            med_inc: Thu nhập trung bình
            house_age: Tuổi nhà
            ave_rooms: Số phòng trung bình
            ave_bedrms: Số phòng ngủ trung bình
            population: Dân số
            ave_occup: Mật độ cư trú trung bình
            latitude: Vĩ độ
            longitude: Kinh độ
        
        Returns:
            float: Giá nhà dự đoán (đơn vị: trăm nghìn USD)
        """
        try:
            # Tạo DataFrame từ dữ liệu đầu vào
            data = Row(
                MedInc=float(med_inc),
                HouseAge=float(house_age),
                AveRooms=float(ave_rooms),
                AveBedrms=float(ave_bedrms),
                Population=float(population),
                AveOccup=float(ave_occup),
                Latitude=float(latitude),
                Longitude=float(longitude)
            )
            
            df = self.spark.createDataFrame([data])
            
            # Thực hiện dự đoán
            predictions = self.model.transform(df)
            
            # Lấy kết quả dự đoán
            result = predictions.select("prediction").collect()[0][0]
            
            return float(result)
            
        except Exception as e:
            print(f"❌ Lỗi khi dự đoán: {e}")
            raise
    
    def predict_batch(self, data_list):
        """
        Dự đoán hàng loạt
        
        Args:
            data_list: List of dicts, mỗi dict chứa các features
        
        Returns:
            List of predictions
        """
        try:
            rows = []
            for data in data_list:
                rows.append(Row(
                    MedInc=float(data['MedInc']),
                    HouseAge=float(data['HouseAge']),
                    AveRooms=float(data['AveRooms']),
                    AveBedrms=float(data['AveBedrms']),
                    Population=float(data['Population']),
                    AveOccup=float(data['AveOccup']),
                    Latitude=float(data['Latitude']),
                    Longitude=float(data['Longitude'])
                ))
            
            df = self.spark.createDataFrame(rows)
            predictions = self.model.transform(df)
            
            results = [float(row.prediction) for row in predictions.select("prediction").collect()]
            return results
            
        except Exception as e:
            print(f"❌ Lỗi khi dự đoán hàng loạt: {e}")
            raise
    
    def close(self):
        """Đóng Spark session và cleanup"""
        if self.spark:
            self.spark.stop()
            self.spark = None
        
        # Xóa thư mục tạm nếu có
        if self.temp_model_dir and os.path.exists(self.temp_model_dir):
            try:
                shutil.rmtree(self.temp_model_dir, ignore_errors=True)
                print(f"✓ Đã xóa thư mục tạm: {self.temp_model_dir}")
            except Exception:
                pass

# Global predictor instance
_predictor = None

def get_predictor():
    """Lấy singleton instance của predictor"""
    global _predictor
    if _predictor is None:
        # Có thể override model path bằng environment variable
        model_path = os.getenv("MODEL_PATH")
        if not model_path:
            # Thử HDFS path trước, fallback về local
            hdfs_namenode = os.getenv("HDFS_NAMENODE", "hdfs://worker1:8020")
            hdfs_model_path = os.getenv("HDFS_MODEL_PATH", f"{hdfs_namenode}/bigdata/model")
            # Thử load từ HDFS, nếu không được thì fallback về local
            try:
                # Test xem có thể access HDFS không
                cmd = ['hdfs', 'dfs', '-test', '-e', hdfs_model_path]
                result = subprocess.run(cmd, capture_output=True, timeout=10)
                if result.returncode == 0:
                    model_path = hdfs_model_path
                    print(f"📂 Sử dụng model từ HDFS: {hdfs_model_path}")
                else:
                    model_path = "models/house_price_model"
                    print(f"📂 Sử dụng model local: {model_path}")
            except Exception:
                model_path = "models/house_price_model"
                print(f"📂 Sử dụng model local (fallback): {model_path}")
        
        _predictor = HousePricePredictor(model_path=model_path)
    return _predictor

