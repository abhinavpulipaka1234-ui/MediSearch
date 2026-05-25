import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Bell, Activity, Layers } from 'lucide-react';
import Dashboard from './components/Dashboard';
import Queue from './components/Queue';
import './index.css';

function NavHeader({ toast }) {
  const location = useLocation();
  return (
    <header className="nav-header" style={{ position: 'relative' }}>
      <div>
        <h2 className="text-gradient">MediSearch Provider</h2>
        <p className="text-secondary" style={{fontSize: '0.9rem'}}>Real-time Triage & Resource Allocation</p>
      </div>
      <nav className="nav-links" style={{ alignItems: 'center' }}>
        <Link to="/" className={`nav-link ${location.pathname === '/' ? 'active' : ''}`}><Layers size={18} style={{marginRight: '6px', verticalAlign: 'middle'}}/> Queue</Link>
        <Link to="/metrics" className={`nav-link ${location.pathname === '/metrics' ? 'active' : ''}`}><Activity size={18} style={{marginRight: '6px', verticalAlign: 'middle'}}/> Analytics (Spark)</Link>
        <div style={{ position: 'relative', marginLeft: '1rem', color: toast ? 'var(--danger)' : 'var(--text-secondary)' }}>
          <Bell size={24} />
          {toast && <div style={{ position: 'absolute', top: '-5px', right: '-5px', width: '10px', height: '10px', background: 'var(--danger)', borderRadius: '50%' }}/>}
        </div>
      </nav>
      
      {/* Escalation Toast Alert */}
      {toast && (
        <div className="animate-fade-in" style={{ 
          position: 'absolute', top: '100%', right: 0, marginTop: '1rem',
          background: 'rgba(239, 68, 68, 0.15)', border: '1px solid var(--danger)', 
          padding: '1rem', borderRadius: '8px', zIndex: 100, backdropFilter: 'blur(10px)',
          maxWidth: '350px'
        }}>
          <h4 style={{ color: 'var(--danger)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            🚨 URGENT ESCALATION
          </h4>
          <p style={{ fontSize: '0.9rem', color: '#fff' }}>{toast}</p>
        </div>
      )}
    </header>
  );
}

function App() {
  const [toast, setToast] = useState(null);

  useEffect(() => {
    // Connect to WebSocket notification stream
    const ws = new WebSocket('ws://localhost:8000/ws/notifications');
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'ESCALATION') {
        setToast(data.msg);
        setTimeout(() => setToast(null), 10000); // Hide after 10s
      }
    };

    return () => ws.close();
  }, []);

  return (
    <Router>
      <div className="app-container">
        <div className="content-wrapper animate-fade-in" style={{ maxWidth: '1400px' }}>
          <NavHeader toast={toast} />
          <main className="glass-panel" style={{flex: 1, display: 'flex', flexDirection: 'column'}}>
            <Routes>
              <Route path="/" element={<Queue />} />
              <Route path="/metrics" element={<Dashboard />} />
            </Routes>
          </main>
        </div>
      </div>
    </Router>
  );
}

export default App;
