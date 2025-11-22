import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { GoogleLogin } from "@react-oauth/google";
import api from "../api";

export default function SignUp() {
    const navigate = useNavigate()
    const [formData, setFormData] = useState({
    full_name: "",
    email: "",
    password1: "",
    password2: "",
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const handleChange = (event) => {
        setFormData({...formData, [event.target.name]:event.target.value})
    }

    const handleSubmit = async (event) => {
        event.preventDefault()
        setLoading(true)
        setError('')

        try {
            await api.post('register/', formData)
            navigate('login/')
        } catch (err) {
      setError(err.response?.data?.detail || "Signup failed");
    } finally {
      setLoading(false);
    }
    }

    const handleGoogleSuccess = async (credentialResponse) => {
        try {
        const { credential } = credentialResponse;
        await api.post("google/login/", { access_token: credential });
        navigate("/");
        } catch (err) {
        setError("Google login failed. Try again.");
        }
    };
    return (
    <div className="flex min-h-screen items-center justify-center bg-background-light dark:bg-background-dark p-4">
      <div className="w-full max-w-md flex flex-col items-center">
        <div className="flex size-12 items-center justify-center text-primary mb-4">
          <span className="material-symbols-outlined !text-5xl">school</span>
        </div>

        <h1 className="text-3xl font-bold text-center text-slate-900 dark:text-slate-50">
          Create Your Account
        </h1>
        <p className="mt-2 text-center text-base text-slate-600 dark:text-slate-400">
          Find scholarships tailored for you.
        </p>

        <form onSubmit={handleSubmit} className="mt-8 w-full space-y-4">
          <label className="flex flex-col">
            <p className="text-sm font-medium pb-2 text-slate-800 dark:text-slate-300">Full Name</p>
            <input
              name="full_name"
              value={formData.full_name}
              onChange={handleChange}
              placeholder="Enter your full name"
              className="form-input rounded-lg border border-slate-300 bg-background-light dark:bg-background-dark h-12 p-3"
              required
            />
          </label>

          <label className="flex flex-col">
            <p className="text-sm font-medium pb-2 text-slate-800 dark:text-slate-300">Email</p>
            <input
              name="email"
              type="email"
              value={formData.email}
              onChange={handleChange}
              placeholder="Enter your email address"
              className="form-input rounded-lg border border-slate-300 bg-background-light dark:bg-background-dark h-12 p-3"
              required
            />
          </label>

          <label className="flex flex-col">
            <p className="text-sm font-medium pb-2 text-slate-800 dark:text-slate-300">Password</p>
            <input
              name="password1"
              type="password"
              value={formData.password1}
              onChange={handleChange}
              placeholder="Enter your password"
              className="form-input rounded-lg border border-slate-300 bg-background-light dark:bg-background-dark h-12 p-3"
              required
            />
          </label>

          <label className="flex flex-col">
            <p className="text-sm font-medium pb-2 text-slate-800 dark:text-slate-300">Confirm Password</p>
            <input
              name="password2"
              type="password"
              value={formData.password2}
              onChange={handleChange}
              placeholder="Confirm your password"
              className="form-input rounded-lg border border-slate-300 bg-background-light dark:bg-background-dark h-12 p-3"
              required
            />
          </label>

          {error && <p className="text-red-500 text-sm">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full h-12 bg-primary text-white font-bold rounded-lg hover:opacity-90 active:scale-95 transition"
          >
            {loading ? "Creating..." : "Create Account"}
          </button>
        </form>

        <div className="relative my-8 w-full flex items-center justify-center">
          <div className="absolute w-full border-t border-slate-300"></div>
          <span className="relative z-10 bg-background-light dark:bg-background-dark px-4 text-sm text-slate-600">
            Or continue with
          </span>
        </div>

        <div className="flex justify-center">
          <GoogleLogin onSuccess={handleGoogleSuccess} onError={() => setError("Google Login Failed")} />
        </div>

        <p className="mt-8 text-center text-sm text-slate-600 dark:text-slate-400">
          Already have an account?{" "}
          <a className="font-bold text-primary hover:underline" href="/login">
            Log In
          </a>
        </p>
      </div>
    </div>
  );
}
