# HƯỚNG DẪN FIX HOSTNAME TRÊN NOLE3

## Vấn đề
HDFS không thể start vì hostname `nole3` không resolve được.

## Giải pháp

### Bước 1: SSH vào Nole3
```bash
ssh nole3@192.168.80.178
```

### Bước 2: Sửa /etc/hosts
```bash
sudo nano /etc/hosts
```

Thêm hoặc sửa các dòng sau (xóa các dòng cũ nếu có):
```
192.168.80.165  nole1
192.168.80.51   nole2
192.168.80.178  nole3
```

Lưu file (Ctrl+O, Enter, Ctrl+X)

### Bước 3: Test hostname resolution
```bash
ping -c 2 nole3
ping -c 2 nole1
ping -c 2 nole2
```

Tất cả phải thành công!

### Bước 4: Restart HDFS
```bash
# Stop HDFS
~/hadoop/sbin/stop-dfs.sh

# Start HDFS
~/hadoop/sbin/start-dfs.sh

# Disable safe mode
~/hadoop/bin/hdfs dfsadmin -safemode leave

# Check status
~/hadoop/bin/hdfs dfsadmin -report
```

### Bước 5: Verify HDFS
```bash
# List HDFS root
~/hadoop/bin/hdfs dfs -ls /

# Create test directory
~/hadoop/bin/hdfs dfs -mkdir -p /test

# List again
~/hadoop/bin/hdfs dfs -ls /
```

## Sau khi fix xong

Quay lại máy development và tiếp tục setup Nole1 và Nole2:

```bash
cd ~/Tuan/Project/BigData/final_project

# Setup Nole1
./scripts/setup_nole1_ssh.sh

# Setup Nole2
./scripts/setup_nole2_ssh.sh

# Upload data
ssh nole3@192.168.80.178
cd ~/Tuan/Project/BigData/final_project
python3 data/prepare_data.py
export HDFS_NAMENODE=hdfs://nole3:8020
python3 data/upload_to_hdfs.py
```
