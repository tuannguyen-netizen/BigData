#!/bin/bash
# Fix Airflow database permission issue

set -e

echo "=========================================="
echo "FIX AIRFLOW DATABASE ISSUE"
echo "=========================================="
echo ""

# Set AIRFLOW_HOME
export AIRFLOW_HOME=~/Tuan/Project/BigData/final_project
export AIRFLOW__CORE__DAGS_FOLDER=~/Tuan/Project/BigData/final_project/dags
export AIRFLOW__CORE__LOAD_EXAMPLES=False
export PYTHONPATH=~/Tuan/Project/BigData/final_project:$PYTHONPATH

echo "AIRFLOW_HOME: $AIRFLOW_HOME"
echo ""

# Check if directory exists
if [ ! -d "$AIRFLOW_HOME" ]; then
    echo "Creating AIRFLOW_HOME directory..."
    mkdir -p "$AIRFLOW_HOME"
fi

# Check permissions
echo "Checking permissions..."
ls -ld "$AIRFLOW_HOME"

# Ensure we have write permission
if [ ! -w "$AIRFLOW_HOME" ]; then
    echo "ERROR: No write permission to $AIRFLOW_HOME"
    echo "Fixing permissions..."
    chmod 755 "$AIRFLOW_HOME"
fi

# Remove old database if exists
if [ -f "$AIRFLOW_HOME/airflow.db" ]; then
    echo "Removing old database..."
    rm -f "$AIRFLOW_HOME/airflow.db"
fi

# Remove old config if exists
if [ -f "$AIRFLOW_HOME/airflow.cfg" ]; then
    echo "Backing up old config..."
    mv "$AIRFLOW_HOME/airflow.cfg" "$AIRFLOW_HOME/airflow.cfg.backup"
fi

# Initialize database
echo ""
echo "Initializing Airflow database..."
cd "$AIRFLOW_HOME"
airflow db init

# Create admin user
echo ""
echo "Creating admin user..."
airflow users create \
  --username admin \
  --firstname Admin \
  --lastname User \
  --role Admin \
  --email admin@example.com \
  --password admin 2>/dev/null || echo "User already exists"

# Check database file
echo ""
echo "Checking database file..."
ls -lh "$AIRFLOW_HOME/airflow.db"

echo ""
echo "=========================================="
echo "✓ Setup complete!"
echo "=========================================="
echo ""
echo "To start Airflow:"
echo "  cd $AIRFLOW_HOME"
echo "  airflow standalone"
echo ""
echo "Or run webserver and scheduler separately:"
echo "  Terminal 1: airflow webserver --port 8080"
echo "  Terminal 2: airflow scheduler"
echo ""
