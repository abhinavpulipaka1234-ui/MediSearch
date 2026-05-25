-- db/schema.sql

CREATE TABLE patients (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    age INT,
    gender VARCHAR(10)
);

CREATE TABLE doctors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    specialty VARCHAR(100)
);

CREATE TABLE cases (
    case_id VARCHAR(50) PRIMARY KEY,
    patient_id VARCHAR(50) NOT NULL,
    patient_age INT,
    symptoms TEXT,
    condition_label VARCHAR(100),
    severity VARCHAR(20),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE triage_reports (
    id SERIAL PRIMARY KEY,
    case_id VARCHAR(50) REFERENCES cases(case_id),
    doctor_id INT REFERENCES doctors(id),
    status VARCHAR(20) DEFAULT 'PENDING',
    confidence_score FLOAT,
    relevant_historical_cases JSONB,
    top_conditions JSONB,
    -- Doctor custom diagnosis fields
    doctor_diagnosis VARCHAR(200),
    doctor_severity VARCHAR(20),
    doctor_notes TEXT,
    diagnosis_type VARCHAR(20) DEFAULT 'AI',
    -- reject note
    reject_note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE treatment_plans (
    id SERIAL PRIMARY KEY,
    triage_report_id INT REFERENCES triage_reports(id),
    day_by_day_plan JSONB,
    status VARCHAR(20) DEFAULT 'ACTIVE'
);

CREATE TABLE symptom_logs (
    id SERIAL PRIMARY KEY,
    patient_id VARCHAR(50) NOT NULL,
    case_id VARCHAR(50) REFERENCES cases(case_id),
    symptoms TEXT,
    severity VARCHAR(20),
    pain_level INT DEFAULT 5,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    removed_at TIMESTAMP DEFAULT NULL
);
