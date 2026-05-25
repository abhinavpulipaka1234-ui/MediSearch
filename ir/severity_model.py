import os
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
import shap
import mlflow

from pyspark.sql import SparkSession
from pyspark.ml import Pipeline
from pyspark.ml.classification import LogisticRegression
from pyspark.ml.feature import Tokenizer, HashingTF, IDF, StringIndexer, IndexToString
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
from sklearn.linear_model import LogisticRegression as SklearnLR
from sklearn.feature_extraction.text import TfidfVectorizer

plt.switch_backend('agg')

OUTPUT_DIR = "/app/frontend/doctor/public/analytics"
os.makedirs(OUTPUT_DIR, exist_ok=True)

spark = SparkSession.builder \
    .appName("MediSearch-SeverityModel") \
    .getOrCreate()
spark.sparkContext.setLogLevel("ERROR")

mlflow.set_tracking_uri("http://mlflow:5000")
mlflow.set_experiment("MediSearch-SeverityModel")

print("Loading Data for Severity Classification...")
df = spark.read.parquet("/app/data/cases/")

# Map severity string to labels
labelIndexer = StringIndexer(inputCol="severity", outputCol="label").fit(df)
df = labelIndexer.transform(df)

# Text Processing MLlib Pipeline
tokenizer = Tokenizer(inputCol="symptoms", outputCol="words")
hashingTF = HashingTF(inputCol="words", outputCol="rawFeatures", numFeatures=200)
idf = IDF(inputCol="rawFeatures", outputCol="features")
lr = LogisticRegression(maxIter=10, regParam=0.01, family="multinomial")

pipeline = Pipeline(stages=[tokenizer, hashingTF, idf, lr])

print("Splitting Data 80/20...")
trainData, testData = df.randomSplit([0.8, 0.2], seed=42)

with mlflow.start_run():
    print("Training PySpark MLlib Logistic Regression...")
    model = pipeline.fit(trainData)
    predictions = model.transform(testData)
    
    # 1. Evaluate metrics
    evaluator = MulticlassClassificationEvaluator(predictionCol="prediction", labelCol="label")
    f1 = evaluator.evaluate(predictions, {evaluator.metricName: "f1"})
    accuracy = evaluator.evaluate(predictions, {evaluator.metricName: "accuracy"})
    print(f"Test F1 Score: {f1:.4f}")
    print(f"Test Accuracy: {accuracy:.4f}")
    
    mlflow.log_metric("f1_score", f1)
    mlflow.log_metric("accuracy", accuracy)

    # 2. Confusion Matrix
    print("Computing Confusion Matrix...")
    cm = predictions.groupby('label').pivot('prediction').count().fillna(0).toPandas()
    cm = cm.set_index('label')
    cm.columns = [f"Pred_{col}" for col in cm.columns]
    
    plt.figure(figsize=(8,6))
    sns.heatmap(cm, annot=True, fmt='g', cmap='Blues')
    plt.title("Severity Model Confusion Matrix")
    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    plt.savefig(f"{OUTPUT_DIR}/severity_confusion_matrix.png")
    plt.close()
    
    mlflow.spark.log_model(model, "severity_lr_model")
    mlflow.log_artifact(f"{OUTPUT_DIR}/severity_confusion_matrix.png")

# 3. Explainability with SHAP on Pandas Sample
print("Sampling 10,000 rows to Pandas for SHAP Explanation...")
pandas_df = df.sample(fraction=0.01, seed=42).limit(10000).toPandas()

# To use SHAP cleanly on text features, we train a mirror scikit-learn model locally
vectorizer = TfidfVectorizer(max_features=200, stop_words='english')
X_sample = vectorizer.fit_transform(pandas_df['symptoms'])
y_sample = pandas_df['label']

sklearn_lr = SklearnLR(max_iter=1000, multi_class='multinomial')
sklearn_lr.fit(X_sample, y_sample)

# Generate SHAP over the linear model approximation
# Using LinearExplainer
explainer = shap.LinearExplainer(sklearn_lr, X_sample, feature_dependence="independent")
shap_values = explainer.shap_values(X_sample)

# Save SHAP Summary Plot
shap.summary_plot(shap_values, X_sample, feature_names=vectorizer.get_feature_names_out(), show=False)
plt.title("SHAP Feature Importance for Severity")
plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/severity_shap_summary.png")
plt.close()

print(f"SHAP Explanations computed and saved to {OUTPUT_DIR}/severity_shap_summary.png")
spark.stop()
