import React, { useState, useEffect, useCallback } from 'react';
import { patientApi } from '../apiClient';

function Timetable({ patientId }) {
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await patientApi(patientId).get(`/timetable/${encodeURIComponent(patientId)}`);
      setPlans(res.data);
      setError(null);
    } catch (e) {
      setError('Could not load your treatment schedule.');
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [patientId]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return <p style={{ color: 'var(--text-muted)', padding: '2rem' }}>Loading your timetable…</p>;
  }

  if (error) {
    return (
      <div className="empty-state">
        <p style={{ color: 'var(--danger)' }}>{error}</p>
        <button type="button" className="btn btn-primary" style={{ marginTop: '1rem' }} onClick={load}>
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="animate-fade-in" style={{ padding: '1rem 0' }}>
      <h2 style={{ marginBottom: '0.25rem' }}>Treatment timetable</h2>
      <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
        Day-by-day plans appear here after your doctor approves a triage report.
      </p>

      {plans.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📅</div>
          <p>No active treatment schedule yet. Complete triage and wait for physician approval.</p>
        </div>
      ) : (
        plans.map((plan) => (
          <div key={plan.plan_id} style={{ marginBottom: '2rem' }}>
            <div style={{ marginBottom: '1rem' }}>
              <span className="badge badge-approved">{plan.triage_status}</span>
              <span style={{ marginLeft: '0.75rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                Case {plan.case_id}
                {plan.diagnosis_type === 'DOCTOR' && plan.doctor_diagnosis
                  ? ` · ${plan.doctor_diagnosis}`
                  : ` · ${plan.condition_label}`}
              </span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {(plan.day_by_day_plan || []).map((day) => (
                <div
                  key={`${plan.plan_id}-${day.day}`}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'flex-start',
                    gap: '1rem',
                    padding: '1.25rem',
                    background: 'var(--bg-card)',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border)',
                  }}
                >
                  <div>
                    <h4 style={{ color: 'var(--accent-primary)', marginBottom: '0.35rem' }}>Day {day.day}</h4>
                    <ul style={{ margin: 0, paddingLeft: '1.25rem', color: 'var(--text-secondary)' }}>
                      {(day.tasks || []).map((t, i) => (
                        <li key={i} style={{ marginBottom: '0.25rem' }}>
                          {t}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <span
                    className="badge"
                    style={{
                      background:
                        day.status === 'active'
                          ? 'rgba(34, 197, 94, 0.15)'
                          : 'rgba(99, 102, 241, 0.12)',
                      color: day.status === 'active' ? 'var(--success)' : 'var(--accent-primary)',
                      border: '1px solid var(--border)',
                      flexShrink: 0,
                    }}
                  >
                    {day.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ))
      )}
    </div>
  );
}

export default Timetable;
