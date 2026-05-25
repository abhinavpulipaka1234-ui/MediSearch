import os
import uuid
import datetime
import random
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

NUM_RECORDS = 1_000_000
OUTPUT_DIR = "data/cases"

# Define 10 Condition Categories and specific condition labels
CONDITIONS = {
    "Respiratory": ["Asthma", "COVID-19", "Bronchitis", "Pneumonia", "COPD"],
    "Cardiovascular": ["Hypertension", "Heart Failure", "Arrhythmia", "Myocardial Infarction"],
    "Gastrointestinal": ["GERD", "IBS", "Peptic Ulcer", "Gastroenteritis", "Crohn's Disease"],
    "Neurological": ["Migraine", "Epilepsy", "Parkinson's Disease", "Multiple Sclerosis"],
    "Musculoskeletal": ["Osteoarthritis", "Rheumatoid Arthritis", "Gout", "Muscle Strain"],
    "Endocrine": ["Type 2 Diabetes", "Hypothyroidism", "Hyperthyroidism"],
    "Dermatological": ["Eczema", "Psoriasis", "Acne", "Dermatitis"],
    "Psychiatric": ["Major Depressive Disorder", "Generalized Anxiety Disorder", "Schizophrenia"],
    "Infectious": ["Influenza", "Malaria", "Dengue", "Tuberculosis"],
    "Urological": ["UTI", "Kidney Stones", "BPH"]
}

# ~100 realistic symptom descriptions (we combine them to form the ~500 vocab)
SYMPTOM_POOL = {
    "Respiratory": ["shortness of breath", "wheezing", "dry cough", "productive cough with green sputum", "chest tightness", "difficulty breathing on exertion", "anosmia", "sore throat"],
    "Cardiovascular": ["chest pain radiating to left arm", "palpitations", "dizziness on standing", "swelling in lower extremities", "racing heartbeat", "crushing chest pressure"],
    "Gastrointestinal": ["acid reflux", "heartburn after meals", "abdominal cramping", "watery diarrhea", "bloody stool", "nausea and vomiting", "loss of appetite"],
    "Neurological": ["throbbing headache", "aura before headache", "unilateral weakness", "facial drooping", "tremor in resting hands", "tingling in fingers"],
    "Musculoskeletal": ["joint stiffness in the morning", "swollen red joints", "sharp lower back pain", "muscle spasms", "limited range of motion in knee"],
    "Endocrine": ["excessive thirst", "frequent urination", "unexplained weight loss", "fatigue", "cold intolerance", "heat intolerance", "bulging eyes"],
    "Dermatological": ["itchy red rash", "scaly silver plaques", "cystic facial lesions", "hives after eating", "blistering skin"],
    "Psychiatric": ["persistent feelings of sadness", "loss of interest in hobbies", "racing thoughts", "insomnia", "auditory hallucinations", "panic attacks"],
    "Infectious": ["high grade fever", "chills and rigors", "night sweats", "body aches", "fatigue"],
    "Urological": ["burning sensation during urination", "frequent urge to urinate", "flank pain radiating to groin", "blood in urine"]
}

SEVERITIES = ["Low", "Medium", "High", "Emergency"]

def generate_cases(num_records):
    print(f"Generating {num_records} synthetic medical cases...")
    
    # Pre-generate IDs to speed things up
    case_ids = [str(uuid.uuid4()) for _ in range(num_records)]
    
    # Ages normal distribution between 18 and 90
    ages = np.random.normal(loc=55, scale=18, size=num_records).astype(int)
    ages = np.clip(ages, 18, 95)
    
    # Timestamps (random over the past year)
    now = datetime.datetime.now()
    timestamps = [now - datetime.timedelta(days=random.randint(0, 365), hours=random.randint(0, 24)) for _ in range(num_records)]
    
    # Choose random category
    categories = list(CONDITIONS.keys())
    chosen_categories = np.random.choice(categories, size=num_records)
    
    condition_labels = []
    symptoms = []
    severities = []
    
    for cat in chosen_categories:
        cond = random.choice(CONDITIONS[cat])
        condition_labels.append(cond)
        
        # Pick 2-4 symptoms matching the category mixed with 1 random general symptom
        num_symps = random.randint(2, 4)
        cat_symps = random.sample(SYMPTOM_POOL[cat], min(num_symps, len(SYMPTOM_POOL[cat])))
        
        # Add random noise symptom
        noise_cat = random.choice(categories)
        noise_symp = random.choice(SYMPTOM_POOL[noise_cat])
        cat_symps.append(noise_symp)
        
        symptoms.append(", ".join(cat_symps))
        
        # Map severity logically
        if cond in ["Myocardial Infarction", "Stroke", "Heart Failure"]:
            sev = random.choices(SEVERITIES, weights=[0.0, 0.1, 0.4, 0.5])[0]
        elif cond in ["COVID-19", "Pneumonia", "Kidney Stones"]:
            sev = random.choices(SEVERITIES, weights=[0.1, 0.4, 0.4, 0.1])[0]
        else:
            sev = random.choices(SEVERITIES, weights=[0.6, 0.3, 0.08, 0.02])[0]
        severities.append(sev)

    # Output using PyArrow Map
    print("Building PyArrow Table...")
    table = pa.table({
        'case_id': case_ids,
        'patient_age': ages.tolist(),
        'symptoms': symptoms,
        'condition_label': condition_labels,
        'severity': severities,
        'timestamp': [ts.isoformat() for ts in timestamps],
        'category_partition': chosen_categories.tolist()
    })

    print(f"Writing partitioned Parquet files to {OUTPUT_DIR}...")
    pq.write_to_dataset(
        table,
        root_path=OUTPUT_DIR,
        partition_cols=['category_partition'],
        basename_template='cases_{i}.parquet'
    )
    print("Done!")

if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    generate_cases(NUM_RECORDS)
