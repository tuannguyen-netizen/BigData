# Scripts Directory

This directory contains all shell scripts organized by purpose.

## Directory Structure

```
scripts/
├── setup/      # Setup and installation scripts
├── workers/    # Celery worker management scripts
├── checks/     # Health check and status scripts
├── fixes/      # Fix and repair scripts
└── utils/      # Utility and helper scripts
```

## Setup Scripts (`setup/`)

Scripts for initial system setup and configuration:

- **`setup_all.sh`** - Complete system setup (all nodes)
- **`setup_airflow.sh`** - Setup Airflow on master node
- **`setup_hosts.sh`** - Configure /etc/hosts for hostname resolution
- **`setup_nole1_ssh.sh`** - Setup SSH for Nole1 (Spark node)
- **`setup_nole2_ssh.sh`** - Setup SSH for Nole2 (Kafka node)
- **`setup_nole3.sh`** - Setup Nole3 (Hadoop node)
- **`setup_nole3_ssh.sh`** - Setup SSH for Nole3

**Usage Example:**
```bash
# Setup all nodes
./scripts/setup/setup_all.sh

# Setup specific node
./scripts/setup/setup_nole1_ssh.sh
```

## Worker Scripts (`workers/`)

Scripts for starting and managing Celery workers:

- **`start_kafka_worker.sh`** - Start Celery worker for Kafka node (queue: nole2)
- **`start_spark_worker.sh`** - Start Celery worker for Spark node (queue: nole1)

**Usage Example:**
```bash
# On Nole2 (Kafka machine)
./scripts/workers/start_kafka_worker.sh airflow-master

# On Nole1 (Spark machine)
./scripts/workers/start_spark_worker.sh airflow-master
```

## Health Check Scripts (`checks/`)

Scripts for checking system status and health:

- **`check_hdfs_connection.sh`** - Verify HDFS connectivity and status
- **`check_spark_status.sh`** - Check Spark Master and workers status
- **`check_spark_workers.sh`** - List active Spark workers

**Usage Example:**
```bash
# Check HDFS
./scripts/checks/check_hdfs_connection.sh

# Check Spark cluster
./scripts/checks/check_spark_status.sh
```

## Fix Scripts (`fixes/`)

Scripts for fixing common issues:

- **`fix_airflow_dags.sh`** - Fix Airflow DAG issues
- **`fix_airflow_db.sh`** - Fix Airflow database issues
- **`fix_nole3_hostname.sh`** - Fix hostname configuration for Nole3

**Usage Example:**
```bash
# Fix Airflow database
./scripts/fixes/fix_airflow_db.sh

# Fix hostname issues
./scripts/fixes/fix_nole3_hostname.sh
```

## Utility Scripts (`utils/`)

General utility and helper scripts:

- **`cleanup_airflow.sh`** - Clean up Airflow logs and temporary files
- **`deploy_spark_jobs.sh`** - Deploy Spark jobs to cluster
- **`migrate_airflow.sh`** - Migrate Airflow to new version/configuration
- **`continue_setup.sh`** - Continue interrupted setup process

**Usage Example:**
```bash
# Clean up Airflow
./scripts/utils/cleanup_airflow.sh

# Deploy Spark jobs
./scripts/utils/deploy_spark_jobs.sh
```

## Common Patterns

### Making Scripts Executable

```bash
chmod +x scripts/**/*.sh
```

### Running Scripts from Project Root

All scripts should be run from the project root directory:

```bash
cd /path/to/final_project
./scripts/setup/setup_all.sh
```

### Environment Variables

Some scripts may require environment variables. See [.env.example](../.env.example) for available options.

## Troubleshooting

If a script fails:

1. Check script permissions: `ls -l scripts/category/script.sh`
2. Check environment variables: `env | grep HDFS`
3. Check logs in the script output
4. Refer to [docs/archived/](../docs/archived/) for detailed troubleshooting

## Adding New Scripts

When adding new scripts:

1. Place in appropriate subdirectory based on purpose
2. Make executable: `chmod +x script.sh`
3. Add documentation header in script
4. Update this README
5. Test thoroughly before committing
