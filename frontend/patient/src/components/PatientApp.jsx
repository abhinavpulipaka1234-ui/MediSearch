import React, { useState } from 'react';
import { Routes, Route, Link, useLocation } from 'react-router-dom';
import Chatbot from './Chatbot';
import TriageResult from './TriageResult';
import SymptomLogger from './SymptomLogger';
import PatientCases from './PatientCases';
import Timetable from './Timetable';

function PatientApp() {
  const location = useLocation();

  // Simple patient ID — persisted in sessionStorage
  const [patientId] = useState(() => {
    let pid = sessionStorage.getItem('patient_id');
    if (!pid) {
      pid = `patient_${Math.floor(Math.random() * 100000)}`;
      sessionStorage.setItem('patient_id', pid);
    }
    return pid;
  });

  const currentPath = location.pathname;

  return (
    <div className="app-container">
      <div className="content-wrapper animate-fade-in">
        <header className="nav-header">
          <div>
            <h2 className="text-gradient" style={{ marginTop: '0.25rem' }}>MediSearch Patient</h2>
            <p className="text-secondary" style={{ fontSize: '0.85rem' }}>
              AI Triage &amp; Health Tracking · ID: {patientId.slice(-6)}
            </p>
          </div>
          <nav className="nav-links">
            <Link to="/" className={`nav-link ${currentPath === '/' ? 'active' : ''}`}>
              💬 AI Triage
            </Link>
            <Link to="/cases" className={`nav-link ${currentPath === '/cases' ? 'active' : ''}`}>
              📋 My Cases
            </Link>
            <Link to="/logger" className={`nav-link ${currentPath === '/logger' ? 'active' : ''}`}>
              📝 Symptom Log
            </Link>
            <Link to="/timetable" className={`nav-link ${currentPath === '/timetable' ? 'active' : ''}`}>
              📅 Treatment Plan
            </Link>
          </nav>
        </header>

        <main className="glass-panel" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <Routes>
            <Route path="/" element={<Chatbot patientId={patientId} />} />
            <Route path="/result" element={<TriageResult patientId={patientId} />} />
            <Route path="/cases" element={<PatientCases patientId={patientId} />} />
            <Route path="/logger" element={<SymptomLogger patientId={patientId} />} />
            <Route path="/timetable" element={<Timetable patientId={patientId} />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

export default PatientApp;
