import React, { useEffect, useState } from "react";
import api from "../api"; 
import { useNavigate } from "react-router-dom";

const Dashboard = () => {
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        const res = await api.get("user/user_dashboard/");
        setDashboard(res.data);
      } catch (err) {
        console.error("Error fetching dashboard:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchDashboard();
  }, []);

  async function handleBookmark() {
        const previousState = scholarship.is_bookmarked;
        setScholarship(prev => ({ ...prev, is_bookmarked: !previousState }));

        try {
            if (previousState) {
                await api.post(`/scholarships/${id}/unbookmark/`);
            } else {
                await api.post(`/scholarships/${id}/bookmark_scholarship/`);
            }
        } catch (err) {
            console.error("Bookmark failed:", err);
            setScholarship(prev => ({ ...prev, is_bookmarked: previousState }));
        }
    }

    
    async function handleApply() {
        window.open(scholarship.link, '_blank');
        try {
            await api.post(`/scholarships/${id}/save/`);
        } catch (err) {
            console.error("Failed to track application:", err);
        }
    }

  if (loading) return <div className="p-6 text-center">Loading dashboard...</div>;
  if (!dashboard) return <div className="p-6 text-center">No data available.</div>;

  const stats = dashboard.stats;
  const recentApps = dashboard.recent_applications;
  const bookmarks = dashboard.bookmarked_scholarships;
  const recommended = dashboard.recommended_scholarships;
  const deadlines = dashboard.upcoming_deadlines;

  return (
    <div className="container mx-auto p-4 md:p-6 lg:p-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-center gap-6 p-6 bg-white dark:bg-gray-800 rounded-xl shadow border border-gray-200 dark:border-gray-700">
        <div className="rounded-full bg-gray-300 dark:bg-gray-600 size-20" />
        <div className="flex-1 text-center sm:text-left">
          <h2 className="text-2xl font-bold">Welcome back!</h2>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Here's your scholarship progress.
          </p>
          <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
            <Stat label="Applied" value={stats.total_applications} />
            <Stat label="Saved" value={stats.total_bookmarks} />
            <Stat label="Accepted" value={stats.accepted_applications} color="text-green-500" />
            <Stat label="Pending" value={stats.pending_applications} color="text-yellow-500" />
          </div>
        </div>
      </div>

      {/* Applications */}
      <Section title="My Applications">
        {recentApps.length > 0 ? (
          recentApps.map((app) => (
            <div
              key={app.id}
              className="flex flex-col sm:flex-row justify-between items-center p-4 border rounded-lg bg-gray-50 dark:bg-gray-900"
            >
              <div>
                <p className="font-medium">{app.scholarship.title}</p>
                <p className="text-sm text-gray-500">
                  Deadline: {app.scholarship.end_date}
                </p>
              </div>
              <div className="flex gap-3">
                <span className="capitalize font-semibold text-sm text-blue-600">
                  {app.status}
                </span>
                <button
                  onClick={() => navigate(`/scholarships/${app.scholarship.id}`)}
                  className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg"
                >
                  View
                </button>
              </div>
            </div>
          ))
        ) : (
          <p>No applications yet.</p>
        )}
      </Section>

      {/* Upcoming Deadlines */}
      <Section title="Upcoming Deadlines">
        {deadlines.map((s) => (
          <div
            key={s.id}
            className="flex justify-between p-3 border-b last:border-0 text-sm"
          >
            <p>{s.title}</p>
            <p className="text-red-500">{new Date(s.end_date).toDateString()}</p>
          </div>
        ))}
      </Section>

      {/* Saved Scholarships */}
      <Section title="Saved Scholarships">
        <div className="flex overflow-x-auto gap-4 pb-2">
          {bookmarks.map((s) => (
            <div
              key={s.id}
              className="w-64 flex-shrink-0 border rounded-lg p-4 bg-white dark:bg-gray-800"
            >
              <p className="font-semibold mb-2">{s.title}</p>
              <p className="text-sm text-gray-500 line-clamp-2">{s.description}</p>
              <div className="mt-3 flex gap-2">
                <button
                  onClick={() => navigate(`/scholarships/${s.id}`)}
                  className="flex-1 py-2 bg-blue-600 text-white rounded-lg text-sm"
                >
                  Apply
                </button>
                <button
                  onClick={() => handleBookmark(s.id)}
                  className="p-2 bg-red-100 dark:bg-red-800/50 text-red-600 dark:text-red-400 rounded-lg"
                >
                  🗑
                </button>
              </div>
            </div>
          ))}
        </div>
      </Section>

      {/* Recommended */}
      <Section title="Recommended for You">
        <div className="flex overflow-x-auto gap-4 pb-2">
          {recommended.map((s) => (
            <div
              key={s.id}
              className="w-72 flex-shrink-0 border rounded-lg p-4 bg-white dark:bg-gray-800"
            >
              <p className="font-semibold">{s.title}</p>
              <p className="text-sm text-gray-500 mt-1 line-clamp-2">
                {s.description}
              </p>
              <p className="text-xs text-gray-400 mt-2">
                Deadline: {s.end_date}
              </p>
            </div>
          ))}
        </div>
      </Section>
    </div>
  );
};

// Components
const Stat = ({ label, value, color }) => (
  <div>
    <p className={`text-xl font-bold ${color || ""}`}>{value}</p>
    <p className="text-xs text-gray-500">{label}</p>
  </div>
);

const Section = ({ title, children }) => (
  <div className="mt-8 bg-white dark:bg-gray-800 p-6 rounded-xl shadow border border-gray-200 dark:border-gray-700">
    <h3 className="text-xl font-bold mb-4">{title}</h3>
    {children}
  </div>
);

export default Dashboard;
