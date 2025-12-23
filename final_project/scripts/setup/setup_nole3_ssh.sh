#!/bin/bash
# Script tự động setup Nole3 (Airflow + Hadoop + RabbitMQ) qua SSH
# Chạy từ máy development

set -e

NOLE3_USER="nole3"
NOLE3_HOST="192.168.80.178"

echo "=========================================="
echo "SETUP NOLE3 - Airflow + Hadoop + RabbitMQ"
echo "=========================================="

# Tạo script để chạy trên Nole3
cat > /tmp/setup_nole3_remote.sh << 'EOFREMOTE'
#!/bin/bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}[1/9] Cấu hình /etc/hosts...${NC}"
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

echo -e "${YELLOW}[2/9] Cài đặt RabbitMQ...${NC}"
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

echo -e "${YELLOW}[3/9] Cài đặt Hadoop...${NC}"
if [ ! -d ~/hadoop ]; then
    cd ~
    if [ ! -f hadoop-3.3.6.tar.gz ]; then
        wget https://downloads.apache.org/hadoop/common/hadoop-3.3.6/hadoop-3.3.6.tar.gz
    fi
    tar -xzf hadoop-3.3.6.tar.gz
    ln -s hadoop-3.3.6 hadoop
    
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

echo -e "${YELLOW}[4/9] Cấu hình Hadoop...${NC}"
mkdir -p ~/hadoop_data/namenode
mkdir -p ~/hadoop_data/datanode

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

echo -e "${YELLOW}[5/9] Format Namenode...${NC}"
if [ ! -d ~/hadoop_data/namenode/current ]; then
    ~/hadoop/bin/hdfs namenode -format -force
    echo -e "${GREEN}✓ Namenode đã format${NC}"
else
    echo -e "${GREEN}✓ Namenode đã được format trước đó${NC}"
fi

echo -e "${YELLOW}[6/9] Cài đặt Airflow...${NC}"
pip3 install --user apache-airflow==3.1.3
pip3 install --user apache-airflow-providers-celery

# Tạo thư mục project
mkdir -p ~/Tuan/Project/BigData
echo -e "${GREEN}✓ Airflow đã cài đặt${NC}"

echo -e "${YELLOW}[7/9] Cài đặt Python dependencies...${NC}"
pip3 install --user celery pika pandas scikit-learn kafka-python pyspark==4.0.0
echo -e "${GREEN}✓ Dependencies đã cài đặt${NC}"

echo -e "${YELLOW}[8/9] Stop existing HDFS processes...${NC}"
~/hadoop/sbin/stop-dfs.sh 2>/dev/null || true
sleep 3
echo -e "${GREEN}✓ HDFS processes stopped${NC}"

echo -e "${YELLOW}[9/9] Start HDFS...${NC}"
~/hadoop/sbin/start-dfs.sh
sleep 5
~/hadoop/bin/hdfs dfsadmin -safemode leave
echo -e "${GREEN}✓ HDFS đã khởi động${NC}"

echo ""
echo "=========================================="
echo -e "${GREEN}SETUP NOLE3 HOÀN TẤT!${NC}"
echo "=========================================="
echo "RabbitMQ: http://192.168.80.178:15672 (guest/guest)"
echo "HDFS: http://192.168.80.178:9870"
echo ""
EOFREMOTE

# Copy script lên Nole3
echo "Copying setup script to Nole3..."
scp /tmp/setup_nole3_remote.sh ${NOLE3_USER}@${NOLE3_HOST}:/tmp/

# Chạy script trên Nole3
echo "Running setup on Nole3..."
ssh ${NOLE3_USER}@${NOLE3_HOST} "bash /tmp/setup_nole3_remote.sh"

# Copy project code
echo "Copying project code to Nole3..."
scp -r ~/Tuan/Project/BigData/final_project ${NOLE3_USER}@${NOLE3_HOST}:~/Tuan/Project/BigData/

# Setup Airflow environment
echo "Setting up Airflow environment on Nole3..."
ssh ${NOLE3_USER}@${NOLE3_HOST} << 'EOFSSH'
# Set environment variables
if ! grep -q "AIRFLOW_HOME" ~/.bashrc; then
    cat >> ~/.bashrc << 'EOF'
export AIRFLOW_HOME=~/Tuan/Project/BigData/final_project
export AIRFLOW__CORE__DAGS_FOLDER=~/Tuan/Project/BigData/final_project/dags
export AIRFLOW__CORE__LOAD_EXAMPLES=False
export PYTHONPATH=~/Tuan/Project/BigData/final_project:$PYTHONPATH
EOF
fi

export AIRFLOW_HOME=~/Tuan/Project/BigData/final_project
export AIRFLOW__CORE__DAGS_FOLDER=~/Tuan/Project/BigData/final_project/dags
export AIRFLOW__CORE__LOAD_EXAMPLES=False
export PYTHONPATH=~/Tuan/Project/BigData/final_project:$PYTHONPATH

# Initialize Airflow
cd ~/Tuan/Project/BigData/final_project
airflow db init

# Create admin user
airflow users create \
  --username admin \
  --firstname Admin \
  --lastname User \
  --role Admin \
  --email admin@example.com \
  --password admin 2>/dev/null || echo "User already exists"

# Install project dependencies
pip3 install --user -r requirements.txt
EOFSSH

echo ""
echo "=========================================="
echo "NOLE3 SETUP COMPLETE!"
echo "=========================================="
echo ""
echo "Để start Celery worker trên Nole3:"
echo "  ssh ${NOLE3_USER}@${NOLE3_HOST}"
echo "  cd ~/Tuan/Project/BigData/final_project"
echo "  celery -A mycelery.system_worker worker --loglevel=info --queues=hadoop_queue --hostname=hadoop_worker@nole3 --broker=pyamqp://guest@localhost//"
echo ""
echo "Để start Airflow trên Nole3:"
echo "  ssh ${NOLE3_USER}@${NOLE3_HOST}"
echo "  Terminal 1: airflow webserver --port 8080"
echo "  Terminal 2: airflow scheduler"
echo ""
