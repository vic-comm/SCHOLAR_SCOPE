import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api/", 
});

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

api.interceptors.request.use(
  (config) => {
    // 1. Grab the latest token from storage
    const token = localStorage.getItem("access_token") || localStorage.getItem("token");
    
    const isLoginEndpoint = config.url.includes('auth/google');

    if (token && !isLoginEndpoint) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    return config;
  },
  (error) => Promise.reject(error)
);

// Detects 401 (Unauthorized) errors and logs the user out
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      
      window.location.href = "/login";
      return Promise.reject(error);
    }
    return Promise.reject(error);
  }
);
export default api;