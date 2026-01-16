// import React, { useState } from "react";
// import axios from "axios";
// import api from '.../api'

// export default function Login() {
//     const [email, setEmail] = useState("");
//     const [password, setPassword] = useState("");
//     const [loading, setLoading] = useState(false);
//     const [error, setError] = useState("");

//     const handleLogin = async (event) => {
//         event.preventDefault()
//         setLoading(True)
//         setError('')

//         try {
//             const res = await api.post('/dj-rest-auth/login/', {email, password})
//             localStorage.setItem('access_token', res.data.access)
//             window.location.href = "/dashboard"
//         } catch (err) {
//         setError("Invalid credentials. Please try again.");
//         } finally {
//         setLoading(false);
//     }
//     } ;

//     function handleGoogleLogin() {
//         window.location.href = `${import.meta.env.VITE_API_URL}/accounts/google/login/`;
//     }

//      return (
//     <div className="min-h-screen flex items-center justify-center bg-background-light dark:bg-background-dark p-4 font-display">
//       <div className="w-full max-w-md bg-white dark:bg-slate-900 rounded-xl p-8 shadow-md">
//         <h1 className="text-2xl font-bold mb-6 text-center">Welcome Back</h1>

//         {error && <p className="text-red-500 text-center mb-4">{error}</p>}

//         <form onSubmit={handleLogin} className="flex flex-col gap-4">
//           <input
//             type="text"
//             placeholder="Email or Username"
//             className="border rounded-lg p-3"
//             value={email}
//             onChange={(e) => setEmail(e.target.value)}
//           />

//           <input
//             type="password"
//             placeholder="Password"
//             className="border rounded-lg p-3"
//             value={password}
//             onChange={(e) => setPassword(e.target.value)}
//           />

//           <button
//             type="submit"
//             disabled={loading}
//             className="bg-primary text-white rounded-lg p-3 hover:bg-primary/90 transition"
//           >
//             {loading ? "Logging in..." : "Log In"}
//           </button>
//         </form>

//         <div className="mt-6 text-center text-sm text-gray-600">OR</div>

//         <button
//           onClick={handleGoogleLogin}
//           className="mt-4 flex items-center justify-center gap-2 border rounded-lg p-3 hover:bg-gray-100 w-full"
//         >
//           <img src="https://developers.google.com/identity/images/g-logo.png" alt="Google" className="h-5" />
//           Continue with Google
//         </button>
//       </div>
//     </div>
//   );
// }

import React, { useState } from "react";
import { useNavigate } from "react-router-dom"; 
import api from "../api"; 

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

            // Store both tokens if using JWT
            localStorage.setItem("access_token", res.data.access);
            localStorage.setItem("refresh_token", res.data.refresh);
            
            // 👈 Use navigate instead of window.location for SPA feel
            navigate("/dashboard"); 
        } catch (err) {
            console.error("Login Error:", err);
            // safe navigation operator (?) prevents crash if response is undefined
            setError(err.response?.data?.non_field_errors?.[0] || "Invalid credentials. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    function handleGoogleLogin() {
        // This redirects to your Django backend which handles the Google OAuth dance
        window.location.href = `${import.meta.env.VITE_API_URL}/accounts/google/login/`;
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-slate-900 p-4 font-sans">
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
    );
}