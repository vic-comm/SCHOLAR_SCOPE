// src/components/Navbar.jsx
import React, { useState, useEffect, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";

export default function Navbar({ onFilter }) {
  const navigate = useNavigate();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [level, setLevel]   = useState("");
  const [tag,   setTag]     = useState("");
  const [query, setQuery]   = useState("");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [mobileSearchOpen, setMobileSearchOpen] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    setIsAuthenticated(!!token);
  }, []);

  // Close menu on outside click
  useEffect(() => {
    function handleClickOutside(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setMobileMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function handleSubmit(e) {
    e.preventDefault();
    onFilter({ query, level, tag });
    setMobileSearchOpen(false);
  }

  const handleReset = () => {
    setQuery(""); setLevel(""); setTag("");
    onFilter({});
  };

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    setIsAuthenticated(false);
    setMobileMenuOpen(false);
    navigate("/login");
  };

  return (
    <>
      {/* ── Main navbar ────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-20 w-full border-b border-slate-200/80 bg-background-light/90 backdrop-blur-sm dark:border-slate-800/80 dark:bg-background-dark/90">
        <div className="flex h-14 items-center justify-between px-4 gap-3">

          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 flex-shrink-0">
            <span className="material-symbols-outlined text-2xl text-primary">school</span>
            <span className="font-bold text-slate-900 dark:text-slate-50 text-base">
              ScholarScope
            </span>
          </Link>

          {/* ── Desktop search form (lg+) ─────────────────────────────── */}
          <form
            onSubmit={handleSubmit}
            className="hidden lg:flex flex-1 justify-center items-center gap-2 px-6"
          >
            <div className="relative flex w-full max-w-sm items-center">
              <span className="material-symbols-outlined absolute left-3 text-slate-400 text-[18px]">search</span>
              <input
                type="text"
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="Search scholarships..."
                className="w-full rounded-full border border-slate-300 bg-white py-1.5 pl-9 pr-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/30 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-50 dark:placeholder:text-slate-500"
              />
            </div>
            <select
              value={level}
              onChange={e => setLevel(e.target.value)}
              className="rounded-lg border border-slate-300 bg-white py-1.5 px-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-primary/30 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-50"
            >
              <option value="">All Levels</option>
              <option value="highschool">High School</option>
              <option value="undergraduate">Undergraduate</option>
              <option value="postgraduate">Postgraduate</option>
              <option value="phd">PhD</option>
              <option value="other">Other</option>
            </select>
            <select
              value={tag}
              onChange={e => setTag(e.target.value)}
              className="rounded-lg border border-slate-300 bg-white py-1.5 px-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-primary/30 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-50"
            >
              <option value="">All Tags</option>
              <option value="international">International</option>
              <option value="merit">Merit</option>
              <option value="need">Need</option>
              <option value="general">General</option>
            </select>
            <button type="submit" className="rounded-lg bg-primary px-3 py-1.5 text-sm font-medium text-white hover:bg-primary/90 transition flex-shrink-0">
              Search
            </button>
            <button type="button" onClick={handleReset} className="rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 transition flex-shrink-0" title="Reset filters">
              <span className="material-symbols-outlined text-[18px] leading-none">refresh</span>
            </button>
          </form>

          {/* ── Right side ───────────────────────────────────────────────── */}
          <div className="flex items-center gap-1 flex-shrink-0">

            {/* Mobile: search icon toggle */}
            <button
              className="lg:hidden flex items-center justify-center w-9 h-9 rounded-lg text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800 transition"
              onClick={() => setMobileSearchOpen(v => !v)}
              aria-label="Search"
            >
              <span className="material-symbols-outlined text-[20px]">
                {mobileSearchOpen ? "close" : "search"}
              </span>
            </button>

            {/* Desktop: auth links */}
            {isAuthenticated ? (
              <>
                <Link to="/dashboard" className="hidden sm:block rounded-lg px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800 transition">
                  Dashboard
                </Link>
                <Link to="/profile" className="hidden sm:block rounded-lg px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800 transition">
                  Profile
                </Link>
                <button onClick={handleLogout} className="hidden sm:block rounded-lg bg-red-50 px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-100 dark:bg-red-900/20 dark:text-red-400 dark:hover:bg-red-900/40 transition">
                  Sign Out
                </button>
              </>
            ) : (
              <>
                <Link to="/login" className="hidden sm:block rounded-lg px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800 transition">
                  Sign In
                </Link>
                <Link to="/signup" className="hidden sm:block rounded-lg bg-primary px-3 py-1.5 text-sm font-medium text-white hover:bg-primary/90 shadow-sm transition">
                  Sign Up
                </Link>
              </>
            )}

            {/* Mobile: hamburger */}
            <div className="relative sm:hidden" ref={menuRef}>
              <button
                className="flex items-center justify-center w-9 h-9 rounded-lg text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800 transition"
                onClick={() => setMobileMenuOpen(v => !v)}
                aria-label="Menu"
              >
                <span className="material-symbols-outlined text-[20px]">
                  {mobileMenuOpen ? "close" : "menu"}
                </span>
              </button>

              {/* Dropdown menu */}
              {mobileMenuOpen && (
                <div className="absolute right-0 top-full mt-1 w-44 rounded-xl border border-slate-200 bg-white shadow-lg dark:border-slate-700 dark:bg-slate-900 py-1 z-50">
                  {isAuthenticated ? (
                    <>
                      <Link to="/dashboard" onClick={() => setMobileMenuOpen(false)}
                        className="flex items-center gap-2 px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-800">
                        <span className="material-symbols-outlined text-[16px]">dashboard</span>
                        Dashboard
                      </Link>
                      <Link to="/profile" onClick={() => setMobileMenuOpen(false)}
                        className="flex items-center gap-2 px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-800">
                        <span className="material-symbols-outlined text-[16px]">person</span>
                        Profile
                      </Link>
                      <div className="border-t border-slate-100 dark:border-slate-800 my-1" />
                      <button onClick={handleLogout}
                        className="flex w-full items-center gap-2 px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20">
                        <span className="material-symbols-outlined text-[16px]">logout</span>
                        Sign Out
                      </button>
                    </>
                  ) : (
                    <>
                      <Link to="/login" onClick={() => setMobileMenuOpen(false)}
                        className="flex items-center gap-2 px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-800">
                        <span className="material-symbols-outlined text-[16px]">login</span>
                        Sign In
                      </Link>
                      <Link to="/signup" onClick={() => setMobileMenuOpen(false)}
                        className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-primary hover:bg-primary/5">
                        <span className="material-symbols-outlined text-[16px]">person_add</span>
                        Sign Up
                      </Link>
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ── Mobile search panel (slides in below navbar) ─────────────── */}
        {mobileSearchOpen && (
          <div className="lg:hidden border-t border-slate-200 dark:border-slate-800 bg-background-light dark:bg-background-dark px-4 py-3">
            <form onSubmit={handleSubmit} className="flex flex-col gap-2">
              <div className="relative">
                <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-[18px]">search</span>
                <input
                  type="text"
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  placeholder="Search scholarships..."
                  autoFocus
                  className="w-full rounded-lg border border-slate-300 bg-white py-2 pl-9 pr-4 text-sm text-slate-900 placeholder:text-slate-400 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/30 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-50"
                />
              </div>
              <div className="flex gap-2">
                <select
                  value={level}
                  onChange={e => setLevel(e.target.value)}
                  className="flex-1 rounded-lg border border-slate-300 bg-white py-2 px-2 text-sm text-slate-700 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-50"
                >
                  <option value="">All Levels</option>
                  <option value="highschool">High School</option>
                  <option value="undergraduate">Undergraduate</option>
                  <option value="postgraduate">Postgraduate</option>
                  <option value="phd">PhD</option>
                  <option value="other">Other</option>
                </select>
                <select
                  value={tag}
                  onChange={e => setTag(e.target.value)}
                  className="flex-1 rounded-lg border border-slate-300 bg-white py-2 px-2 text-sm text-slate-700 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-50"
                >
                  <option value="">All Tags</option>
                  <option value="international">International</option>
                  <option value="merit">Merit</option>
                  <option value="need">Need</option>
                  <option value="general">General</option>
                </select>
              </div>
              <div className="flex gap-2">
                <button type="submit" className="flex-1 rounded-lg bg-primary py-2 text-sm font-medium text-white hover:bg-primary/90 transition">
                  Search
                </button>
                <button type="button" onClick={handleReset} className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 transition">
                  <span className="material-symbols-outlined text-[18px] leading-none">refresh</span>
                </button>
              </div>
            </form>
          </div>
        )}
      </header>
    </>
  );
}