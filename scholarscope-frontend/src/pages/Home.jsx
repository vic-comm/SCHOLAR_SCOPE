// src/pages/Home.jsx
import React, { useState, useEffect, useRef, useCallback } from 'react'
import { Link } from 'react-router-dom'
import ScholarshipCard from '../components/ScholarshipCard'
import Navbar from '../components/Navbar'
import api from '../api'

// ── Skeleton card — shown while loading more results ─────────────────────────
function SkeletonCard() {
  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4 animate-pulse">
      <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-3/4 mb-3" />
      <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded w-full mb-2" />
      <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded w-5/6 mb-4" />
      <div className="flex gap-2">
        <div className="h-5 bg-slate-200 dark:bg-slate-700 rounded-full w-16" />
        <div className="h-5 bg-slate-200 dark:bg-slate-700 rounded-full w-20" />
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────
export default function Home() {
  const [scholarships, setScholarships] = useState([])
  const [nextCursor,   setNextCursor]   = useState(null)   // URL from `next` field
  const [loading,      setLoading]      = useState(true)   // initial page load
  const [loadingMore,  setLoadingMore]  = useState(false)  // subsequent scroll loads
  const [hasMore,      setHasMore]      = useState(true)
  const [filters,      setFilters]      = useState({ query: '', level: '', tag: '' })

  // Sentinel div at the bottom of the list — IntersectionObserver watches this
  const sentinelRef = useRef(null)
  // Keep a stable reference to the active filters for use inside the observer
  const filtersRef  = useRef(filters)
  filtersRef.current = filters

  // ── Fetch a page of scholarships ────────────────────────────────────────────
  // cursorUrl: full URL from `next` field (null for first page)
  // reset: true when filters change (replace list), false when scrolling (append)
  const fetchPage = useCallback(async (cursorUrl = null, reset = false) => {
    if (reset) {
      setLoading(true)
    } else {
      setLoadingMore(true)
    }

    try {
      let res

      if (cursorUrl) {
        // DRF returns absolute cursor URLs like:
        //   http://localhost:8000/api/scholarships/?cursor=xxx
        // axios baseURL is already http://localhost:8000/api/
        // Strip BOTH origin AND the /api/ prefix, leaving just:
        //   scholarships/?cursor=xxx
        const url      = new URL(cursorUrl)
        const basePath = new URL(api.defaults.baseURL).pathname  // e.g. "/api/"
        let   relative = url.pathname + url.search               // e.g. "/api/scholarships/?cursor=..."
        if (relative.startsWith(basePath)) {
          relative = relative.slice(basePath.length)             // -> "scholarships/?cursor=..."
        }
        res = await api.get(relative)
      } else {
        const { query, level, tag } = filtersRef.current
        res = await api.get('scholarships/', {
          params: {
            q:     query || undefined,
            level: level || undefined,
            tag:   tag   || undefined,
          },
        })
      }

      const { results, next } = res.data

      setScholarships(prev => reset ? results : [...prev, ...results])
      setNextCursor(next)
      setHasMore(!!next)

    } catch (err) {
      console.error('Error fetching scholarships:', err)
      // Stop the observer retrying forever after a failed request
      setHasMore(false)
    } finally {
      setLoading(false)
      setLoadingMore(false)
    }
  }, [])

  // ── Initial load + filter changes ──────────────────────────────────────────
  useEffect(() => {
    setScholarships([])
    setNextCursor(null)
    setHasMore(true)
    fetchPage(null, true)
  }, [filters, fetchPage])

  // ── IntersectionObserver — fires when sentinel enters the viewport ──────────
  useEffect(() => {
    if (!sentinelRef.current) return

    const observer = new IntersectionObserver(
      (entries) => {
        const [entry] = entries
        // Only fire if: sentinel is visible, we have more pages, not already loading
        if (entry.isIntersecting && hasMore && !loadingMore && !loading) {
          fetchPage(nextCursor, false)
        }
      },
      {
        // rootMargin: start fetching 200px before the sentinel becomes visible
        // so cards are already loading before the user hits the bottom.
        rootMargin: '0px 0px 200px 0px',
        threshold: 0,
      }
    )

    observer.observe(sentinelRef.current)
    return () => observer.disconnect()

  }, [hasMore, loadingMore, loading, nextCursor, fetchPage])

  // ── Bookmark / watch handlers (unchanged logic) ────────────────────────────
  const handleBookmarkToggle = useCallback(async (id, is_bookmarked) => {
    setScholarships(prev =>
      prev.map(s => s.id === id ? { ...s, is_bookmarked: !is_bookmarked } : s)
    )
    try {
      const url = is_bookmarked
        ? `scholarships/${id}/unbookmark/`
        : `scholarships/${id}/bookmark_scholarship/`
      await api.post(url)
    } catch (err) {
      console.error('Bookmark toggle failed:', err)
      setScholarships(prev =>
        prev.map(s => s.id === id ? { ...s, is_bookmarked } : s)
      )
    }
  }, [])

  const handleToggleWatch = useCallback(async (id) => {
    const target = scholarships.find(s => s.id === id)
    if (!target) return
    const wasWatched = target.is_watched

    setScholarships(prev =>
      prev.map(s => s.id === id ? { ...s, is_watched: !wasWatched } : s)
    )
    try {
      await api.post(`scholarships/${id}/toggle_watch_scholarship/`)
    } catch (err) {
      console.error('Watch toggle failed:', err)
      setScholarships(prev =>
        prev.map(s => s.id === id ? { ...s, is_watched: wasWatched } : s)
      )
    }
  }, [scholarships])

  const handleFilter = useCallback((incoming) => {
    setFilters({
      query: incoming.query || '',
      level: incoming.level || '',
      tag:   incoming.tag   || '',
    })
  }, [])

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <div className="font-display bg-background-light dark:bg-background-dark min-h-screen">
      <Navbar onFilter={handleFilter} />

      <main className="flex-1">
        <h2 className="text-slate-900 dark:text-slate-50 text-[22px] font-bold leading-tight tracking-[-0.015em] px-4 pb-3 pt-5">
          Scholarships
        </h2>

        {/* ── Initial loading state ── */}
        {loading && (
          <div className="grid grid-cols-1 gap-4 p-4 pt-0 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {Array.from({ length: 12 }).map((_, i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        )}

        {/* ── Scholarship grid ── */}
        {!loading && scholarships.length > 0 && (
          <div className="grid grid-cols-1 gap-4 p-4 pt-0 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {scholarships.map(scholarship => (
              <Link
                key={scholarship.id}
                to={`/scholarships/${scholarship.id}`}
                className="block h-full"
              >
                <ScholarshipCard
                  scholarship={scholarship}
                  onToggleBookmark={handleBookmarkToggle}
                  onToggleWatch={handleToggleWatch}
                />
              </Link>
            ))}
          </div>
        )}

        {/* ── Empty state ── */}
        {!loading && scholarships.length === 0 && (
          <div className="flex flex-col items-center justify-center p-16 gap-3">
            <p className="text-slate-500 dark:text-slate-400 text-base">
              No scholarships found.
            </p>
            <p className="text-slate-400 dark:text-slate-500 text-sm">
              Try adjusting your filters or search query.
            </p>
          </div>
        )}

        {/* ── "Load more" skeleton — shown at the bottom while fetching next page ── */}
        {loadingMore && (
          <div className="grid grid-cols-1 gap-4 px-4 pb-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <SkeletonCard key={`more-${i}`} />
            ))}
          </div>
        )}

        {/* ── End-of-list message ── */}
        {!loading && !hasMore && scholarships.length > 0 && (
          <p className="text-center text-slate-400 dark:text-slate-500 text-sm py-8">
            You've seen all {scholarships.length} scholarships
          </p>
        )}

        {/*
          ── Sentinel div ──
          This invisible div sits at the bottom of the page.
          The IntersectionObserver watches it. When it scrolls into view
          (or within 200px of the viewport), the next page is fetched.
          Must be rendered even when loadingMore=true so the observer
          stays active — we just won't fire again because of the loadingMore guard.
        */}
        <div ref={sentinelRef} style={{ height: 1 }} aria-hidden="true" />
      </main>
    </div>
  )
}