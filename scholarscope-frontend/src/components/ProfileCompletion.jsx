import React from 'react';
import { useNavigate } from 'react-router-dom';

const ProfileCompletion = ({ percentage }) => {
  const navigate = useNavigate();

  // Color logic: Red for low, Yellow for medium, Green for high
  const getColor = (score) => {
    if (score < 40) return "bg-red-500";
    if (score < 80) return "bg-yellow-500";
    return "bg-green-500";
  };

  const getTextColor = (score) => {
    if (score < 40) return "text-red-600 dark:text-red-400";
    if (score < 80) return "text-yellow-600 dark:text-yellow-400";
    return "text-green-600 dark:text-green-400";
  };

  // Optional: Hide completely if 100% (uncomment if you prefer that)
  if (percentage >= 100) return null;

  return (
    <div className="bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm mb-8 transition-colors">
      
      {/* Header Section */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end mb-4 gap-2">
        <div>
          <h3 className="font-bold text-lg text-slate-900 dark:text-white">
            Profile Completion
          </h3>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 max-w-lg">
            Complete your profile to receive more accurate scholarship matches and increase your acceptance chances.
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          <span className={`text-2xl font-bold ${getTextColor(percentage)}`}>
            {percentage}%
          </span>
        </div>
      </div>

      {/* Progress Bar Track */}
      <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-3 mb-4 overflow-hidden border border-slate-100 dark:border-slate-700">
        {/* Progress Bar Fill */}
        <div 
          className={`h-full rounded-full transition-all duration-1000 ease-out ${getColor(percentage)}`}
          style={{ width: `${percentage}%` }}
        ></div>
      </div>

      {/* Call to Action */}
      {percentage < 100 ? (
        <button 
          onClick={() => navigate('/profile')}
          className="text-sm font-semibold text-primary hover:text-primary/80 dark:text-blue-400 dark:hover:text-blue-300 flex items-center gap-1 transition-colors"
        >
          Complete my profile <span aria-hidden="true">→</span>
        </button>
      ) : (
        <p className="text-sm font-medium text-green-600 dark:text-green-400 flex items-center gap-2">
          <span>✅</span> Your profile is optimized!
        </p>
      )}
    </div>
  );
};

export default ProfileCompletion;