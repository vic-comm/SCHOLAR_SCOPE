import React, {useState, useEffect} from 'react'
import ScholarshipCard from '../components/ScholarshipCard'
import Navbar from '../components/Navbar'
import { Link } from 'react-router-dom';
import api from '../api'

export default function Home(){
  const [scholarships, setScholarships] = useState([])
  const [loading, setLoading] = useState(true)

  const fetchScholarships = async (filters={}) => {
    setLoading(true)
    try {
      const res = await api.get('scholarships/', {
        params: {
          q: filters.query || "",
          level: filters.level || "",
          tag: filters.tag || "",
        },
      })
      const data = res.data.results ? res.data.results : res.data;
      setScholarships(data);
    }
    catch(err) {
      console.error("Error fetching scholarships:", err);
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchScholarships()
  }, [])

  const handleFilter = (filters) => {
    fetchScholarships(filters);
  };

  const handleBookmarkToggle = async(id, is_bookmarked) => {

    e.preventDefault();
    e.stopPropagation();
    // Optimistically update UI
    setScholarships(scholarships => 
      scholarships.map(s => 
        s.id === id ? {...s, is_bookmarked: !is_bookmarked} : s
      )
    )

    try {
      const url = is_bookmarked 
        ? `scholarships/${id}/unbookmark/` 
        : `scholarships/${id}/bookmark_scholarship/`;
      await api.post(url);
    } catch(err) {
      console.error("Bookmark toggle failed:", err)
      // Revert on error
      setScholarships(scholarships => 
        scholarships.map(s => 
          s.id === id ? {...s, is_bookmarked: is_bookmarked} : s
        )
      )
    }
  }

  const handleToggleWatch = async (id) => {
  // 1. Find the current scholarship to know its state
  const targetScholarship = scholarships.find((s) => s.id === id);
  if (!targetScholarship) return;

  const wasWatched = targetScholarship.is_watched;

  // 2. Optimistic UI Update: Instantly toggle it in the local state
  setScholarships((prevScholarships) =>
    prevScholarships.map((s) =>
      s.id === id ? { ...s, is_watched: !wasWatched } : s
    )
  );

  // 3. Make the API call
  try {
    await api.post(`scholarships/${id}/toggle_watch_scholarship/`);
    // Optional: show a small toast notification here
  } catch (err) {
    console.error("Watch toggle failed:", err);
    // 4. Revert the UI if the API call fails
    setScholarships((prevScholarships) =>
      prevScholarships.map((s) =>
        s.id === id ? { ...s, is_watched: wasWatched } : s
      )
    );
  }
};

  return (
    <div className="font-display bg-background-light dark:bg-background-dark min-h-screen">
      <Navbar onFilter={handleFilter} />

      <main className="flex-1">
        <h2 className="text-slate-900 dark:text-slate-50 text-[22px] font-bold leading-tight tracking-[-0.015em] px-4 pb-3 pt-5">
          Scholarships
        </h2>

        {loading ? (
          <div className="flex items-center justify-center p-10">
            <p className="text-slate-500 dark:text-slate-400">Loading scholarships...</p>
          </div>
        ) : scholarships.length > 0 ? (
          <div className="grid grid-cols-1 gap-4 p-4 pt-0 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {scholarships.map((scholarship) => (
              <Link 
                key={scholarship.id} 
                to={`/scholarships/${scholarship.id}`}
                className="block h-full" // block ensures it wraps correctly, h-full keeps height uniform
              >
                <ScholarshipCard
                  scholarship={scholarship}
                  onToggleBookmark={handleBookmarkToggle}
                  onToggleWatch={handleToggleWatch}
                />
              </Link>
            ))}
          </div>
        ) : (
          <div className="flex items-center justify-center p-10">
            <p className="text-slate-500 dark:text-slate-400">No scholarships found. Try adjusting your filters.</p>
          </div>
        )}
      </main>
    </div>
  );
}
