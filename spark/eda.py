# spark/eda.py
import os
import matplotlib.pyplot as plt
import seaborn as sns
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, explode, split, count, avg, length, size

# Use agg without graphical backend
plt.switch_backend('agg')

# Configure Output Dirt
OUTPUT_DIR = "/app/frontend/doctor/public/analytics"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Start Spark
spark = SparkSession.builder \
    .appName("MediSearch-EDA") \
    .getOrCreate()

spark.sparkContext.setLogLevel("ERROR")

print("Starting MediSearch PySpark EDA on 1M Records...")
# Load Parquet
# Inside Docker, we mount data, or load via HDFS
df = spark.read.parquet("/app/data/cases/")

print(f"Total rows loaded: {df.count()}")

# ================================
# KPI 1: Age Distribution
# ================================
print("Computing Age Distribution...")
age_counts = df.groupBy("patient_age").count().orderBy("patient_age").toPandas()
plt.figure(figsize=(10,6))
sns.barplot(data=age_counts, x="patient_age", y="count", color='skyblue')
plt.title("Patient Age Distribution")
plt.xticks(rotation=90)
plt.savefig(f"{OUTPUT_DIR}/age_dist.png")
plt.close()

# ================================
# KPI 2: Top Conditions
# ================================
print("Computing Top Conditions...")
top_conds = df.groupBy("condition_label").count().orderBy(col("count").desc()).limit(15).toPandas()
plt.figure(figsize=(12,6))
sns.barplot(data=top_conds, y="condition_label", x="count", palette="viridis")
plt.title("Top 15 Medical Conditions")
plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/top_conditions.png")
plt.close()

# ================================
# KPI 3: Severity Breakdown
# ================================
print("Computing Severity Breakdown...")
sev_counts = df.groupBy("severity").count().toPandas()
plt.figure(figsize=(8,8))
plt.pie(sev_counts["count"], labels=sev_counts["severity"], autopct="%1.1f%%", colors=["#2ECC71", "#F1C40F", "#E67E22", "#E74C3C"])
plt.title("Overall Severity Breakdown")
plt.savefig(f"{OUTPUT_DIR}/severity_pie.png")
plt.close()

# ================================
# KPI 4: Top Symptoms
# ================================
print("Computing Term Frequency (Symptoms)...")
# split symptoms column and explode
symptoms_df = df.withColumn("symptom", explode(split(col("symptoms"), ",\\s*")))
top_symps = symptoms_df.groupBy("symptom").count().orderBy(col("count").desc()).limit(20).toPandas()
plt.figure(figsize=(10,8))
sns.barplot(data=top_symps, y="symptom", x="count", palette="magma")
plt.title("Top 20 Most Frequent Symptoms")
plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/top_symptoms.png")
plt.close()

# Other KPIs are processed similarly (left out for brevity, producing the core files for now)
print(f"EDA Complete. Dashboards outputted to {OUTPUT_DIR}")
spark.stop()
