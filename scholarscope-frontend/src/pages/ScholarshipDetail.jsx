import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from '../api'
import { Bookmark, Heart, Share2, ArrowLeft, ChevronDown, ExternalLink } from "lucide-react";

export default function ScholarshipDetail() {
    const {id} = useParams()
    const navigate = useNavigate()
    const [scholarship, setScholarship] = useState(null);
    const [similar, setSimilar] = useState([]);
    const [isBookmarked, setIsBookmarked] = useState(false);

    useEffect(() => {
        async function fetchScholarship() {
            try {
                const res = await api.get(`scholarships/${id}/details`)
                setScholarship(res.data.data)
                setSimilar(res.data.similar_scholarships)
                setIsBookmarked(res.data.is_bookmarked)
            } catch (err) {
                console.error("Error loading scholarship details:", err);
            }
        };
        fetchScholarship();
    }, [id])

    async function handleBookmark() {
        try {
            if (scholarship.is_bookmarked) {
                await api.post(`/scholarships/${id}/unbookmark/`)
                setScholarship({ ...scholarship, is_bookmarked: false });
            } else {
                await api.post(`/scholarships/${id}/bookmark_scholarship/`)
                setScholarship({ ...scholarship, is_bookmarked: true });
            }
        } catch (err) {
            console.error("Bookmark error:", err);
        }
    }

    async function handleSave() {
        try {
            if (scholarship.is_saved) {
                await api.post(`/scholarships/${id}/unbookmark/`)
                setScholarship({ ...scholarship, is_saved: false });
            } else {
                await api.post(`/scholarships/${id}/bookmark_scholarship/`)
                setScholarship({ ...scholarship, is_saved: true });
            }
        } catch (err) {
            console.error("Save error:", err);
        }
    }


    if (!scholarship) {
    return (
      <div className="flex items-center justify-center min-h-screen text-lg text-slate-500">
        Loading scholarship details...
      </div>
    );
  }

  return (
    <div className="bg-background-light dark:bg-background-dark font-display text-slate-800 dark:text-slate-200 min-h-screen">
      {/* Header */}
      <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm px-6">
        <button onClick={() => navigate(-1)} className="flex items-center gap-1 hover:text-primary transition">
          <ArrowLeft className="w-5 h-5" />
          <span className="font-medium hidden sm:inline">Back</span>
        </button>
        <h1 className="text-lg sm:text-xl font-bold">Scholarship Details</h1>
        <div className="w-8" />
      </header>

      {/* Main Content */}
      <main className="max-w-5xl mx-auto px-6 py-10">
        {/* Title */}
        <div className="mb-8">
          <h1 className="text-3xl md:text-4xl font-bold leading-tight">{scholarship.title}</h1>
          <h2 className="text-primary text-2xl font-bold mt-2 mb-4">{scholarship.reward || "$— Award"}</h2>

          {/* Tags */}
          <div className="flex flex-wrap gap-2">
            {scholarship.tags?.map((tag, i) => (
              <div
                key={i}
                className="px-3 py-1 rounded-lg bg-primary/15 text-primary text-sm font-medium"
              >
                {tag.name}
              </div>
            ))}
          </div>
        </div>

        {/* Dates */}
        <div className="grid sm:grid-cols-2 gap-6 mb-10">
          <div className="p-4 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/50">
            <p className="text-sm text-slate-500">Start Date</p>
            <p className="text-base font-medium">{scholarship.start_date || "N/A"}</p>
          </div>
          <div className="p-4 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/50">
            <p className="text-sm text-slate-500">End Date</p>
            <p className="text-base font-medium">{scholarship.end_date || "N/A"}</p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex flex-wrap items-center gap-3 mb-10">
          <a
            href={scholarship.link}
            target="_blank"
            rel="noreferrer"
            className="flex h-12 flex-1 items-center justify-center rounded-lg bg-primary text-white font-semibold shadow-sm hover:bg-primary/90 transition"
          >
            Apply Now
          </a>

          <button
            onClick={handleBookmark}
            className={`flex h-12 w-12 items-center justify-center rounded-lg border transition ${
              isBookmarked
                ? "bg-primary/10 border-primary text-primary"
                : "bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800"
            }`}
          >
            <Bookmark className={isBookmarked ? "fill-primary" : ""} />
          </button>
          <button onClick={handleSave} className="h-12 w-12 flex items-center justify-center rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:bg-slate-100 dark:hover:bg-slate-800 transition">
            <span className="material-symbols-outlined filled text-primary">{scholarship.is_saved ? Unsave : Save}</span>
          </button>
          <button className="flex h-12 w-12 items-center justify-center rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 hover:bg-slate-100 dark:hover:bg-slate-800 transition">
            <Share2 className="w-5 h-5" />
          </button>
        </div>

        {/* Accordion Sections */}
        <div className="space-y-4">
          <Accordion title="Description">
            <p className="leading-relaxed text-slate-700 dark:text-slate-300">
              {scholarship.description}
            </p>
          </Accordion>

          <Accordion title="Eligibility & Requirements">
            <p className="leading-relaxed text-slate-700 dark:text-slate-300 whitespace-pre-line">
              {scholarship.eligibility || "Eligibility information not available."}
            </p>
            <a
              href={scholarship.link}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 mt-4 px-4 py-2 rounded-lg bg-primary/15 text-primary font-semibold hover:bg-primary/25 transition"
            >
              <ExternalLink className="w-4 h-4" />
              Visit Official Page
            </a>
          </Accordion>
        </div>

        {/* Similar Scholarships */}
        <div className="mt-16">
          <h3 className="text-xl font-bold mb-4">Similar Scholarships</h3>
          <div className="flex gap-5 overflow-x-auto pb-4 scrollbar-hide">
            {similar.map((item) => (
              <div
                key={item.id}
                className="flex-none w-80 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/50 p-5 hover:shadow-md transition"
              >
                <h4 className="font-semibold truncate text-lg mb-1">{item.title}</h4>
                <p className="text-primary font-semibold mb-1">{item.reward || "$—"}</p>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  Closes {item.end_date || "soon"}
                </p>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}

function Accordion({ title, children }) {
  const [open, setOpen] = useState(true);
  return (
    <div className="rounded-xl bg-white dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex justify-between items-center p-4 text-left"
      >
        <h3 className="text-lg font-semibold">{title}</h3>
        <ChevronDown
          className={`w-5 h-5 transition-transform duration-300 ${open ? "rotate-180" : ""}`}
        />
      </button>
      {open && <div className="px-4 pb-4">{children}</div>}
    </div>
  );
}