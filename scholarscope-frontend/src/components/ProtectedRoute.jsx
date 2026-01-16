import React, { useState, useEffect } from "react";
import { Navigate } from "react-router-dom";
import { jwtDecode } from "jwt-decode";

function ProtectedRoute({ children }) {
  const [isAuthorized, setIsAuthorized] = useState(null);

  useEffect(() => {
    auth().catch(() => setIsAuthorized(false));
  }, []);

  const auth = async () => {
    const token = localStorage.getItem("access_token");

    if (!token) {
      setIsAuthorized(false);
      return;
    }

    try {
      // Optional: Check if token is expired
      const decoded = jwtDecode(token);
      const tokenExpiration = decoded.exp;
      const now = Date.now() / 1000;

      if (tokenExpiration < now) {
        await refreshToken(); // You can implement auto-refresh here later
      } else {
        setIsAuthorized(true);
      }
    } catch (error) {
      // If decoding fails (invalid token), deny access
      setIsAuthorized(false);
    }
  };

  // Simple Refresh Logic Placeholder
  const refreshToken = async () => {
    const refreshToken = localStorage.getItem("refresh_token");
    // For MVP, if access expires, we just log them out
    if (!refreshToken) {
        setIsAuthorized(false);
        return;
    }
    // You would call api.post('/v1/auth/token/refresh/') here in production
    setIsAuthorized(false); 
  };

  if (isAuthorized === null) {
    return <div className="flex justify-center items-center h-screen">Loading...</div>;
  }

  // If authorized, render the child component (Dashboard).
  // If not, redirect to Login.
  return isAuthorized ? children : <Navigate to="/login" />;
}

export default ProtectedRoute;