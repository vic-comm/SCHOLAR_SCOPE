import React, { useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import api from "../api"; // Your Axios instance

const GoogleCallback = () => {
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    const handleCallback = async () => {
      // 1. Extract the "code" from the URL query params
      const searchParams = new URLSearchParams(location.search);
      const code = searchParams.get("code");

      if (!code) {
        console.error("No code found in URL");
        navigate("/login"); 
        return;
      }

      try {
        // 2. Send the code to your Backend
        // Your backend will exchange this code for a Google token,
        // log the user in, and return your Django auth token + user data.
        const res = await api.post('v1/auth/google/', {
            code: code, // Sending the code directly
        });
        const accessToken = res.data.access || res.data.key;
        
        if (!accessToken) {
            console.error("No access token found in response", res.data);
            throw new Error("Login failed: No token received");
        }

        // 2. Save consistently (match what api.js looks for)
        localStorage.setItem("access_token", accessToken);
        
        // 3. Force the header for the IMMEDIATE next request (redirect)
        api.defaults.headers.common['Authorization'] = `Bearer ${accessToken}`;

        // 4. Redirect
        const user = res.data.user;
        if (user && user.is_onboarded) {
            navigate("/dashboard");
        } else {
            navigate("/profile");
        }

      }catch (err) {
        console.error("Google Login Failed:", err);
        navigate("/login"); // Send back to login on error
      }
    };

    handleCallback();
  }, [location, navigate]);

  return (
    <div className="flex items-center justify-center min-h-screen">
      <p className="text-xl font-semibold animate-pulse">
        Processing Google Login...
      </p>
    </div>
  );
};

export default GoogleCallback;