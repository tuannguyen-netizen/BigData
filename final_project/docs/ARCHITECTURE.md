# System Architecture

## Overview

This project implements a distributed real-time machine learning pipeline for house price prediction using Apache Spark, Kafka, Airflow, and HDFS.

## Distributed Architecture

### Node Configuration

The system runs across 3 physical nodes:

| Node | Hostname | IP | Services | Celery Queue |
|------|----------|-----|----------|--------------|
| **Nole1** | worker3 | 192.168.80.165 | Spark Master + Workers | `nole1` |
| **Nole2** | - | 192.168.80.51 | Kafka Cluster (Docker) | `nole2` |
| **Nole3** | worker1 | 192.168.80.178 | HDFS Namenode + Datanode | `nole3` |
| **Airflow** | airflow-master | - | Airflow + RabbitMQ | - |

### Communication Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Airflow (Orchestrator)                     │
│  ┌──────────────┐         ┌──────────────┐            │
│  │  Airflow DAG │────────▶│  RabbitMQ    │            │
│  └──────────────┘         └──────┬───────┘            │
└──────────────────────────────────┼─────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
        ┌───────────▼───┐  ┌───────▼──────┐  ┌───▼──────────┐
        │ Kafka Worker  │  │ Spark Worker │  │ Hadoop Worker│
        │ (nole2)       │  │ (nole1)      │  │ (nole3)      │
        └───────┬───────┘  └──────┬───────┘  └───┬──────────┘
                │                 │              │
        ┌───────▼───────┐  ┌──────▼──────┐  ┌───▼──────────┐
        │ Kafka Cluster │  │ Spark Master │  │ HDFS         │
        │ (Docker)      │  │ + Workers    │  │ Namenode     │
        │ Port: 9092    │  │ Port: 7077   │  │ Port: 8020   │
        └───────────────┘  └──────────────┘  └──────────────┘
```

**Key Design Decision: RabbitMQ + Celery Instead of SSH**

- **Traditional Approach**: Use SSH to execute commands on remote nodes
- **Our Approach**: Use RabbitMQ message broker + Celery workers
- **Benefits**:
  - No SSH key management
  - Better error handling and retry logic
  - Centralized message broker
  - Easy to scale (add more workers)
  - Task queuing and prioritization

## Data Flow

### Training Pipeline

```
1. Prepare Data (local)
   ↓
2. Upload to HDFS (/bigdata/house_prices/train_data.csv)
   ↓
3. Spark ML Training (read from HDFS)
   ↓
4. Save Model to HDFS (/bigdata/house_prices/model)
```

### Streaming Pipeline

```
1. Producer reads from HDFS (/bigdata/house_prices/streaming_data.csv)
   ↓
2. Send to Kafka (house-prices-input topic)
   ↓
3. Spark Streaming reads from Kafka
   ↓
4. Load Model from HDFS
   ↓
5. Predict and send to Kafka (house-prices-output topic)
   ↓
6. Consumer visualizes results
```

## Technology Stack

### Core Components

- **Apache Spark 4.0.0**: Distributed ML training and streaming
- **Apache Kafka 3.8.0**: Message queue for streaming data
- **Apache Airflow 2.7.0**: Workflow orchestration
- **Hadoop HDFS**: Distributed file storage
- **RabbitMQ**: Message broker for Celery
- **Celery**: Distributed task queue

### ML Framework

- **Spark ML**: Random Forest Regressor
- **Features**: 8 features (MedInc, HouseAge, AveRooms, etc.)
- **Target**: House prices (in $100K units)

### Programming Languages

- **Python 3.9+**: Main language for all components
- **Bash**: Shell scripts for setup and utilities

## Storage Architecture

### HDFS Structure

```
/bigdata/house_prices/
├── train_data.csv           # Training dataset
├── streaming_data.csv       # Streaming dataset
├── model/                   # Current model
│   ├── metadata/
│   └── stages/
│       ├── 0_VectorAssembler_*/
│       └── 1_RandomForestRegressor_*/
└── models/                  # Model versions (future)
    ├── v1/
    ├── v2/
    └── model_current -> v2  # Symbolic link
```

### Local Storage

```
final_project/
├── data/                    # Local data preparation
├── models/                  # Local model backup (optional)
└── logs/                    # Application logs
```

## Network Ports

| Service | Port | Protocol | Description |
|---------|------|----------|-------------|
| HDFS Namenode | 8020 | TCP | HDFS RPC |
| HDFS Web UI | 9870 | HTTP | HDFS monitoring |
| Spark Master | 7077 | TCP | Spark RPC |
| Spark Web UI | 8080 | HTTP | Spark monitoring |
| Kafka Broker | 9092 | TCP | Kafka protocol |
| RabbitMQ | 5672 | AMQP | Message broker |
| RabbitMQ UI | 15672 | HTTP | Management UI |
| Airflow Web | 8080 | HTTP | Airflow UI |

## Scalability Considerations

### Horizontal Scaling

- **Spark**: Add more worker nodes
- **Kafka**: Add more brokers and partitions
- **HDFS**: Add more datanodes
- **Celery**: Add more workers on different machines

### Vertical Scaling

- Increase memory for Spark executors
- Increase CPU cores for workers
- Increase disk space for HDFS

## Fault Tolerance

### Data Reliability

- **HDFS**: Replication factor (default: 3)
- **Kafka**: Topic replication
- **Spark**: Checkpoint mechanism

### Task Reliability

- **Airflow**: Task retry logic
- **Celery**: Task acknowledgment and retry
- **Spark Streaming**: Checkpoint recovery

## Security Considerations

### Current Setup (Development)

- No authentication on HDFS
- No SSL/TLS on Kafka
- Default RabbitMQ credentials

### Production Recommendations

- Enable Kerberos for HDFS
- Enable SSL/TLS for Kafka
- Use strong credentials for RabbitMQ
- Enable Airflow authentication
- Use firewall rules to restrict access

## Monitoring and Logging

### Web UIs

- **Spark Master**: http://nole1:8080
- **HDFS Namenode**: http://nole3:9870
- **RabbitMQ**: http://airflow-master:15672
- **Airflow**: http://airflow-master:8080

### Logs Location

- **Airflow**: `$AIRFLOW_HOME/logs/`
- **Spark**: `$SPARK_HOME/logs/`
- **Celery**: Console output or configured log file
- **Application**: `final_project/logs/`

## References

For more details, see:
- [Setup Guide](archived/SETUP_GUIDE.md)
- [RabbitMQ Configuration](archived/RABBITMQ_CONFIG.md)
- [System Information](archived/SYSTEM_INFO.md)
