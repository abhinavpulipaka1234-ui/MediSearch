import React, { useState, useEffect } from 'react';
import { patientApi } from '../apiClient';

function PatientCases({ patientId }) {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchCases();
  }, [patientId]);

  const fetchCases = async () => {
    try {
      const res = await patientApi(patientId).get(`/patient/${encodeURIComponent(patientId)}/cases`);
      setCases(res.data);
      setError(null);
    } catch (err) {
      setError('Failed to load your cases. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const severityBadge = (sev) => {
    const cls = {
      'Low': 'badge-low', 'Medium': 'badge-medium',
      'High': 'badge-high', 'Emergency': 'badge-emergency'
    }[sev] || 'badge-medium';
    return <span className={`badge ${cls}`}>{sev}</span>;
  };

  const statusBadge = (status) => {
    const cls = {
      'PENDING': 'badge-pending', 'APPROVED': 'badge-approved', 'REJECTED': 'badge-rejected'
    }[status] || 'badge-info';
    return <span className={`badge ${cls}`}>{status}</span>;
  };

  if (loading) return <p style={{ color: 'var(--text-muted)', padding: '2rem' }}>Loading your cases...</p>;

  if (error) return (
    <div className="empty-state">
      <div className="empty-state-icon">⚠️</div>
      <p style={{ color: 'var(--danger)' }}>{error}</p>
      <button className="btn btn-primary" style={{ marginTop: '1rem' }} onClick={fetchCases}>Retry</button>
    </div>
  );

  return (
    <div className="animate-fade-in" style={{ padding: '1rem 0' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h2 style={{ marginBottom: '0.25rem' }}>My Cases</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            Your triage history — only you can see these
          </p>
        </div>
        <span className="badge badge-info">{cases.length} Total</span>
      </div>

      {cases.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📋</div>
          <p>No cases yet. Complete an AI triage to create your first case.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {cases.map((c, idx) => (
            <div key={c.case_id || idx}
              className="card card-interactive"
              onClick={() => setExpanded(expanded === c.case_id ? null : c.case_id)}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
                <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                  {severityBadge(c.severity)}
                  {statusBadge(c.status)}
                </div>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  {c.timestamp ? new Date(c.timestamp).toLocaleDateString('en-US', {
                    month: 'short', day: 'numeric', year: 'numeric'
                  }) : ''}
                </span>
              </div>

              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginTop: '1rem' }}>
                {c.diagnosis_type === 'DOCTOR' ? "Doctor's Diagnosis" : 'AI Triage Suggestion'}
              </p>
              <h4 style={{ marginTop: '0.35rem', color: 'var(--text-primary)' }}>
                {c.diagnosis_type === 'DOCTOR' ? c.doctor_diagnosis : c.condition_label}
              </h4>

              {c.diagnosis_type === 'DOCTOR' && (
                <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '0.35rem' }}>
                  AI had suggested: {c.condition_label}
                </p>
              )}

              <p style={{
                color: 'var(--text-secondary)', fontSize: '0.9rem', marginTop: '0.5rem',
                display: '-webkit-box', WebkitLineClamp: expanded === c.case_id ? 20 : 2,
                WebkitBoxOrient: 'vertical', overflow: 'hidden'
              }}>
                {c.symptoms}
              </p>

              {expanded === c.case_id && (
                <div className="animate-fade-in" style={{ marginTop: '1rem', borderTop: '1px solid var(--border)', paddingTop: '1rem' }}>
                  {/* Confidence */}
                  {c.confidence_score != null && (
                    <div style={{ marginBottom: '1rem' }}>
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Confidence: </span>
                      <span style={{ fontWeight: 600 }}>{(c.confidence_score * 100).toFixed(1)}%</span>
                    </div>
                  )}

                  {/* Doctor notes */}
                  {c.doctor_notes && (
                    <div style={{
                      padding: '1rem', marginBottom: '1rem',
                      background: 'rgba(20, 184, 166, 0.08)',
                      border: '1px solid rgba(20, 184, 166, 0.2)',
                      borderRadius: 'var(--radius-md)'
                    }}>
                      <p style={{ fontSize: '0.8rem', color: 'var(--accent-teal)', marginBottom: '0.3rem', fontWeight: 600 }}>
                        Doctor's Notes
                      </p>
                      <p style={{ fontSize: '0.9rem' }}>{c.doctor_notes}</p>
                    </div>
                  )}

                  {/* Rejection note */}
                  {c.status === 'REJECTED' && c.reject_note && (
                    <div style={{
                      padding: '1rem', marginBottom: '1rem',
                      background: 'rgba(239, 68, 68, 0.08)',
                      border: '1px solid rgba(239, 68, 68, 0.2)',
                      borderRadius: 'var(--radius-md)'
                    }}>
                      <p style={{ fontSize: '0.8rem', color: 'var(--danger)', marginBottom: '0.3rem', fontWeight: 600 }}>
                        Doctor's Feedback (Report Returned)
                      </p>
                      <p style={{ fontSize: '0.9rem' }}>{c.reject_note}</p>
                    </div>
                  )}

                  {/* Doctor severity override */}
                  {c.doctor_severity && c.doctor_severity !== c.severity && (
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                      Doctor adjusted severity: <strong style={{ color: 'var(--accent-teal)' }}>{c.doctor_severity}</strong> (AI: {c.severity})
                    </p>
                  )}

                  {/* Top conditions */}
                  {c.top_conditions && c.top_conditions.length > 0 && (
                    <div style={{ marginTop: '0.5rem' }}>
                      <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '0.5rem' }}>Top Matching Conditions:</p>
                      {c.top_conditions.map((tc, i) => (
                        <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.4rem 0', fontSize: '0.85rem' }}>
                          <span>{tc.condition}</span>
                          <span style={{ color: 'var(--text-muted)' }}>{tc.match_pct}%</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default PatientCases;
