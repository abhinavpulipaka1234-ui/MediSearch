import React from 'react';
import { Link } from 'react-router-dom';

function LandingPage() {
  return (
    <div className="landing-container">
      <div className="landing-content animate-slide-up">
        <h1 className="landing-logo">MediSearch</h1>
        <p className="landing-subtitle">
          AI-Powered Medical Triage &amp; Health Intelligence Platform.
          <br />
          Get instant symptom assessment, smart diagnostics, and seamless doctor collaboration.
        </p>

        <h2 className="landing-question">How can we help you today?</h2>

        <div className="landing-buttons">
          <Link to="/patient" className="role-btn patient-btn" id="btn-patient-portal">
            <span className="role-icon">🩺</span>
            <span className="role-label">I'm a Patient</span>
            <span className="role-desc">Start symptom assessment</span>
          </Link>

          <Link to="/doctor" className="role-btn doctor-btn" id="btn-doctor-portal">
            <span className="role-icon">👨‍⚕️</span>
            <span className="role-label">I'm a Doctor</span>
            <span className="role-desc">Review triage queue</span>
          </Link>
        </div>

        <p style={{ marginTop: '3rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          Powered by BM25 Information Retrieval · PySpark Analytics · Real-time Triage
        </p>
      </div>
    </div>
  );
}

export default LandingPage;
