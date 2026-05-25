import React from 'react';
import { useLocation, Link } from 'react-router-dom';

function TriageResult({ patientId }) {
  const { state } = useLocation();
  const report = state?.report;

  if (!report) {
    return (
      <div className="empty-state animate-fade-in">
        <div className="empty-state-icon">📋</div>
        <h3>No Triage Data</h3>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
          Please complete the AI assessment first.
        </p>
        <Link to="/" className="btn btn-primary">Start Assessment</Link>
      </div>
    );
  }

  const severityClass = {
    low: 'badge-low', medium: 'badge-medium',
    high: 'badge-high', emergency: 'badge-emergency'
  }[report.estimated_severity?.toLowerCase()] || 'badge-medium';

  const confidencePct = (report.confidence * 100).toFixed(1);
  const confidenceClass = report.confidence >= 0.7 ? 'confidence-high' :
    report.confidence >= 0.4 ? 'confidence-mid' : 'confidence-low';

  return (
    <div className="animate-fade-in" style={{ padding: '1rem 0' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 style={{ marginBottom: '0.25rem' }}>Triage Assessment Result</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            Based on BM25 Information Retrieval analysis
          </p>
        </div>
        <span className={`badge ${severityClass}`}>{report.estimated_severity} Priority</span>
      </div>

      {/* Low confidence warning */}
      {report.low_confidence && (
        <div style={{
          marginTop: '1.5rem', padding: '1rem 1.25rem',
          background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.25)',
          borderRadius: 'var(--radius-md)', color: 'var(--warning)'
        }}>
          ⚠️ {report.low_confidence_message}
        </div>
      )}

      {/* Main diagnosis card */}
      <div style={{
        margin: '2rem 0', padding: '1.75rem',
        background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)',
        border: '1px solid var(--border)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              AI Suggested Condition
            </p>
            <h3 className="text-accent" style={{ fontSize: '1.4rem', marginTop: '0.25rem' }}>
              {report.draft_condition}
            </h3>
          </div>
          <div style={{ textAlign: 'right' }}>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Pain Score
            </p>
            <p style={{ fontSize: '1.3rem', fontWeight: 700 }}>
              {report.pain_score}/10
            </p>
          </div>
        </div>

        {/* Confidence Meter */}
        <div style={{ marginTop: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
            <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Confidence Score</span>
            <span style={{ fontWeight: 600, fontSize: '1rem' }}>{confidencePct}%</span>
          </div>
          <div className="confidence-bar">
            <div className={`confidence-fill ${confidenceClass}`} style={{ width: `${confidencePct}%` }} />
          </div>
        </div>

        {/* Extracted Symptoms */}
        <div style={{ marginTop: '1.25rem' }}>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '0.3rem' }}>Analyzed Symptoms</p>
          <p style={{ color: 'var(--text-secondary)' }}>{report.extracted_symptoms}</p>
        </div>
      </div>

      {/* Top Conditions */}
      {report.top_conditions && report.top_conditions.length > 0 && (
        <div style={{ marginBottom: '2rem' }}>
          <h4 style={{ marginBottom: '1rem' }}>Top Matching Conditions</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {report.top_conditions.map((c, i) => (
              <div key={i} style={{
                padding: '1rem 1.25rem',
                background: i === 0 ? 'rgba(99, 102, 241, 0.08)' : 'var(--bg-card)',
                borderRadius: 'var(--radius-md)',
                border: `1px solid ${i === 0 ? 'rgba(99, 102, 241, 0.25)' : 'var(--border)'}`,
                display: 'flex', justifyContent: 'space-between', alignItems: 'center'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <span style={{
                    width: '28px', height: '28px', borderRadius: '50%',
                    background: i === 0 ? 'var(--accent-primary)' : 'var(--bg-tertiary)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: '0.8rem', fontWeight: 700, color: 'white', flexShrink: 0
                  }}>
                    {i + 1}
                  </span>
                  <span style={{ fontWeight: i === 0 ? 600 : 400 }}>{c.condition}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                  <div className="progress-bar" style={{ width: '80px' }}>
                    <div className="progress-fill" style={{ width: `${c.match_pct}%` }} />
                  </div>
                  <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', minWidth: '45px', textAlign: 'right' }}>
                    {c.match_pct}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Similar Cases */}
      {report.similar_cases && report.similar_cases.length > 0 && (
        <div style={{ marginBottom: '2rem' }}>
          <h4 style={{ marginBottom: '1rem' }}>Most Similar Historical Cases</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {report.similar_cases.map((c, i) => (
              <div key={i} style={{
                padding: '1rem 1.25rem',
                background: 'var(--bg-card)',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border)',
                borderLeft: '4px solid var(--accent-teal)'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <p style={{ fontWeight: 500, marginBottom: '0.2rem' }}>Case {c.case_id}</p>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                      Condition: <span style={{ color: 'var(--accent-teal)' }}>{c.condition}</span>
                    </p>
                  </div>
                  <span className="badge badge-teal">BM25: {c.similarity}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* CTA */}
      <div style={{ textAlign: 'center', marginTop: '2rem', padding: '1.5rem', background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)' }}>
        <p style={{ color: 'var(--warning)', marginBottom: '1rem', fontWeight: 500 }}>
          📋 Your case has been submitted to the triage queue. A doctor will review it shortly.
        </p>
        <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', flexWrap: 'wrap' }}>
          <Link to="/cases" className="btn btn-primary">View My Cases</Link>
          <Link to="/timetable" className="btn btn-secondary">Treatment Plan</Link>
          <Link to="/logger" className="btn btn-secondary">Log More Symptoms</Link>
        </div>
      </div>
    </div>
  );
}

export default TriageResult;
