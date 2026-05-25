import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import PatientApp from './components/PatientApp';
import './index.css';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/*" element={<PatientApp />} />
      </Routes>
    </Router>
  );
}

export default App;
