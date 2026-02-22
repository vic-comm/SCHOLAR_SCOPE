import React, { useEffect, useState } from "react";
import api from "../api"; 
import { useNavigate } from "react-router-dom";
import Navbar from '../components/Navbar';
import ExtensionPrompt from '../components/ExtensionPrompt';
import ProfileCompletion from "../components/ProfileCompletion";

const Dashboard = () => {
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        const res = await api.get("users/user_dashboard/");
        setDashboard(res.data);
      } catch (err) {
        console.error("Error fetching dashboard:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchDashboard();
  }, []);

  async function handleRemoveBookmark(scholarshipId) {
    const previousDashboard = { ...dashboard };
    
    setDashboard((prev) => ({
      ...prev,
      bookmarked_scholarships: prev.bookmarked_scholarships.filter(
        (s) => s.id !== scholarshipId
      ),
      stats: {
        ...prev.stats,
        total_bookmarks: Math.max(0, prev.stats.total_bookmarks - 1),
      },
    }));

    try {
      await api.post(`/scholarships/${scholarshipId}/unbookmark/`);
    } catch (err) {
      console.error("Unbookmark failed:", err);
      setDashboard(previousDashboard);
    }
  }

  // Optional: Handle what happens when searching from the Dashboard
  const handleNavbarSearch = (filters) => {
    // Ideally, this redirects to the main list with search params
    // navigate(`/scholarships?q=${filters.query}`);
    console.log("Search triggered from dashboard:", filters);
  };

  if (loading) return <div className="p-6 text-center text-gray-500">Loading dashboard...</div>;
  if (!dashboard) return <div className="p-6 text-center text-gray-500">No data available.</div>;

  const stats = dashboard.stats || {};
  const recentApps = dashboard.recent_applications || [];
  const bookmarks = dashboard.bookmarked_scholarships || [];
  const recommended = dashboard.recommended_scholarships || [];
  const deadlines = dashboard.upcoming_deadlines || [];
  const watched = dashboard.watched_scholarships || [];
  
  return (
    // 1. Wrap everything in a min-height container for background color consistency
    <div className="min-h-screen bg-gray-50 dark:bg-slate-950 font-display">
      
      {/* 2. Add Navbar at the top */}
      <Navbar onFilter={handleNavbarSearch} />

      {/* 3. Main Content Container */}
      <div className="container mx-auto p-4 md:p-6 lg:p-8">
        
        {/* Header */}
        <div className="flex flex-col sm:flex-row items-center gap-6 p-6 bg-white dark:bg-slate-900 rounded-xl shadow-sm border border-slate-200 dark:border-slate-800">
          <div className="rounded-full bg-primary/10 flex items-center justify-center size-20 text-primary font-bold text-3xl">
             👋
          </div>
          <div className="flex-1 text-center sm:text-left">
            <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Welcome back!</h2>
            <p className="text-slate-500 dark:text-slate-400 mt-1">
              Here is your scholarship progress overview.
            </p>
            <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
              <Stat label="Applied" value={stats.total_applications || 0} />
              <Stat label="Saved" value={stats.total_bookmarks || 0} />
              <Stat label="Accepted" value={stats.accepted_applications || 0} color="text-green-600 dark:text-green-400" />
              <Stat label="Pending" value={stats.pending_applications || 0} color="text-yellow-600 dark:text-yellow-400" />
            </div>
          </div>
        </div>

        {/* Profile Completion */}
        <ProfileCompletion percentage={dashboard.stats.profile_completion} />
        {/* Applications */}
        <Section title="My Applications">
          {recentApps.length > 0 ? (
            <div className="space-y-3">
              {recentApps.map((app) => (
                <div
                  key={`${app.is_scrape ? 'scrape' : 'app'}-${app.id}`}
                  className="flex flex-col sm:flex-row justify-between items-center p-4 border border-slate-200 dark:border-slate-800 rounded-lg bg-gray-50 dark:bg-slate-900/50 hover:bg-white dark:hover:bg-slate-900 transition-colors"
                >
                  <div className="mb-3 sm:mb-0 text-center sm:text-left">
                    <p className="font-semibold text-slate-900 dark:text-slate-200">
                      {app.scholarship?.title || "Unknown Title"}
                    </p>
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                      {app.is_scrape ? (
                          <span className="flex items-center gap-1 justify-center sm:justify-start">
                             Added manually • Submitted: {app.submitted_at ? new Date(app.submitted_at).toLocaleDateString() : "N/A"}
                          </span>
                      ) : (
                          <span>Deadline: {app.scholarship?.end_date || "N/A"}</span>
                      )}
                    </p>
                  </div>
                  
                  <div className="flex items-center gap-3">
                    <Badge status={app.status} />
                    {app.is_scrape ? (
                      <button
                          onClick={() => app.scholarship?.link && window.open(app.scholarship.link, '_blank')}
                          className="px-4 py-2 text-sm border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 bg-white dark:bg-slate-900"
                      >
                          Visit Site
                      </button>
                    ) : (
                      <button
                          onClick={() => navigate(`/scholarships/${app.scholarship?.id}`)}
                          className="px-4 py-2 text-sm bg-primary text-white rounded-lg hover:bg-primary/90 shadow-sm"
                      >
                          View Details
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-slate-500">
              You haven't applied to any scholarships yet.
            </div>
          )}
        </Section>

        {/* Upcoming Deadlines */}
        <Section title="Upcoming Deadlines">
          {deadlines.length > 0 ? (
              <div className="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800">
                  {deadlines.map((s, index) => (
                  <div
                      key={s.id}
                      className={`flex justify-between items-center p-4 ${index !== deadlines.length - 1 ? 'border-b border-slate-100 dark:border-slate-800' : ''}`}
                  >
                      <p className="font-medium text-slate-800 dark:text-slate-200 truncate pr-4">{s.title}</p>
                      <p className="text-sm font-semibold text-red-500 whitespace-nowrap">
                          {s.end_date ? new Date(s.end_date).toLocaleDateString() : "ASAP"}
                      </p>
                  </div>
                  ))}
              </div>
          ) : (
              <p className="text-slate-500">No upcoming deadlines.</p>
          )}
        </Section>

        {/* Saved Scholarships */}
        <Section title="Saved Scholarships">
          {bookmarks.length > 0 ? (
              <div className="flex overflow-x-auto gap-4 pb-4 scrollbar-hide">
              {bookmarks.map((s) => (
                  <div
                  key={s.id}
                  className="w-72 flex-shrink-0 border border-slate-200 dark:border-slate-800 rounded-xl p-5 bg-white dark:bg-slate-900 shadow-sm hover:shadow-md transition-shadow"
                  >
                  <div className="h-12 mb-2">
                      <p className="font-semibold text-slate-900 dark:text-white line-clamp-2 leading-tight">
                          {s.title}
                      </p>
                  </div>
                  <p className="text-sm text-slate-500 dark:text-slate-400 mb-4 h-10 line-clamp-2">
                      {s.description || "No description available."}
                  </p>
                  <div className="flex gap-2 mt-auto">
                      <button
                      onClick={() => navigate(`/scholarships/${s.id}`)}
                      className="flex-1 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary/90"
                      >
                      Apply Now
                      </button>
                      <button
                      onClick={() => handleRemoveBookmark(s.id)}
                      className="p-2 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/40 border border-red-100 dark:border-transparent"
                      title="Remove from saved"
                      >
                      ✕
                      </button>
                  </div>
                  </div>
              ))}
              </div>
          ) : (
              <p className="text-slate-500">No saved scholarships.</p>
          )}
        </Section>
        
        {/* Watched scholarships */}
        <Section title="Watching for Next Cycle">
          {watched.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {watched.map((s) => (
                <div
                  key={s.id}
                  className="flex items-center justify-between p-4 border border-blue-200 dark:border-blue-900/50 bg-blue-50/50 dark:bg-blue-900/10 rounded-xl"
                >
                  <div className="pr-4">
                    <p className="font-semibold text-slate-900 dark:text-white line-clamp-1">
                      {s.title}
                    </p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="material-symbols-outlined text-[14px] text-blue-600 dark:text-blue-400">
                        notifications_active
                      </span>
                      <p className="text-xs text-blue-600 dark:text-blue-400 font-medium">
                        We'll email you when this opens.
                      </p>
                    </div>
                  </div>
                  
                  <div className="flex flex-col items-end gap-2 shrink-0">
                    {/* Unwatch Button */}
                    <button
                      onClick={async () => {
                        // Call the exact same endpoint to toggle (unwatch)
                        await api.post(`scholarships/${s.id}/toggle_watch_scholarship/`);
                        // Remove it from the dashboard UI instantly
                        setDashboard(prev => ({
                            ...prev,
                            watched_scholarships: prev.watched_scholarships.filter(item => item.id !== s.id)
                        }));
                      }}
                      className="text-xs text-slate-500 hover:text-red-500 transition-colors"
                    >
                      Stop watching
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-4 border border-dashed border-slate-300 dark:border-slate-700 rounded-xl text-center text-slate-500 text-sm">
              You aren't watching any recurring scholarships.
            </div>
          )}
        </Section>

        {/* Recommended */}
        <Section title="Recommended for You">
          {recommended.length > 0 ? (
              <div className="flex overflow-x-auto gap-4 pb-4 scrollbar-hide">
              {recommended.map((s) => (
                  <div
                  key={s.id}
                  onClick={() => navigate(`/scholarships/${s.id}`)}
                  className="w-72 flex-shrink-0 border border-slate-200 dark:border-slate-800 rounded-xl p-5 bg-white dark:bg-slate-900 cursor-pointer hover:border-primary/50 transition-colors group"
                  >
                  <p className="font-semibold text-slate-900 dark:text-white group-hover:text-primary transition-colors truncate">
                      {s.title}
                  </p>
                  <p className="text-sm text-slate-500 dark:text-slate-400 mt-2 line-clamp-2 h-10">
                      {s.description}
                  </p>
                  <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-800 flex justify-between items-center">
                      <span className="text-xs text-slate-400">Deadline</span>
                      <span className="text-xs font-medium text-slate-700 dark:text-slate-300">
                          {s.end_date || "Rolling"}
                      </span>
                  </div>
                  </div>
              ))}
              </div>
          ) : (
              <p className="text-slate-500">No recommendations available yet.</p>
          )}
        </Section>
      </div>
    <ExtensionPrompt />
    </div>

  );
};

// --- Sub Components ---

const Stat = ({ label, value, color }) => (
  <div className="bg-gray-50 dark:bg-slate-800/50 p-3 rounded-lg text-center border border-transparent dark:border-slate-700">
    <p className={`text-2xl font-bold ${color || "text-slate-900 dark:text-white"}`}>{value}</p>
    <p className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">{label}</p>
  </div>
);

const Section = ({ title, children }) => (
  <div className="mt-8">
    <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
        {title}
    </h3>
    {children}
  </div>
);

const Badge = ({ status }) => {
    const styles = {
        pending: "bg-yellow-100 text-yellow-700 border-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-400 dark:border-yellow-800",
        accepted: "bg-green-100 text-green-700 border-green-200 dark:bg-green-900/30 dark:text-green-400 dark:border-green-800",
        rejected: "bg-red-100 text-red-700 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800",
        submitted: "bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-800",
    };

    const defaultStyle = "bg-gray-100 text-gray-700 border-gray-200 dark:bg-gray-800 dark:text-gray-400";

    return (
        <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium border ${styles[status?.toLowerCase()] || defaultStyle} capitalize`}>
            {status || "Unknown"}
        </span>
    );
};

export default Dashboard;