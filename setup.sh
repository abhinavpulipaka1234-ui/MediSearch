#!/bin/bash
set -e

echo "Building MediSearch Infrastructure & Environment Setup..."

# Create project structure
mkdir -p data db kafka spark/output ir api frontend/patient frontend/doctor hadoop/namenode hadoop/datanode mlflow pgdata

# Install Python dependencies locally for development/data gen
if ! command -v pip &> /dev/null
then
    echo "pip could not be found, attempting python3 -m pip"
    python3 -m pip install -r requirements.txt
else
    pip install -r requirements.txt
fi

python3 -m spacy download en_core_web_sm
python3 -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"

# Start Docker containers in detached mode
echo "Starting Docker containers..."
docker compose up -d zookeeper kafka namenode datanode hive-metastore postgres mlflow

# Wait for HDFS to spin up
echo "Waiting for NameNode to exit safe mode..."
sleep 20
docker exec -it $(docker ps -qf "name=namenode" -n 1) hdfs dfsadmin -safemode wait

# Wait for Postgres
echo "Waiting for Postgres to accept connections..."
sleep 10
docker exec -it $(docker ps -qf "name=postgres" -n 1) pg_isready -U admin -d medisearch

echo "Setup Complete!"
