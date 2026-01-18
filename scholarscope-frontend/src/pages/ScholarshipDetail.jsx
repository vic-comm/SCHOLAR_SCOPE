import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from '../api' // Ensure this axios instance has your interceptors/base URL
import { Bookmark, Heart, Share2, ArrowLeft, ChevronDown, ExternalLink } from "lucide-react";

export default function ScholarshipDetail() {
    const { id } = useParams()
    const navigate = useNavigate()
    const [scholarship, setScholarship] = useState(null);
    const [similar, setSimilar] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function fetchScholarship() {
            setLoading(true);
            try {
                const res = await api.get(`scholarships/${id}/details/`)
                setScholarship(res.data.data)
                setSimilar(res.data.similar_scholarships || [])
            } catch (err) {
                console.error("Error loading scholarship details:", err);
            } finally {
                setLoading(false);
            }
        };
        window.scrollTo(0, 0);
        fetchScholarship();
    }, [id])

    // Helper to handle 401 (Unauthorized) if user tries action while logged out
    const handleAuthError = (err) => {
        if (err.response && err.response.status === 401) {
            navigate('/login', { state: { from: location.pathname } });
        } else {
            console.error("Action failed:", err);
        }
    };

    async function handleBookmark() {
        if (!scholarship) return;
        const previousState = scholarship.is_bookmarked;
        
        // Optimistically update UI
        setScholarship(prev => ({ ...prev, is_bookmarked: !previousState }));

        try {
            if (previousState) {
                // Matches: @action(detail=True, methods=['post']) def unbookmark(...)
                await api.post(`scholarships/${id}/unbookmark/`)
            } else {
                // Matches: @action(detail=True, methods=['post']) def bookmark_scholarship(...)
                await api.post(`scholarships/${id}/bookmark_scholarship/`)
            }
        } catch (err) {
            // Revert on error
            setScholarship(prev => ({ ...prev, is_bookmarked: previousState }));
            handleAuthError(err);
        }
    }

    async function handleSave() {
        if (!scholarship) return;
        const previousState = scholarship.is_saved;
        
        // Optimistically update UI
        setScholarship(prev => ({ ...prev, is_saved: !previousState }));

        try {
            if (previousState) {
                // Matches: @action(detail=True, methods=['post']) def unsave_scholarship(...)
                await api.post(`scholarships/${id}/unsave_scholarship/`)
            } else {
                // Matches: @action(detail=True, methods=['post']) def save(...)
                await api.post(`scholarships/${id}/save/`)
            }
        } catch (err) {
            // Revert on error
            setScholarship(prev => ({ ...prev, is_saved: previousState }));
            handleAuthError(err);
        }
    }

    async function handleApply() {
        // We use the specific 'apply' endpoint which returns the link and tracks application
        try {
            // Matches: @action(detail=True, methods=['post']) def apply(...)
            const res = await api.post(`scholarships/${id}/apply/`);
            
            // The backend returns { message, scholarship_link, already_applied }
            const linkToOpen = res.data.scholarship_link || scholarship.link;

            if (linkToOpen) {
                window.open(linkToOpen, '_blank');
            }
            
            // Since your backend 'apply' creates an Application object (same as save),
            // we update is_saved to true to reflect that the user has interacted/saved it.
            setScholarship(prev => ({ ...prev, is_saved: true }));

        } catch (err) {
            console.error("Failed to apply:", err);
            handleAuthError(err);
            
            // Fallback: If API fails (e.g., network), still try to open the link if we have it
            if (scholarship.link) {
                window.open(scholarship.link, '_blank');
            }
        }
    }

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen bg-background-light dark:bg-background-dark">
                <p className="text-slate-500 dark:text-slate-400">Loading details...</p>
            </div>
        );
    }

    if (!scholarship) {
        return (
            <div className="flex flex-col items-center justify-center min-h-screen bg-background-light dark:bg-background-dark gap-4">
                <p className="text-slate-500 dark:text-slate-400">Scholarship not found.</p>
                <button onClick={() => navigate('/')} className="text-primary hover:underline">
                    Go Home
                </button>
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
                <h1 className="text-lg sm:text-xl font-bold truncate max-w-[200px] sm:max-w-md">
                    Scholarship Details
                </h1>
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
                                {tag.name || tag}
                            </div>
                        ))}
                    </div>
                </div>

                {/* Dates */}
                <div className="grid sm:grid-cols-2 gap-6 mb-10">
                    <div className="p-4 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/50">
                        <p className="text-sm text-slate-500 dark:text-slate-400">Start Date</p>
                        <p className="text-base font-medium">{scholarship.start_date || "Open"}</p>
                    </div>
                    <div className="p-4 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/50">
                        <p className="text-sm text-slate-500 dark:text-slate-400">Deadline</p>
                        <p className="text-base font-medium">{scholarship.end_date || "Ongoing"}</p>
                    </div>
                </div>

                {/* Actions */}
                <div className="flex flex-wrap items-center gap-3 mb-10">
                    <button
                        onClick={handleApply}
                        className="flex h-12 flex-1 items-center justify-center rounded-lg bg-primary text-white font-semibold shadow-sm hover:bg-primary/90 transition"
                    >
                        Apply Now
                    </button>

                    <button
                        onClick={handleBookmark}
                        className={`flex h-12 w-12 items-center justify-center rounded-lg border transition ${
                            scholarship.is_bookmarked
                                ? "bg-primary/10 border-primary text-primary"
                                : "bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800"
                        }`}
                        title={scholarship.is_bookmarked ? "Remove bookmark" : "Bookmark scholarship"}
                    >
                        <Bookmark className={`w-5 h-5 ${scholarship.is_bookmarked ? "fill-current" : ""}`} />
                    </button>

                    <button 
                        onClick={handleSave} 
                        className={`h-12 w-12 flex items-center justify-center rounded-lg border transition ${
                            scholarship.is_saved
                                ? "bg-primary/10 border-primary text-primary"
                                : "bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 hover:bg-slate-100 dark:hover:bg-slate-800"
                        }`}
                        title={scholarship.is_saved ? "Unsave scholarship" : "Save for later"}
                    >
                        <Heart className={`w-5 h-5 ${scholarship.is_saved ? "fill-current" : ""}`} />
                    </button>

                    <button 
                        onClick={() => {
                            if (navigator.share) {
                                navigator.share({
                                    title: scholarship.title,
                                    url: window.location.href
                                }).catch(console.error);
                            } else {
                                navigator.clipboard.writeText(window.location.href);
                                alert("Link copied to clipboard!");
                            }
                        }}
                        className="flex h-12 w-12 items-center justify-center rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                        title="Share"
                    >
                        <Share2 className="w-5 h-5" />
                    </button>
                </div>

                {/* Accordion Sections */}
                <div className="space-y-4">
                    <Accordion title="Description">
                        <div className="leading-relaxed text-slate-700 dark:text-slate-300 whitespace-pre-line">
                            {scholarship.description}
                        </div>
                    </Accordion>

                    <Accordion title="Eligibility & Requirements">
                        <div className="leading-relaxed text-slate-700 dark:text-slate-300 whitespace-pre-line">
                            {scholarship.eligibility || "See official website for detailed requirements."}
                        </div>
                        {scholarship.link && (
                            <a
                                href={scholarship.link}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-2 mt-4 px-4 py-2 rounded-lg bg-primary/10 text-primary font-semibold hover:bg-primary/20 transition"
                            >
                                <ExternalLink className="w-4 h-4" />
                                Visit Official Page
                            </a>
                        )}
                    </Accordion>
                </div>

                {/* Similar Scholarships */}
                {similar.length > 0 && (
                    <div className="mt-16">
                        <h3 className="text-xl font-bold mb-4">Similar Scholarships</h3>
                        <div className="flex gap-5 overflow-x-auto pb-4 scrollbar-hide">
                            {similar.map((item) => (
                                <div
                                    key={item.id}
                                    onClick={() => navigate(`/scholarships/${item.id}`)}
                                    className="flex-none w-80 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/50 p-5 hover:shadow-md transition cursor-pointer"
                                >
                                    <h4 className="font-semibold truncate text-lg mb-1 dark:text-slate-200">{item.title}</h4>
                                    <p className="text-primary font-semibold mb-1">{item.reward || "Variable Award"}</p>
                                    <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400 mt-2">
                                         <span>End: {item.end_date || "N/A"}</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
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