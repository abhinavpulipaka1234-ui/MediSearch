import React, { useEffect, useState } from 'react';
import axios from 'axios';

const API_BASE = 'http://localhost:8000';

function Queue() {
  const [queue, setQueue] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(null);

  useEffect(() => {
    fetchQueue();
    // Refresh queue passively
    const interval = setInterval(fetchQueue, 15000);
    return () => clearInterval(interval);
  }, []);

  const fetchQueue = async () => {
    try {
      const res = await axios.get(`${API_BASE}/doctor/queue`);
      setQueue(res.data);
    } catch(err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const processReport = async (report_id, action) => {
    try {
      await axios.post(`${API_BASE}/doctor/report`, { report_id, action });
      setQueue(q => q.filter(r => r.report_id !== report_id));
      setExpanded(null);
    } catch(err) {
      console.error(err);
    }
  };

  if (loading) return <div style={{ color: 'var(--text-secondary)' }}>Loading intelligent triage queue...</div>;

  return (
    <div className="animate-fade-in" style={{ padding: '1rem 0' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2rem' }}>
        <h3>Intake Queue</h3>
        <span className="badge" style={{ background: 'rgba(255,255,255,0.1)' }}>{queue.length} Pending</span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: '1.5rem' }}>
        {queue.length === 0 ? <p style={{ color: 'var(--text-muted)' }}>No pending intakes.</p> : null}
        
        {queue.map(item => {
          const isExp = expanded === item.report_id;
          const badgeClass = item.severity.toLowerCase() === 'emergency' ? 'badge-emergency' : (item.severity.toLowerCase() === 'high' ? 'badge-high' : 'badge-medium');
          
          return (
            <div key={item.report_id} 
              style={{
                background: 'var(--bg-tertiary)', border: '1px solid var(--border)', borderRadius: '12px',
                padding: '1.5rem', cursor: 'pointer', transition: 'transform 0.2s',
                transform: isExp ? 'scale(1.02)' : 'scale(1)',
                boxShadow: isExp ? 'var(--shadow-glow)' : 'var(--shadow-md)'
              }}
              onClick={() => !isExp && setExpanded(item.report_id)}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className={`badge ${badgeClass}`}>{item.severity}</span>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{item.case_id.split('-')[1] || item.case_id}</span>
              </div>
              
              <h4 style={{ marginTop: '1rem', color: 'var(--text-primary)' }}>{item.condition_label}</h4>
              <p style={{ color: 'var(--accent-primary)', fontSize: '0.9rem', marginBottom: '1rem' }}>
                IR Confidence: {(item.confidence_score * 100).toFixed(1)}%
              </p>
              
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '1rem', display: '-webkit-box', WebkitLineClamp: isExp ? 10 : 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                {item.symptoms}
              </p>

              {isExp && (
                <div className="animate-fade-in" style={{ marginTop: '1.5rem', borderTop: '1px solid var(--border)', paddingTop: '1.5rem' }}>
                  <p style={{ fontWeight: 600, marginBottom: '0.5rem' }}>Resource Allocator Suggestion:</p>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '1rem' }}>Assign priority schedule immediately.</p>
                  
                  <div style={{ display: 'flex', gap: '1rem' }}>
                    <button onClick={(e) => { e.stopPropagation(); processReport(item.report_id, 'APPROVED'); }} className="btn btn-primary" style={{ flex: 1 }}>Approve Plan</button>
                    <button onClick={(e) => { e.stopPropagation(); processReport(item.report_id, 'REJECTED'); }} className="btn btn-secondary" style={{ flex: 1, borderColor: 'var(--danger)', color: 'var(--danger)' }}>Reject</button>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  );
}

export default Queue;
