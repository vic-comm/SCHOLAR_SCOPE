// import React from "react";

// const ScholarshipCard = ({ scholarship, onToggleBookmark }) => {
//   const { id, title, description, end_date, is_bookmarked } = scholarship;

//   return (
//     <div className="relative flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
//       <button
//         className={`absolute top-3 right-3 flex h-8 w-8 items-center justify-center rounded-full ${
//           is_bookmarked
//             ? "text-primary bg-primary/10"
//             : "text-slate-400 hover:bg-primary/10 hover:text-primary"
//         }`}
//         onClick={() => onToggleBookmark(id, is_bookmarked)}
//       >
//         <span
//           className="material-symbols-outlined text-xl"
//           style={is_bookmarked ? { fontVariationSettings: "'FILL' 1" } : {}}
//         >
//           bookmark
//         </span>
//       </button>

//       <div>
//         <p className="text-slate-900 dark:text-slate-50 text-base font-bold leading-normal pr-8">
//           {title}
//         </p>
//         <p className="text-slate-500 dark:text-slate-400 text-sm font-normal leading-normal mt-2">
//           {description?.slice(0, 100)}...
//         </p>
//       </div>

//       <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400">
//         <span className="material-symbols-outlined text-base">calendar_today</span>
//         <p className="text-xs font-normal">Deadline: {end_date}</p>
//       </div>
//     </div>
//   );
// };

// export default ScholarshipCard;

import React from "react";

const ScholarshipCard = ({ 
  scholarship, 
  onToggleBookmark, 
  onToggleWatch // You'll need to pass this function from the parent
}) => {
  const { 
    id, 
    title, 
    description, 
    end_date, 
    is_bookmarked,
    is_recurring,
    is_watched, // Assuming backend sends this boolean
    status // active vs expired
  } = scholarship;

  const isExpired = status === 'expired';

  return (
    <div className="relative flex flex-col justify-between h-full rounded-xl border border-slate-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow dark:border-slate-800 dark:bg-slate-900">
      
      {/* Top Action Buttons (Bookmark & Watch) */}
      <div className="absolute top-4 right-4 flex gap-2">
        {/* Watch/Bell Button (Only show if it's recurring) */}
        {is_recurring && (
           <button
             onClick={(e) => { e.stopPropagation(); onToggleWatch(id); }}
             className={`flex h-8 w-8 items-center justify-center rounded-full transition-colors ${
               is_watched
                 ? "text-blue-600 bg-blue-100 dark:bg-blue-900/40 dark:text-blue-400"
                 : "text-slate-400 hover:bg-blue-50 hover:text-blue-600 dark:hover:bg-slate-800"
             }`}
             title={is_watched ? "Watching for next cycle" : "Remind me next cycle"}
           >
             <span className="material-symbols-outlined text-xl" style={is_watched ? { fontVariationSettings: "'FILL' 1" } : {}}>
               notifications
             </span>
           </button>
        )}

        {/* Standard Bookmark Button */}
        {!isExpired && (
          <button
            onClick={(e) => { e.stopPropagation(); onToggleBookmark(id, is_bookmarked); }}
            className={`flex h-8 w-8 items-center justify-center rounded-full transition-colors ${
              is_bookmarked
                ? "text-primary bg-primary/10"
                : "text-slate-400 hover:bg-primary/10 hover:text-primary dark:hover:bg-slate-800"
            }`}
          >
            <span className="material-symbols-outlined text-xl" style={is_bookmarked ? { fontVariationSettings: "'FILL' 1" } : {}}>
              bookmark
            </span>
          </button>
        )}
      </div>

      <div>
        {/* Recurring Badge */}
        {is_recurring && (
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400 mb-3 border border-purple-200 dark:border-purple-800/50">
                <span className="material-symbols-outlined" style={{ fontSize: '12px' }}>update</span>
                Recurs Annually
            </span>
        )}

        <p className="text-slate-900 dark:text-slate-50 text-base font-bold leading-normal pr-16">
          {title}
        </p>
        <p className="text-slate-500 dark:text-slate-400 text-sm font-normal leading-normal mt-2 line-clamp-3">
          {description}
        </p>
      </div>

      <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-slate-500 dark:text-slate-400">
          <span className="material-symbols-outlined text-[16px]">
            {isExpired ? 'event_busy' : 'calendar_today'}
          </span>
          <p className={`text-xs font-medium ${isExpired ? 'text-red-500' : ''}`}>
            {isExpired ? 'Cycle Closed' : `Deadline: ${end_date || 'Rolling'}`}
          </p>
        </div>
        
        {/* Expired + Recurring CTA */}
        {isExpired && is_recurring && !is_watched && (
           <button 
             onClick={(e) => { e.stopPropagation(); onToggleWatch(id); }}
             className="text-xs font-semibold text-blue-600 hover:text-blue-800 dark:text-blue-400 flex items-center gap-1"
           >
             Remind Me <span aria-hidden="true">&rarr;</span>
           </button>
        )}
      </div>
    </div>
  );
};

export default ScholarshipCard;