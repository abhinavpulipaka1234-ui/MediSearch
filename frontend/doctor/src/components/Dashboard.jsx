import React from 'react';

function Dashboard() {
  const images = [
    { src: '/analytics/age_dist.png', desc: 'Patient Age Distribution (EDA)' },
    { src: '/analytics/top_conditions.png', desc: 'Top 15 Conditions Present (EDA)' },
    { src: '/analytics/severity_pie.png', desc: 'Global Severity Distribution (EDA)' },
    { src: '/analytics/top_symptoms.png', desc: 'Most Frequent NLP Extracted Symptoms (EDA)' },
    { src: '/analytics/clustering_elbow.png', desc: 'Symptom Clustering Elbow Curve (MLlib K-Means)' },
    { src: '/analytics/severity_confusion_matrix.png', desc: 'Severity Model Confusion Matrix (PySpark Logistic Regression)' },
    { src: '/analytics/severity_shap_summary.png', desc: 'SHAP Feature Importance (Explaining Severe Symptoms)' }
  ];

  return (
    <div className="animate-fade-in" style={{ padding: '1rem 0' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2rem' }}>
        <h3>Big Data Analytics Suite</h3>
        <span className="badge" style={{ background: 'rgba(59, 130, 246, 0.15)', color: 'var(--accent-primary)' }}>PySpark MLlib & Pandas Insights</span>
      </div>

      <p style={{ color: 'var(--text-secondary)', marginBottom: '3rem' }}>
        Visualizations generated directly from HDFS Parquet processing. Tracked by MLflow.
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '2rem' }}>
        {images.map((img, i) => (
          <div key={i} style={{ 
            background: 'var(--bg-tertiary)', 
            border: '1px solid var(--border)', 
            borderRadius: '16px', 
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column'
          }}>
            <div style={{ padding: '1rem 1.5rem', background: 'rgba(0,0,0,0.2)', borderBottom: '1px solid var(--border)' }}>
              <p style={{ fontWeight: 500, margin: 0 }}>{img.desc}</p>
            </div>
            
            <div style={{ padding: '1.5rem', display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '300px', background: 'white' }}>
              <img 
                src={img.src} 
                alt={img.desc} 
                style={{ maxWidth: '100%', maxHeight: '400px', objectFit: 'contain' }} 
                onError={(e) => { e.target.style.display = 'none'; e.target.parentElement.innerHTML = '<p style="color:var(--text-muted); text-align:center;">Pipeline artifact not yet generated. Run Spark EDA first.</p>'; }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default Dashboard;
