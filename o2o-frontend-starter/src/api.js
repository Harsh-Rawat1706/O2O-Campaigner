import axios from 'axios';

// Change this through .env; keep the backend untouched.
export const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'https://o2o-campaigner.onrender.com/api/v1').replace(/\/$/, '');
const client = axios.create({ baseURL: API_BASE, headers: { 'Content-Type': 'application/json' } });
client.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('o2o_access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});
client.interceptors.response.use((r) => r, (error) => {
  const status = error?.response?.status;
  const detail = error?.response?.data?.detail;
  const message = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map(x => x.msg).join(', ') : error.message || 'Request failed';
  if (status === 401) sessionStorage.removeItem('o2o_access_token');
  return Promise.reject(new Error(status ? `${message} (${status})` : `${message}. If this is a browser CORS error, the backend must allow this frontend origin.`));
});
export const api = {
  get: (path, config) => client.get(path, config).then(r => r.data),
  post: (path, body, config) => client.post(path, body, config).then(r => r.data),
  patch: (path, body, config) => client.patch(path, body, config).then(r => r.data),
  delete: (path, config) => client.delete(path, config).then(r => r.status === 204 ? null : r.data),
};
export function formatMoneyPaise(value) { return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 }).format((Number(value) || 0) / 100); }
export function formatMoneyRupees(value) { return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 }).format(Number(value) || 0); }
export function getBrowserLocation() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) return reject(new Error('This browser does not support location. Enter your location manually or try another browser.'));
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => resolve({ lat: coords.latitude, lng: coords.longitude, accuracy: coords.accuracy }),
      (e) => reject(new Error(e.code === 1 ? 'Location permission was denied. You can try again or enter a location manually.' : e.code === 2 ? 'Your location is unavailable. Try again or enter a location manually.' : 'Location request timed out. Try again.')),
      { enableHighAccuracy: true, timeout: 12000, maximumAge: 60000 },
    );
  });
}
