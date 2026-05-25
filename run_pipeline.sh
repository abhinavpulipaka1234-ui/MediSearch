#!/bin/bash
set -e

echo "======================================"
echo "    MediSearch Full Pipeline Runner   "
echo "======================================"

echo "Starting dependent services (HDFS, Postgres, Kafka, Zookeeper, MLflow)..."
docker compose up -d zookeeper kafka namenode datanode postgres mlflow hive-metastore
sleep 15

echo "1. Generating 1M Synthetic Cases to ./data..."
python3 data/generate_cases.py

echo "2. Ingesting Data to HDFS..."
docker exec -it medisearch-namenode-1 hdfs dfs -mkdir -p /medisearch/cases/
docker cp ./data/cases/ medisearch-namenode-1:/tmp/cases/
docker exec -it medisearch-namenode-1 bash -c "hdfs dfs -put -f /tmp/cases/* /medisearch/cases/"

echo "Installing ML dependencies inside Spark Container..."
docker compose up -d spark-master
sleep 10
docker exec -it -u 0 medisearch-spark-master-1 pip install mlflow scikit-learn shap seaborn matplotlib pandas numpy pyarrow

echo "3. Running Spark EDA..."
docker exec -it medisearch-spark-master-1 spark-submit /app/spark/eda.py

echo "4. Running Spark Clustering..."
docker exec -it medisearch-spark-master-1 spark-submit /app/spark/clustering.py

echo "5. Building Information Retrieval Index..."
python3 ir/inverted_index.py

echo "6. Training Severity Machine Learning Model..."
docker exec -it medisearch-spark-master-1 spark-submit /app/ir/severity_model.py

echo "7. Starting the APIs and Frontends..."
docker compose up -d backend-api patient-frontend doctor-frontend

echo "Pipeline Complete! Navigate to localhost:5173 (Patient) and localhost:5174 (Doctor)"
