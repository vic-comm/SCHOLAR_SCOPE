import React, { useState } from "react";
import axios from "axios";
import api from '.../api'

export default function Login() {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const handleLogin = async (event) => {
        event.preventDefault()
        setLoading(True)
        setError('')

        try {
            const res = await api.post('/dj-rest-auth/login/', {email, password})
            localStorage.setItem('access_token', res.data.access)
            window.location.href = "/dashboard"
        } catch (err) {
        setError("Invalid credentials. Please try again.");
        } finally {
        setLoading(false);
    }
    } ;

    function handleGoogleLogin() {
        window.location.href = `${import.meta.env.VITE_API_URL}/accounts/google/login/`;
    }

     return (
    <div className="min-h-screen flex items-center justify-center bg-background-light dark:bg-background-dark p-4 font-display">
      <div className="w-full max-w-md bg-white dark:bg-slate-900 rounded-xl p-8 shadow-md">
        <h1 className="text-2xl font-bold mb-6 text-center">Welcome Back</h1>

        {error && <p className="text-red-500 text-center mb-4">{error}</p>}

        <form onSubmit={handleLogin} className="flex flex-col gap-4">
          <input
            type="text"
            placeholder="Email or Username"
            className="border rounded-lg p-3"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />

          <input
            type="password"
            placeholder="Password"
            className="border rounded-lg p-3"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />

          <button
            type="submit"
            disabled={loading}
            className="bg-primary text-white rounded-lg p-3 hover:bg-primary/90 transition"
          >
            {loading ? "Logging in..." : "Log In"}
          </button>
        </form>

        <div className="mt-6 text-center text-sm text-gray-600">OR</div>

        <button
          onClick={handleGoogleLogin}
          className="mt-4 flex items-center justify-center gap-2 border rounded-lg p-3 hover:bg-gray-100 w-full"
        >
          <img src="https://developers.google.com/identity/images/g-logo.png" alt="Google" className="h-5" />
          Continue with Google
        </button>
      </div>
    </div>
  );
}