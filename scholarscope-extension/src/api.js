// import axios from "axios";

// const api = axios.create({
//   baseURL: import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api/", 
// });

// api.interceptors.request.use(
//   (config) => {
//     const token = localStorage.getItem("access_token");
//     if (token) {
//       config.headers.Authorization = `Bearer ${token}`;
//     }
//     return config;
//   },
//   (error) => {
//     return Promise.reject(error);
//   }
// );


// export default api;

// src/api.js
// Extension-aware Axios instance.
// In the popup: reads token from chrome.storage.local
// In the web app (dev): falls back to localStorage

import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/',
  timeout: 30_000,
});

// Attach token before every request
api.interceptors.request.use(
  (config) =>
    new Promise((resolve) => {
      if (typeof chrome !== 'undefined' && chrome.storage?.local) {
        chrome.storage.local.get(['auth_token'], (result) => {
          if (!chrome.runtime.lastError && result.auth_token) {
            config.headers.Authorization = `Bearer ${result.auth_token}`;
          }
          resolve(config);
        });
      } else {
        const token = window.localStorage.getItem('access_token');
        if (token) config.headers.Authorization = `Bearer ${token}`;
        resolve(config);
      }
    }),
  (error) => Promise.reject(error)
);

// On 401: clear stored token (UI will detect the missing token and show login)
api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      if (typeof chrome !== 'undefined' && chrome.storage?.local) {
        chrome.storage.local.remove('auth_token');
      }
    }
    return Promise.reject(error);
  }
);

export default api;