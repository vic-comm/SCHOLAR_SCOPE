import React from "react";

const ScholarshipCard = ({ scholarship, onToggleBookmark }) => {
  const { id, title, description, end_date, is_bookmarked } = scholarship;

  return (
    <div className="relative flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <button
        className={`absolute top-3 right-3 flex h-8 w-8 items-center justify-center rounded-full ${
          is_bookmarked
            ? "text-primary bg-primary/10"
            : "text-slate-400 hover:bg-primary/10 hover:text-primary"
        }`}
        onClick={() => onToggleBookmark(id, is_bookmarked)}
      >
        <span
          className="material-symbols-outlined text-xl"
          style={is_bookmarked ? { fontVariationSettings: "'FILL' 1" } : {}}
        >
          bookmark
        </span>
      </button>

      <div>
        <p className="text-slate-900 dark:text-slate-50 text-base font-bold leading-normal pr-8">
          {title}
        </p>
        <p className="text-slate-500 dark:text-slate-400 text-sm font-normal leading-normal mt-2">
          {description?.slice(0, 100)}...
        </p>
      </div>

      <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400">
        <span className="material-symbols-outlined text-base">calendar_today</span>
        <p className="text-xs font-normal">Deadline: {end_date}</p>
      </div>
    </div>
  );
};

export default ScholarshipCard;
