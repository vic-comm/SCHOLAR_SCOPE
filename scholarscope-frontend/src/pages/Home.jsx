// src/pages/Home.jsx
import React, { useState, useEffect, useRef, useCallback } from 'react'
import { Link } from 'react-router-dom'
import ScholarshipCard from '../components/ScholarshipCard'
import Navbar from '../components/Navbar'
import api from '../api'

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

export default function Home() {
  const [scholarships, setScholarships] = useState([])
  const [nextCursor,   setNextCursor]   = useState(null)
  const [loading,      setLoading]      = useState(true)
  const [loadingMore,  setLoadingMore]  = useState(false)
  const [hasMore,      setHasMore]      = useState(true)
  const [filters,      setFilters]      = useState({ query: '', level: '', tag: '' })

  const sentinelRef  = useRef(null)
  const filtersRef   = useRef(filters)
  filtersRef.current = filters

  // ── Guard: prevent concurrent fetches firing duplicate appends ─────────────
  // Without this, the IntersectionObserver can fire multiple times before
  // loadingMore state has propagated, causing the same page to be fetched twice
  // and appended twice → duplicate keys → React drops items → missing cards.
  const fetchingRef = useRef(false)

  const fetchPage = useCallback(async (cursorUrl = null, reset = false) => {
    // Prevent concurrent fetches
    if (fetchingRef.current) return
    fetchingRef.current = true

    reset ? setLoading(true) : setLoadingMore(true)

    try {
      let res

      if (cursorUrl) {
        const url      = new URL(cursorUrl)
        const basePath = new URL(api.defaults.baseURL).pathname
        let   relative = url.pathname + url.search
        if (relative.startsWith(basePath)) {
          relative = relative.slice(basePath.length)
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

      if (reset) {
        // On reset just replace — no dedup needed
        setScholarships(results)
      } else {
        // Deduplicate by ID before appending — guards against double-fire
        setScholarships(prev => {
          const existingIds = new Set(prev.map(s => s.id))
          const fresh = results.filter(s => !existingIds.has(s.id))
          return [...prev, ...fresh]
        })
      }

      setNextCursor(next)
      setHasMore(!!next)

    } catch (err) {
      console.error('Error fetching scholarships:', err)
      setHasMore(false)
    } finally {
      setLoading(false)
      setLoadingMore(false)
      fetchingRef.current = false
    }
  }, [])

  useEffect(() => {
    setScholarships([])
    setNextCursor(null)
    setHasMore(true)
    fetchingRef.current = false
    fetchPage(null, true)
  }, [filters, fetchPage])

  useEffect(() => {
    if (!sentinelRef.current) return

    const observer = new IntersectionObserver(
      (entries) => {
        const [entry] = entries
        if (entry.isIntersecting && hasMore && !loadingMore && !loading && !fetchingRef.current) {
          fetchPage(nextCursor, false)
        }
      },
      { rootMargin: '0px 0px 200px 0px', threshold: 0 }
    )

    observer.observe(sentinelRef.current)
    return () => observer.disconnect()
  }, [hasMore, loadingMore, loading, nextCursor, fetchPage])

  const handleBookmarkToggle = useCallback(async (id, is_bookmarked) => {
    setScholarships(prev =>
      prev.map(s => s.id === id ? { ...s, is_bookmarked: !is_bookmarked } : s)
    )
    try {
      await api.post(is_bookmarked
        ? `scholarships/${id}/unbookmark/`
        : `scholarships/${id}/bookmark_scholarship/`
      )
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

  return (
    <div className="font-display bg-background-light dark:bg-background-dark min-h-screen">
      <Navbar onFilter={handleFilter} />

      <main className="flex-1">
        <h2 className="text-slate-900 dark:text-slate-50 text-[22px] font-bold leading-tight tracking-[-0.015em] px-4 pb-3 pt-5">
          Scholarships
        </h2>

        {loading && (
          <div className="grid grid-cols-1 gap-4 p-4 pt-0 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {Array.from({ length: 12 }).map((_, i) => <SkeletonCard key={i} />)}
          </div>
        )}

        {!loading && scholarships.length > 0 && (
          <div className="grid grid-cols-1 gap-4 p-4 pt-0 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {scholarships.map(scholarship => (
              <Link key={scholarship.id} to={`/scholarships/${scholarship.id}`} className="block h-full">
                <ScholarshipCard
                  scholarship={scholarship}
                  onToggleBookmark={handleBookmarkToggle}
                  onToggleWatch={handleToggleWatch}
                />
              </Link>
            ))}
          </div>
        )}

        {!loading && scholarships.length === 0 && (
          <div className="flex flex-col items-center justify-center p-16 gap-3">
            <p className="text-slate-500 dark:text-slate-400 text-base">No scholarships found.</p>
            <p className="text-slate-400 dark:text-slate-500 text-sm">Try adjusting your filters or search query.</p>
          </div>
        )}

        {loadingMore && (
          <div className="grid grid-cols-1 gap-4 px-4 pb-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={`more-${i}`} />)}
          </div>
        )}

        {!loading && !hasMore && scholarships.length > 0 && (
          <p className="text-center text-slate-400 dark:text-slate-500 text-sm py-8">
            You've seen all {scholarships.length} scholarships
          </p>
        )}

        <div ref={sentinelRef} style={{ height: 1 }} aria-hidden="true" />
      </main>
    </div>
  )
}