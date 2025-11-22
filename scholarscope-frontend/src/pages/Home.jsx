import React, {useState, useEffect} from 'react'
import ScholarshipCard from '../components/ScholarshipCard'
import Navbar from '../components/Navbar'
import api from '../api'

export default function Home(){
  const  [scholarships, setScholarships] = useState([])
  const fetchScholarships = async (filters={}) => {
    try {
      const res = await api.get('scholarships/', {
         params: {
          q: filters.query || "",
          level: filters.level || "",
          tag: filters.tag || "",
        },
      })
      setScholarships(res.data)
    }
    catch(err) {
       console.error("Error fetching scholarships:", err);
    }
  }
  useEffect(() => {fetchScholarships()}, [])

  const handleFilter = (filters) => {
    fetchScholarships(filters);
  };
  const handleBookmarkToggle = async(id , is_bookmarked) => {
    try {
        const url = is_bookmarked ? `scholarships/${id}/unbookmark/`: `scholarships/${id}/bookmark_scholarship/`;
        await api.post(url);
        setScholarships(scholarships => scholarships.map(s => { s.id === id ? {...s, is_bookmarked:!is_bookmarked} : s}))
    } catch(err) {
        console.log(err)
    }
  }
  return (
    <div className="font-display bg-background-light dark:bg-background-dark min-h-screen">
      <Navbar onFilter={handleFilter} />

      <main className="flex-1">
        <h2 className="text-slate-900 dark:text-slate-50 text-[22px] font-bold leading-tight tracking-[-0.015em] px-4 pb-3 pt-5">
          Scholarships
        </h2>

        <div className="grid grid-cols-1 gap-4 p-4 pt-0 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {scholarships.map((scholarship) => (
            <ScholarshipCard
              key={scholarship.id}
              scholarship={scholarship}
              onToggleBookmark={handleBookmarkToggle}
            />
          ))}
        </div>
      </main>
    </div>
  );
};
