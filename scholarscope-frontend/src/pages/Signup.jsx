import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Eye, EyeOff, Loader2, School } from "lucide-react"; 
import api from "../api";

export default function SignUp() {
    const navigate = useNavigate();
    const [formData, setFormData] = useState({
        full_name: "",
        email: "",
        password1: "",
        password2: "",
    });
    const [loading, setLoading] = useState(false);
    const [showPassword, setShowPassword] = useState(false);
    const [error, setError] = useState("");

    const handleChange = (event) => {
        setFormData({ ...formData, [event.target.name]: event.target.value });
    };

    function handleGoogleLogin() {
        const GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth";
        const REDIRECT_URI = "http://localhost:5173/google/callback"; 
        
        const params = {
            response_type: 'code',
            client_id: import.meta.env.VITE_CLIENT_ID, // Ensure this matches .env
            redirect_uri: REDIRECT_URI,
            scope: 'openid profile email',
            prompt: 'select_account',
            access_type: 'offline'
        };

        const urlParams = new URLSearchParams(params).toString();
        window.location.href = `${GOOGLE_AUTH_URL}?${urlParams}`;
    }

    const handleSubmit = async (event) => {
        event.preventDefault();
        setLoading(true);
        setError("");

        // Client-side validation
        if (formData.password1 !== formData.password2) {
            setError("Passwords do not match");
            setLoading(false);
            return;
        }

        try {
            // Note: dj-rest-auth registration usually requires username. 
            // We map email to username here if your User model uses email as username.
            const response = await api.post("v1/auth/registration/", {
                username: formData.email, 
                email: formData.email,
                password: formData.password1,
                password_confirm: formData.password2, // Django often expects 'password_confirm' or 'password2' depending on serializer
                first_name: formData.full_name.split(" ")[0], // Optional splitting
                last_name: formData.full_name.split(" ").slice(1).join(" ") || "",
            });

            // Store tokens if returned immediately (depends on backend config)
            if (response.data.access) {
                localStorage.setItem("access_token", response.data.access);
                localStorage.setItem("refresh_token", response.data.refresh);
                navigate("/profile");
            } else {
                // If email verification is mandatory, backend might not return tokens yet
                navigate("/login"); 
            }
        } catch (err) {
            console.error("Signup Error:", err);
            if (err.response?.data) {
                const data = err.response.data;
                // Grab the first available error message
                const firstError = 
                    data.email?.[0] || 
                    data.username?.[0] || 
                    data.password?.[0] || 
                    data.non_field_errors?.[0] || 
                    data.detail || 
                    "Signup failed. Please check your details.";
                setError(firstError);
            } else {
                setError("Network error. Please try again later.");
            }
        } finally {
            setLoading(false);
        }
    };

    const handleGoogleSuccess = async (credentialResponse) => {
        setLoading(true);
        setError("");

        try {
            const { credential } = credentialResponse;
            // Send the ID token to your backend
            const response = await api.post("v1/auth/google/", {
                access_token: credential, // dj-rest-auth Google provider usually expects 'access_token' or 'id_token'
            });

            if (response.data.access) {
                localStorage.setItem("access_token", response.data.access);
                localStorage.setItem("refresh_token", response.data.refresh);
                navigate("/profile");
            }
        } catch (err) {
            console.error("Google Login Error:", err);
            setError("Google login failed. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-slate-950 p-4 font-display">
            <div className="w-full max-w-md bg-white dark:bg-slate-900 p-8 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-800">
                <div className="flex flex-col items-center mb-6">
                    <div className="flex size-12 items-center justify-center text-primary bg-primary/10 rounded-full mb-4">
                        <School className="w-6 h-6" />
                    </div>
                    <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Create Account</h1>
                    <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">Start your scholarship journey today.</p>
                </div>

                {error && (
                    <div className="mb-6 p-3 bg-red-50 dark:bg-red-900/20 border border-red-100 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-sm text-center">
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Full Name</label>
                        <input
                            name="full_name"
                            value={formData.full_name}
                            onChange={handleChange}
                            placeholder="John Doe"
                            className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 dark:text-white"
                            required
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Email</label>
                        <input
                            name="email"
                            type="email"
                            value={formData.email}
                            onChange={handleChange}
                            placeholder="you@example.com"
                            className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 dark:text-white"
                            required
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Password</label>
                        <div className="relative">
                            <input
                                name="password1"
                                type={showPassword ? "text" : "password"}
                                value={formData.password1}
                                onChange={handleChange}
                                placeholder="Min 8 characters"
                                className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 dark:text-white pr-10"
                                required
                                minLength={8}
                            />
                            <button
                                type="button"
                                onClick={() => setShowPassword(!showPassword)}
                                className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600"
                            >
                                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                            </button>
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Confirm Password</label>
                        <input
                            name="password2"
                            type="password"
                            value={formData.password2}
                            onChange={handleChange}
                            placeholder="Confirm password"
                            className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-transparent px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 dark:text-white"
                            required
                        />
                    </div>

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full h-11 bg-primary text-white font-bold rounded-lg hover:bg-primary/90 transition flex items-center justify-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed"
                    >
                        {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                        {loading ? "Creating..." : "Sign Up"}
                    </button>
                </form>

                <div className="relative my-6">
                    <div className="absolute inset-0 flex items-center">
                        <div className="w-full border-t border-slate-200 dark:border-slate-700"></div>
                    </div>
                    <div className="relative flex justify-center text-xs uppercase">
                        <span className="bg-white dark:bg-slate-900 px-2 text-slate-500">Or continue with</span>
                    </div>
                </div>

                <div className="flex justify-center">
                    <button 
                        onClick={handleGoogleLogin}
                        className="flex w-full items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                    >
                        <img src="https://www.svgrepo.com/show/475656/google-color.svg" className="h-5 w-5" alt="Google" />
                        Sign in with Google
                    </button>
                </div>

                <p className="mt-6 text-center text-sm text-slate-600 dark:text-slate-400">
                    Already have an account?{" "}
                    <Link to="/login" className="font-bold text-primary hover:underline">
                        Log In
                    </Link>
                </p>
            </div>
        </div>
    );
}