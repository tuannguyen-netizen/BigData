#!/bin/bash
# Script tự động setup Nole3 (Airflow + Hadoop + RabbitMQ)
# Chạy trên Nole3

set -e

echo "=========================================="
echo "SETUP NOLE3 - Airflow + Hadoop + RabbitMQ"
echo "=========================================="

# Màu sắc cho output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ==========================================
# 1. Cài đặt RabbitMQ
# ==========================================
echo -e "${YELLOW}[1/8] Cài đặt RabbitMQ...${NC}"
if systemctl is-active --quiet rabbitmq-server; then
    echo -e "${GREEN}✓ RabbitMQ đã chạy${NC}"
else
    sudo apt-get update
    sudo apt-get install -y rabbitmq-server
    sudo systemctl start rabbitmq-server
    sudo systemctl enable rabbitmq-server
    sudo rabbitmq-plugins enable rabbitmq_management
    echo -e "${GREEN}✓ RabbitMQ đã cài đặt và khởi động${NC}"
fi

# ==========================================
# 2. Cấu hình /etc/hosts
# ==========================================
echo -e "${YELLOW}[2/8] Cấu hình /etc/hosts...${NC}"
if ! grep -q "nole1" /etc/hosts; then
    sudo bash -c 'cat >> /etc/hosts << EOF
192.168.80.165  nole1
192.168.80.51   nole2
192.168.80.178  nole3
EOF'
    echo -e "${GREEN}✓ Đã thêm hostname mapping${NC}"
else
    echo -e "${GREEN}✓ Hostname mapping đã tồn tại${NC}"
fi

# ==========================================
# 3. Cài đặt Hadoop
# ==========================================
echo -e "${YELLOW}[3/8] Cài đặt Hadoop...${NC}"
if [ ! -d ~/hadoop ]; then
    cd ~
    if [ ! -f hadoop-3.3.6.tar.gz ]; then
        wget https://downloads.apache.org/hadoop/common/hadoop-3.3.6/hadoop-3.3.6.tar.gz
    fi
    tar -xzf hadoop-3.3.6.tar.gz
    ln -s hadoop-3.3.6 hadoop
    
    # Thêm vào ~/.bashrc
    if ! grep -q "HADOOP_HOME" ~/.bashrc; then
        cat >> ~/.bashrc << 'EOF'
export HADOOP_HOME=~/hadoop
export PATH=$PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin
EOF
    fi
    source ~/.bashrc
    echo -e "${GREEN}✓ Hadoop đã cài đặt${NC}"
else
    echo -e "${GREEN}✓ Hadoop đã tồn tại${NC}"
fi

# ==========================================
# 4. Cấu hình Hadoop
# ==========================================
echo -e "${YELLOW}[4/8] Cấu hình Hadoop...${NC}"
mkdir -p ~/hadoop_data/namenode
mkdir -p ~/hadoop_data/datanode

# core-site.xml
cat > ~/hadoop/etc/hadoop/core-site.xml << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>
<configuration>
    <property>
        <name>fs.defaultFS</name>
        <value>hdfs://nole3:8020</value>
    </property>
</configuration>
EOF

# hdfs-site.xml
cat > ~/hadoop/etc/hadoop/hdfs-site.xml << EOF
<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>
<configuration>
    <property>
        <name>dfs.replication</name>
        <value>1</value>
    </property>
    <property>
        <name>dfs.namenode.name.dir</name>
        <value>file://$HOME/hadoop_data/namenode</value>
    </property>
    <property>
        <name>dfs.datanode.data.dir</name>
        <value>file://$HOME/hadoop_data/datanode</value>
    </property>
</configuration>
EOF

echo -e "${GREEN}✓ Hadoop đã cấu hình${NC}"

# ==========================================
# 5. Format Namenode (nếu chưa format)
# ==========================================
echo -e "${YELLOW}[5/8] Format Namenode...${NC}"
if [ ! -d ~/hadoop_data/namenode/current ]; then
    ~/hadoop/bin/hdfs namenode -format -force
    echo -e "${GREEN}✓ Namenode đã format${NC}"
else
    echo -e "${GREEN}✓ Namenode đã được format trước đó${NC}"
fi

# ==========================================
# 6. Cài đặt Airflow
# ==========================================
echo -e "${YELLOW}[6/8] Cài đặt Airflow...${NC}"
pip3 install --user apache-airflow==3.1.3
pip3 install --user apache-airflow-providers-celery

# Set environment variables
export AIRFLOW_HOME=~/Tuan/Project/BigData/final_project
export AIRFLOW__CORE__DAGS_FOLDER=~/Tuan/Project/BigData/final_project/dags
export AIRFLOW__CORE__LOAD_EXAMPLES=False
export PYTHONPATH=~/Tuan/Project/BigData/final_project:$PYTHONPATH

# Thêm vào ~/.bashrc
if ! grep -q "AIRFLOW_HOME" ~/.bashrc; then
    cat >> ~/.bashrc << 'EOF'
export AIRFLOW_HOME=~/Tuan/Project/BigData/final_project
export AIRFLOW__CORE__DAGS_FOLDER=~/Tuan/Project/BigData/final_project/dags
export AIRFLOW__CORE__LOAD_EXAMPLES=False
export PYTHONPATH=~/Tuan/Project/BigData/final_project:$PYTHONPATH
EOF
fi

# Initialize database
airflow db init

# Create admin user (skip if exists)
airflow users create \
  --username admin \
  --firstname Admin \
  --lastname User \
  --role Admin \
  --email admin@example.com \
  --password admin 2>/dev/null || echo "User already exists"

echo -e "${GREEN}✓ Airflow đã cài đặt${NC}"

# ==========================================
# 7. Cài đặt Python dependencies
# ==========================================
echo -e "${YELLOW}[7/8] Cài đặt Python dependencies...${NC}"
cd ~/Tuan/Project/BigData/final_project
pip3 install --user -r requirements.txt
echo -e "${GREEN}✓ Dependencies đã cài đặt${NC}"

# ==========================================
# 8. Start HDFS
# ==========================================
echo -e "${YELLOW}[8/8] Start HDFS...${NC}"
~/hadoop/sbin/start-dfs.sh
sleep 5

# Disable safe mode
~/hadoop/bin/hdfs dfsadmin -safemode leave

echo -e "${GREEN}✓ HDFS đã khởi động${NC}"

# ==========================================
# SUMMARY
# ==========================================
echo ""
echo "=========================================="
echo -e "${GREEN}SETUP NOLE3 HOÀN TẤT!${NC}"
echo "=========================================="
echo ""
echo "Services đã cài đặt:"
echo "  ✓ RabbitMQ: http://localhost:15672 (guest/guest)"
echo "  ✓ Hadoop HDFS: http://localhost:9870"
echo "  ✓ Airflow: Chưa start (cần start thủ công)"
echo ""
echo "Để start Airflow:"
echo "  Terminal 1: airflow webserver --port 8080"
echo "  Terminal 2: airflow scheduler"
echo ""
echo "Để start Celery worker:"
echo "  cd ~/Tuan/Project/BigData/final_project"
echo "  celery -A mycelery.system_worker worker --loglevel=info --queues=hadoop_queue --hostname=hadoop_worker@nole3 --broker=pyamqp://guest@localhost//"
echo ""
