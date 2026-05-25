import React, { useState, useEffect, useCallback } from 'react';
import { patientApi } from '../apiClient';

function SymptomLogger({ patientId }) {
  const apiPatientId = patientId;
  const api = patientApi(apiPatientId);
  const [symptom, setSymptom] = useState('');
  const [severity, setSeverity] = useState('Medium');
  const [painLevel, setPainLevel] = useState(5);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [toast, setToast] = useState(null);

  const fetchLogs = useCallback(async () => {
    try {
      const res = await api.get(`/symptoms/${encodeURIComponent(apiPatientId)}`);
      setLogs(res.data);
    } catch (err) {
      console.error('Failed to fetch logs:', err);
    } finally {
      setLoading(false);
    }
  }, [api, apiPatientId]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  const submitLog = async (e) => {
    e.preventDefault();
    if (!symptom.trim()) return;
    setSubmitting(true);

    try {
      await api.post('/symptoms', {
        patient_id: apiPatientId,
        symptoms: symptom.trim(),
        severity,
        pain_level: painLevel
      });
      setSymptom('');
      setPainLevel(5);
      showToast('Symptom logged successfully');
      await fetchLogs();
    } catch (err) {
      showToast('Failed to log symptom', 'error');
      console.error(err);
    } finally {
      setSubmitting(false);
    }
  };

  const removeLog = async (logId) => {
    try {
      await api.delete(`/symptoms/${logId}?patient_id=${encodeURIComponent(apiPatientId)}`);
      showToast('Symptom removed');
      await fetchLogs();
    } catch (err) {
      showToast('Failed to remove symptom', 'error');
      console.error(err);
    }
  };

  const severityColor = {
    'Low': 'var(--success)',
    'Medium': 'var(--warning)',
    'High': 'var(--urgency-high)',
    'Emergency': 'var(--danger)'
  };

  return (
    <div className="animate-fade-in" style={{ padding: '1rem 0' }}>
      {/* Toast */}
      {toast && (
        <div className={`toast toast-${toast.type}`}>
          {toast.message}
        </div>
      )}

      <h2 style={{ marginBottom: '0.25rem' }}>Symptom Logger</h2>
      <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem', fontSize: '0.9rem' }}>
        Log symptoms that persist in your medical record. Remove entries when symptoms resolve.
      </p>

      {/* Submit Form */}
      <form onSubmit={submitLog} style={{
        display: 'flex', flexDirection: 'column', gap: '1.25rem',
        background: 'var(--bg-card)', padding: '1.5rem',
        borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)',
        marginBottom: '2rem'
      }}>
        <div>
          <label style={{ display: 'block', marginBottom: '0.4rem', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Describe Your Symptoms
          </label>
          <textarea
            className="input-field"
            style={{ minHeight: '100px' }}
            value={symptom}
            onChange={(e) => setSymptom(e.target.value)}
            placeholder="E.g., persistent headache on the left side, mild nausea..."
            required
          />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '0.4rem', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
              Severity
            </label>
            <select
              className="input-field"
              value={severity}
              onChange={e => setSeverity(e.target.value)}
            >
              <option value="Low">Low — Mild discomfort</option>
              <option value="Medium">Medium — Affects daily activities</option>
              <option value="High">High — Severe pain</option>
              <option value="Emergency">Emergency — Immediate danger</option>
            </select>
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '0.4rem', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
              Pain Level: <strong style={{ color: 'var(--text-primary)' }}>{painLevel}/10</strong>
            </label>
            <input
              type="range"
              min="1"
              max="10"
              value={painLevel}
              onChange={e => setPainLevel(parseInt(e.target.value))}
              style={{ width: '100%', accentColor: 'var(--accent-primary)', marginTop: '0.5rem' }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              <span>Minimal</span><span>Moderate</span><span>Severe</span>
            </div>
          </div>
        </div>

        <button type="submit" className="btn btn-primary" style={{ alignSelf: 'flex-start' }} disabled={submitting || !symptom.trim()}>
          {submitting ? 'Logging...' : '📝 Log Symptom'}
        </button>
      </form>

      {/* Existing Logs */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h4>Active Symptom Entries ({logs.length})</h4>
        <button className="btn btn-secondary btn-sm" onClick={fetchLogs}>↻ Refresh</button>
      </div>

      {loading ? (
        <p style={{ color: 'var(--text-muted)' }}>Loading symptom logs...</p>
      ) : logs.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📝</div>
          <p>No symptom entries yet. Log your first symptom above.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {logs.map(log => (
            <div key={log.id} className="log-entry">
              <div style={{ flex: 1 }}>
                <p style={{ fontWeight: 500, marginBottom: '0.3rem' }}>{log.symptoms}</p>
                <div style={{ display: 'flex', gap: '1rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  <span style={{ color: severityColor[log.severity] || 'var(--text-secondary)' }}>
                    ● {log.severity}
                  </span>
                  <span>Pain: {log.pain_level}/10</span>
                  <span>{new Date(log.timestamp).toLocaleDateString('en-US', {
                    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                  })}</span>
                </div>
              </div>
              <button
                className="btn btn-danger btn-sm"
                onClick={() => removeLog(log.id)}
                title="Remove this symptom"
              >
                ✕ Remove
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default SymptomLogger;
