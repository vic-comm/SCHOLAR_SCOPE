import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";

export default function Navbar({ onFilter }) {
  // 1. Initialize Hooks INSIDE the component
  const navigate = useNavigate(); // Required for redirecting after logout
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [level, setLevel] = useState("");
  const [tag, setTag] = useState("");
  const [query, setQuery] = useState("");

  // 2. Check authentication status on mount
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    setIsAuthenticated(!!token);
  }, []);

  function handleSubmit(event) {
    event.preventDefault();
    onFilter({ query, level, tag });
  }

  const handleReset = () => {
    setQuery("");
    setLevel("");
    setTag("");
    onFilter({});
  };

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    setIsAuthenticated(false);
    navigate("/login");
  };

  return (
    <header className="sticky top-0 z-10 flex h-16 w-full items-center justify-between border-b border-slate-200/80 bg-background-light/80 px-4 backdrop-blur-sm dark:border-slate-800/80 dark:bg-background-dark/80 lg:gap-8">
      <div className="flex items-center gap-3">
        <Link to="/" className="flex items-center gap-2">
          <span className="material-symbols-outlined text-3xl text-primary">
            school
          </span>
          <h1 className="hidden text-xl font-bold text-slate-900 dark:text-slate-50 md:block">
            ScholarScope
          </h1>
        </Link>
      </div>

      <form
        onSubmit={handleSubmit}
        className="hidden flex-1 lg:flex lg:justify-center lg:px-8 items-center gap-3"
      >
        {/* Search Input */}
        <div className="relative flex w-full max-w-sm items-center">
          <span className="material-symbols-outlined absolute left-3 text-slate-500 dark:text-slate-400">
            search
          </span>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search scholarships..."
            className="form-input w-full rounded-full border-slate-300 bg-white py-2 pl-10 pr-4 text-slate-900 placeholder:text-slate-500 focus:border-primary focus:ring-primary/50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-50 dark:placeholder:text-slate-400"
          />
        </div>

        {/* Level Dropdown */}
        <select
          value={level}
          onChange={(e) => setLevel(e.target.value)}
          className="rounded-lg border border-slate-300 bg-white py-2 px-3 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-primary/50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-50"
        >
          <option value="">All Levels</option>
          <option value="highschool">High School</option>
          <option value="undergraduate">Undergraduate</option>
          <option value="postgraduate">Postgraduate</option>
          <option value="phd">PhD</option>
          <option value="other">Other</option>
        </select>

        {/* Tag Dropdown */}
        <select
          value={tag}
          onChange={(e) => setTag(e.target.value)}
          className="rounded-lg border border-slate-300 bg-white py-2 px-3 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-primary/50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-50"
        >
          <option value="">All Tags</option>
          <option value="international">International</option>
          <option value="merit">Merit</option>
          <option value="need">Need</option>
          <option value="general">General</option>
        </select>

        <button
          type="submit"
          className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/90"
        >
          Search
        </button>
        <button
          type="button"
          onClick={handleReset}
          className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700 transition flex items-center"
        >
          <span className="material-symbols-outlined text-lg">refresh</span>
        </button>
      </form>

      {/* Right Side - Conditional Rendering */}
      <div className="flex items-center gap-2">
        {isAuthenticated ? (
          <>
            <Link
              to="/dashboard"
              className="hidden rounded-lg px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800 sm:block"
            >
              Dashboard
            </Link>
            <Link
              to="/profile"
              className="hidden rounded-lg px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800 sm:block"
            >
              Update Profile
            </Link>
            <button
              onClick={handleLogout}
              className="hidden rounded-lg bg-red-50 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-100 dark:bg-red-900/20 dark:text-red-400 dark:hover:bg-red-900/40 sm:block transition"
            >
              Sign Out
            </button>
          </>
        ) : (
          <>
            <Link
              to="/login"
              className="rounded-lg px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              Sign In
            </Link>
            <Link
              to="/signup"
              className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/90 shadow-sm"
            >
              Sign Up
            </Link>
          </>
        )}
      </div>
    </header>
  );
}