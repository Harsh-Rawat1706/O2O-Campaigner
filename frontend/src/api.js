
import axios from 'axios';

export const API_BASE = (
  import.meta.env.VITE_API_BASE_URL ||
  'https://o2o-campaigner.onrender.com/api/v1'
).replace(/\/+$/, '');

const client = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

client.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('o2o_access_token');

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    const detail = error?.response?.data?.detail;

    const message =
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail.map((item) => item.msg).join(', ')
          : error.message || 'Request failed';

    if (status === 401) {
      sessionStorage.removeItem('o2o_access_token');
    }

    const errorMessage = status
      ? `${message} (${status})`
      : `${message}. If this is a browser CORS error, the backend must allow this frontend origin.`;

    return Promise.reject(new Error(errorMessage));
  },
);

export const api = {
  get: (path, config) =>
    client.get(path, config).then((response) => response.data),

  post: (path, body, config) =>
    client.post(path, body, config).then((response) => response.data),

  patch: (path, body, config) =>
    client.patch(path, body, config).then((response) => response.data),

  delete: (path, config) =>
    client.delete(path, config).then((response) =>
      response.status === 204 ? null : response.data,
    ),
};

export async function adminLogin(email, password) {
  const response = await api.post('/auth/login', {
    email,
    password,
  });

  if (!response?.access_token) {
    throw new Error('Login response did not contain an access token.');
  }

  sessionStorage.setItem('o2o_access_token', response.access_token);

  try {
    const user = await api.get('/auth/me');

    if (user?.role !== 'admin') {
      sessionStorage.removeItem('o2o_access_token');
      throw new Error('Access denied. This account is not an admin.');
    }

    return {
      access_token: response.access_token,
      token_type: response.token_type || 'bearer',
      user,
    };
  } catch (error) {
    sessionStorage.removeItem('o2o_access_token');
    throw error;
  }
}

export async function getCurrentUser() {
  return api.get('/auth/me');
}

export async function getAdminDashboard() {
  return api.get('/admin/dashboard');
}

export async function getAdminMerchants(params = {}) {
  return api.get('/admin/merchants', {
    params,
  });
}

export async function deactivateAdminMerchant(merchantId) {
  return api.delete(
    `/admin/merchants/${encodeURIComponent(merchantId)}`,
  );
}

export async function restoreAdminMerchant(merchantId) {
  return api.post(
    `/admin/merchants/${encodeURIComponent(merchantId)}/restore`,
    {},
  );
}

export async function getDeletedAdminStores() {
  return api.get('/admin/stores/deleted');
}

export async function deleteAdminStore(storeId) {
  return api.delete(
    `/admin/stores/${encodeURIComponent(storeId)}`,
  );
}

export async function restoreAdminStore(storeId) {
  return api.post(
    `/admin/stores/${encodeURIComponent(storeId)}/restore`,
    {},
  );
}

export async function reviewAdminStore(storeId, decision, reason) {
  if (!['approve', 'reject'].includes(decision)) {
    throw new Error('Decision must be approve or reject.');
  }

  if (decision === 'reject' && !reason?.trim()) {
    throw new Error('A reason is required when rejecting a store.');
  }

  const body =
    decision === 'reject'
      ? {
          decision,
          reason: reason.trim(),
        }
      : {
          decision,
        };

  return api.patch(
    `/admin/stores/${encodeURIComponent(storeId)}/verification`,
    body,
  );
}

export async function getStoreCategories() {
  return api.get('/merchant/stores/categories');
}

export function formatMoneyPaise(value) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2,
  }).format((Number(value) || 0) / 100);
}

export function formatMoneyRupees(value) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2,
  }).format(Number(value) || 0);
}

export function getBrowserLocation() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      return reject(
        new Error(
          'This browser does not support location. Enter your location manually or try another browser.',
        ),
      );
    }

    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        resolve({
          lat: coords.latitude,
          lng: coords.longitude,
          accuracy: coords.accuracy,
        });
      },
      (error) => {
        const message =
          error.code === 1
            ? 'Location permission was denied. You can try again or enter a location manually.'
            : error.code === 2
              ? 'Your location is unavailable. Try again or enter a location manually.'
              : 'Location request timed out. Try again.';

        reject(new Error(message));
      },
      {
        enableHighAccuracy: true,
        timeout: 12000,
        maximumAge: 60000,
      },
    );
  });
}
