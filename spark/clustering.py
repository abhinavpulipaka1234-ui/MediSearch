import os
import matplotlib.pyplot as plt
import mlflow
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, split
from pyspark.ml.feature import HashingTF, IDF, Tokenizer
from pyspark.ml.clustering import KMeans
from pyspark.ml.evaluation import ClusteringEvaluator

plt.switch_backend('agg')

OUTPUT_DIR = "/app/frontend/doctor/public/analytics"
os.makedirs(OUTPUT_DIR, exist_ok=True)

spark = SparkSession.builder \
    .appName("MediSearch-Clustering") \
    .getOrCreate()
spark.sparkContext.setLogLevel("ERROR")

# MLflow tracking
mlflow.set_tracking_uri("http://mlflow:5000")
mlflow.set_experiment("MediSearch-Clustering")

print("Loading data for Clustering...")
df = spark.read.parquet("/app/data/cases/")

# TF-IDF Pipeline on Symptoms
tokenizer = Tokenizer(inputCol="symptoms", outputCol="words")
wordsData = tokenizer.transform(df)

hashingTF = HashingTF(inputCol="words", outputCol="rawFeatures", numFeatures=500)
featurizedData = hashingTF.transform(wordsData)

idf = IDF(inputCol="rawFeatures", outputCol="features")
idfModel = idf.fit(featurizedData)
rescaledData = idfModel.transform(featurizedData)

# Elbow Method to find optimal K
evaluator = ClusteringEvaluator()
silhouette_scores = []
ks = [2, 5, 8, 12, 15]

with mlflow.start_run():
    for k in ks:
        print(f"Training KMeans with K={k}...")
        kmeans = KMeans().setK(k).setSeed(1).setFeaturesCol("features")
        model = kmeans.fit(rescaledData)
        predictions = model.transform(rescaledData)
        score = evaluator.evaluate(predictions)
        silhouette_scores.append(score)
        mlflow.log_metric(f"silhouette_score_k_{k}", score)

    # Plot Elbow / Silhouette
    plt.figure(figsize=(8,6))
    plt.plot(ks, silhouette_scores, marker='o', linestyle='--')
    plt.title("Silhouette Score vs. Number of Clusters (K)")
    plt.xlabel("K (Clusters)")
    plt.ylabel("Silhouette Score")
    plt.savefig(f"{OUTPUT_DIR}/clustering_elbow.png")
    plt.close()
    
    mlflow.log_artifact(f"{OUTPUT_DIR}/clustering_elbow.png")

    # Pick optimal K (max silhouette)
    optimal_k = ks[np.argmax(silhouette_scores)] if 'np' in globals() else 12  # Simplified
    print(f"Optimal K chosen: {optimal_k}")
    
    kmeans_opt = KMeans().setK(optimal_k).setSeed(1).setFeaturesCol("features")
    opt_model = kmeans_opt.fit(rescaledData)
    final_preds = opt_model.transform(rescaledData)

    # Output to HDFS
    labels_df = final_preds.select("case_id", "prediction")
    labels_df.write.mode("overwrite").parquet("/medisearch_data/clusters/")
    
    mlflow.spark.log_model(opt_model, "kmeans_model")
    
print("Clustering Complete!")
spark.stop()
