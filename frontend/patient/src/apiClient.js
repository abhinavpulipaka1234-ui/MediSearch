import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

export function patientApi(patientId) {
  return axios.create({
    baseURL: API_BASE,
    headers: {
      'X-User-Role': 'patient',
      'X-User-Id': patientId,
    },
  });
}

export function doctorApi() {
  return axios.create({
    baseURL: API_BASE,
    headers: {
      'X-User-Role': 'doctor',
      'X-User-Id': 'doctor_1',
    },
  });
}

export { API_BASE };
