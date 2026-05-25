import sqlite3
import pandas as pd
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, date_add, current_date

# Setup
spark = SparkSession.builder \
    .appName("MediSearch-Scheduler") \
    .getOrCreate()
spark.sparkContext.setLogLevel("ERROR")

print("Allocating Treatment Resources...")
df = spark.read.parquet("/medisearch_data/cases/")

# Rule-based logic for priority
df_scheduled = df.withColumn("priority", 
    when(col("severity") == "Emergency", 1)
    .when(col("severity") == "High", 2)
    .when(col("severity") == "Medium", 3)
    .otherwise(4)
)

# Appt times logic (Days from today)
df_scheduled = df_scheduled.withColumn("appointment_date",
    when(col("priority") == 1, current_date())
    .when(col("priority") == 2, date_add(current_date(), 1))
    .when(col("priority") == 3, date_add(current_date(), 7))
    .otherwise(date_add(current_date(), 14))
)

# Save the schedules back
df_scheduled.write.mode("overwrite").parquet("/medisearch_data/schedules/")
print("Scheduler Output Generated!")
spark.stop()
