# FIX AIRFLOW HOME DIRECTORY

## Vấn đề
Airflow tạo file ở `~/airflow` thay vì `~/Tuan/Project/BigData/final_project`

## Nguyên nhân
Biến `AIRFLOW_HOME` chưa được set khi chạy `airflow standalone`

## Giải pháp

### Option 1: Set AIRFLOW_HOME trước khi chạy (Khuyến nghị)

```bash
# Stop airflow hiện tại (Ctrl+C)

# Set AIRFLOW_HOME
export AIRFLOW_HOME=~/Tuan/Project/BigData/final_project

# Verify
echo $AIRFLOW_HOME

# Chạy lại
airflow standalone
```

### Option 2: Thêm vào ~/.bashrc (Permanent)

```bash
# Stop airflow (Ctrl+C)

# Thêm vào ~/.bashrc
cat >> ~/.bashrc << 'EOF'
# Airflow Configuration
export AIRFLOW_HOME=~/Tuan/Project/BigData/final_project
export AIRFLOW__CORE__DAGS_FOLDER=~/Tuan/Project/BigData/final_project/dags
export AIRFLOW__CORE__LOAD_EXAMPLES=False
export PYTHONPATH=~/Tuan/Project/BigData/final_project:$PYTHONPATH
EOF

# Reload
source ~/.bashrc

# Verify
echo $AIRFLOW_HOME

# Chạy lại
airflow standalone
```

### Option 3: Dùng script wrapper

```bash
# Tạo script
cat > ~/start_airflow.sh << 'EOF'
#!/bin/bash
export AIRFLOW_HOME=~/Tuan/Project/BigData/final_project
export AIRFLOW__CORE__DAGS_FOLDER=~/Tuan/Project/BigData/final_project/dags
export AIRFLOW__CORE__LOAD_EXAMPLES=False
export PYTHONPATH=~/Tuan/Project/BigData/final_project:$PYTHONPATH

cd $AIRFLOW_HOME
airflow standalone
EOF

chmod +x ~/start_airflow.sh

# Chạy
~/start_airflow.sh
```

### Option 4: Cleanup và restart

```bash
# Stop airflow (Ctrl+C)

# Xóa thư mục airflow cũ (optional - backup trước)
mv ~/airflow ~/airflow.backup

# Set environment
export AIRFLOW_HOME=~/Tuan/Project/BigData/final_project
export AIRFLOW__CORE__DAGS_FOLDER=~/Tuan/Project/BigData/final_project/dags
export AIRFLOW__CORE__LOAD_EXAMPLES=False

# Reinitialize
cd ~/Tuan/Project/BigData/final_project
airflow db init

# Create admin user
airflow users create \
  --username admin \
  --firstname Admin \
  --lastname User \
  --role Admin \
  --email admin@example.com \
  --password admin

# Start
airflow standalone
```

## Verify

Sau khi start lại, kiểm tra:

```bash
# Check AIRFLOW_HOME
echo $AIRFLOW_HOME
# Phải thấy: /home/nole3/Tuan/Project/BigData/final_project

# Check files được tạo ở đâu
ls -la ~/Tuan/Project/BigData/final_project/airflow*
# Phải thấy các file airflow ở đây

# Check DAGs
airflow dags list | grep -E "train|predict"
```

## Lấy password admin

Nếu password được tạo ở `~/airflow/simple_auth_manager_passwords.json.generated`:

```bash
cat ~/airflow/simple_auth_manager_passwords.json.generated
```

Hoặc tạo user mới:

```bash
export AIRFLOW_HOME=~/Tuan/Project/BigData/final_project
airflow users create \
  --username admin \
  --firstname Admin \
  --lastname User \
  --role Admin \
  --email admin@example.com \
  --password admin
```

## Quick Fix Script

```bash
#!/bin/bash
# Quick fix script

echo "Stopping Airflow..."
# Nếu đang chạy, Ctrl+C

echo "Setting AIRFLOW_HOME..."
export AIRFLOW_HOME=~/Tuan/Project/BigData/final_project
export AIRFLOW__CORE__DAGS_FOLDER=~/Tuan/Project/BigData/final_project/dags
export AIRFLOW__CORE__LOAD_EXAMPLES=False
export PYTHONPATH=~/Tuan/Project/BigData/final_project:$PYTHONPATH

echo "AIRFLOW_HOME is now: $AIRFLOW_HOME"

echo "Creating admin user..."
airflow users create \
  --username admin \
  --firstname Admin \
  --lastname User \
  --role Admin \
  --email admin@example.com \
  --password admin 2>/dev/null || echo "User already exists"

echo "Starting Airflow..."
cd $AIRFLOW_HOME
airflow standalone
```

## Recommended: Permanent Fix

Thêm vào `~/.bashrc`:

```bash
nano ~/.bashrc

# Thêm vào cuối file:
export AIRFLOW_HOME=~/Tuan/Project/BigData/final_project
export AIRFLOW__CORE__DAGS_FOLDER=~/Tuan/Project/BigData/final_project/dags
export AIRFLOW__CORE__LOAD_EXAMPLES=False
export PYTHONPATH=~/Tuan/Project/BigData/final_project:$PYTHONPATH

# Lưu và reload
source ~/.bashrc
```

Sau đó mỗi lần login, biến đã được set sẵn!
