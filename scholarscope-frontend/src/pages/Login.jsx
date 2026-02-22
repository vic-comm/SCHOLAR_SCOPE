import React, { useState } from "react";
import { useNavigate } from "react-router-dom"; 
import api from "../api"; 
import Navbar from '../components/Navbar';

export default function Login() {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    
    const navigate = useNavigate(); 

    const handleLogin = async (event) => {
        event.preventDefault();
        setLoading(true); 
        setError("");

        try {
            const res = await api.post("/v1/auth/login/", { 
                email, 
                password 
            });

            localStorage.setItem("access_token", res.data.access);
            localStorage.setItem("refresh_token", res.data.refresh);
            
            navigate("/dashboard"); 
        } catch (err) {
            console.error("Login Error:", err);
            setError(err.response?.data?.non_field_errors?.[0] || "Invalid credentials. Please try again.");
        } finally {
            setLoading(false);
        }
    };

 function handleGoogleLogin() {
    const GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth";
    const REDIRECT_URI = "http://localhost:5173/google/callback"; 
    
    const params = {
      response_type: 'code',
      client_id: import.meta.env.VITE_CLIENT_ID,
      redirect_uri: REDIRECT_URI,
      scope: 'openid profile email',
      prompt: 'select_account',
      access_type: 'offline' 
    };

    const urlParams = new URLSearchParams(params).toString();
    window.location.href = `${GOOGLE_AUTH_URL}?${urlParams}`;
  }
    return (
        <div className="min-h-screen flex flex-col bg-gray-50 dark:bg-slate-900 font-sans">
            <Navbar onFilter={() => {}} />
            <div className="flex-grow flex items-center justify-center p-4">
                <div className="w-full max-w-md bg-white dark:bg-slate-800 rounded-xl p-8 shadow-lg border border-gray-100 dark:border-slate-700">
                    <h1 className="text-2xl font-bold mb-2 text-center text-gray-900 dark:text-white">Welcome Back</h1>
                    <p className="text-center text-gray-500 dark:text-gray-400 mb-6">Sign in to access your dashboard</p>

                    {error && (
                        <div className="bg-red-50 text-red-500 text-sm p-3 rounded-lg mb-4 border border-red-100">
                            {error}
                        </div>
                    )}

                    <form onSubmit={handleLogin} className="flex flex-col gap-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Email</label>
                            <input
                                type="email" // Changed to email for better mobile keyboard support
                                required
                                className="w-full border border-gray-300 dark:border-slate-600 rounded-lg p-3 bg-transparent dark:text-white focus:ring-2 focus:ring-primary focus:outline-none"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Password</label>
                            <input
                                type="password"
                                required
                                className="w-full border border-gray-300 dark:border-slate-600 rounded-lg p-3 bg-transparent dark:text-white focus:ring-2 focus:ring-primary focus:outline-none"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                            />
                        </div>

                        <button
                            type="submit"
                            disabled={loading}
                            className="bg-blue-600 text-white font-semibold rounded-lg p-3 hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed mt-2"
                        >
                            {loading ? "Logging in..." : "Log In"}
                        </button>
                    </form>

                    <div className="relative mt-6">
                        <div className="absolute inset-0 flex items-center">
                            <span className="w-full border-t border-gray-300 dark:border-gray-600"></span>
                        </div>
                        <div className="relative flex justify-center text-sm">
                            <span className="px-2 bg-white dark:bg-slate-800 text-gray-500">Or continue with</span>
                        </div>
                    </div>

                    <button
                        type="button"
                        onClick={handleGoogleLogin}
                        className="mt-6 flex items-center justify-center gap-3 border border-gray-300 dark:border-gray-600 rounded-lg p-3 hover:bg-gray-50 dark:hover:bg-slate-700 transition w-full text-gray-700 dark:text-white font-medium bg-white dark:bg-transparent"
                    >
                        <img src="https://www.svgrepo.com/show/475656/google-color.svg" alt="Google" className="h-5 w-5" />
                        Google
                    </button>
                </div>
            </div>
        </div>
    );
}