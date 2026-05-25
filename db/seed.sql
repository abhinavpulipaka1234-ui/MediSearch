TRUNCATE TABLE symptom_logs CASCADE;
TRUNCATE TABLE treatment_plans CASCADE;
TRUNCATE TABLE triage_reports CASCADE;
TRUNCATE TABLE cases CASCADE;
TRUNCATE TABLE patients CASCADE;

INSERT INTO patients (name, age, gender) VALUES
  ('John Doe', 45, 'Male'),
  ('Jane Smith', 32, 'Female'),
  ('Carlos Ray', 29, 'Male'),
  ('Elena Silva', 60, 'Female'),
  ('Mohammed Al Fayed', 51, 'Male');

INSERT INTO cases (case_id, patient_id, patient_age, symptoms, condition_label, severity, timestamp) VALUES
  ('case_seed_1', 'patient_1', 45, 'Severe headache with aura, nausea, sensitivity to light', 'Migraine', 'Medium', NOW() - interval '2 days'),
  ('case_seed_2', 'patient_2', 32, 'Persistent cough, fever, body aches, fatigue', 'Influenza', 'Medium', NOW() - interval '1 day'),
  ('case_seed_3', 'patient_3', 29, 'Mild chest discomfort after exercise, shortness of breath', 'Exercise-induced asthma', 'Low', NOW()),
  ('case_seed_4', 'patient_1', 45, 'Burning sensation during urination, frequent urge to urinate', 'UTI', 'Low', NOW() - interval '5 days'),
  ('case_seed_5', 'patient_4', 60, 'Joint stiffness in the morning, swollen red joints', 'Rheumatoid Arthritis', 'Medium', NOW() - interval '3 days');

INSERT INTO triage_reports (case_id, status, confidence_score, relevant_historical_cases, diagnosis_type) VALUES
  ('case_seed_1', 'APPROVED', 0.82, '[{"case_id":"hist_1","similarity":0.85,"condition":"Migraine"}]', 'AI'),
  ('case_seed_2', 'PENDING', 0.78, '[{"case_id":"hist_2","similarity":0.79,"condition":"Influenza"}]', 'AI'),
  ('case_seed_3', 'PENDING', 0.65, '[{"case_id":"hist_3","similarity":0.62,"condition":"Exercise-induced asthma"}]', 'AI'),
  ('case_seed_4', 'APPROVED', 0.91, '[{"case_id":"hist_4","similarity":0.90,"condition":"UTI"}]', 'AI'),
  ('case_seed_5', 'PENDING', 0.74, '[{"case_id":"hist_5","similarity":0.72,"condition":"Rheumatoid Arthritis"}]', 'AI');

INSERT INTO symptom_logs (patient_id, case_id, symptoms, severity, pain_level, timestamp) VALUES
  ('patient_1', 'case_seed_1', 'Persistent throbbing headache on left side', 'Medium', 6, NOW() - interval '2 days'),
  ('patient_1', 'case_seed_1', 'Nausea and light sensitivity', 'Medium', 5, NOW() - interval '1 day'),
  ('patient_2', 'case_seed_2', 'Dry cough worsening at night', 'Medium', 4, NOW() - interval '1 day'),
  ('patient_3', 'case_seed_3', 'Shortness of breath during exercise', 'Low', 3, NOW());

-- Treatment schedules for approved triage (patient timetable demo)
INSERT INTO treatment_plans (triage_report_id, day_by_day_plan, status)
SELECT tr.id,
  '[
    {"day": 1, "tasks": ["Begin migraine care plan", "Take prescribed medication", "Rest in dark room"], "status": "active"},
    {"day": 2, "tasks": ["Continue medication", "Hydrate"], "status": "pending"},
    {"day": 3, "tasks": ["Symptom diary check-in"], "status": "pending"},
    {"day": 7, "tasks": ["Follow-up with physician"], "status": "pending"}
  ]'::jsonb,
  'ACTIVE'
FROM triage_reports tr WHERE tr.case_id = 'case_seed_1';

INSERT INTO treatment_plans (triage_report_id, day_by_day_plan, status)
SELECT tr.id,
  '[
    {"day": 1, "tasks": ["Begin UTI treatment protocol", "Complete antibiotic course"], "status": "active"},
    {"day": 3, "tasks": ["Increase fluid intake"], "status": "pending"},
    {"day": 7, "tasks": ["Lab follow-up if symptoms persist"], "status": "pending"}
  ]'::jsonb,
  'ACTIVE'
FROM triage_reports tr WHERE tr.case_id = 'case_seed_4';
