// import React from "react";

// const ScholarshipCard = ({ 
//   scholarship, 
//   onToggleBookmark, 
//   onToggleWatch 
// }) => {
//   const { 
//     id, 
//     title, 
//     description, 
//     end_date, 
//     is_bookmarked,
//     is_recurring,
//     is_watched, // Assuming backend sends this boolean
//     status // active vs expired
//   } = scholarship;

//   const isExpired = status === 'expired';

//   return (
//     <div className="relative flex flex-col justify-between h-full rounded-xl border border-slate-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow dark:border-slate-800 dark:bg-slate-900">
      
//       {/* Top Action Buttons (Bookmark & Watch) */}
//       <div className="absolute top-4 right-4 flex gap-2">
//         {/* Watch/Bell Button (Only show if it's recurring) */}
//         {is_recurring && (
//            <button
//              onClick={(e) => { e.preventDefault(); e.stopPropagation(); onToggleWatch(id); }}
//              className={`flex h-8 w-8 items-center justify-center rounded-full transition-colors ${
//                is_watched
//                  ? "text-blue-600 bg-blue-100 dark:bg-blue-900/40 dark:text-blue-400"
//                  : "text-slate-400 hover:bg-blue-50 hover:text-blue-600 dark:hover:bg-slate-800"
//              }`}
//              title={is_watched ? "Watching for next cycle" : "Remind me next cycle"}
//            >
//              <span className="material-symbols-outlined text-xl" style={is_watched ? { fontVariationSettings: "'FILL' 1" } : {}}>
//                notifications
//              </span>
//            </button>
//         )}

//         {/* Standard Bookmark Button */}
//         {!isExpired && (
//           <button
//             onClick={(e) => { e.preventDefault(); e.stopPropagation(); onToggleBookmark(id, is_bookmarked); }}
//             className={`flex h-8 w-8 items-center justify-center rounded-full transition-colors ${
//               is_bookmarked
//                 ? "text-primary bg-primary/10"
//                 : "text-slate-400 hover:bg-primary/10 hover:text-primary dark:hover:bg-slate-800"
//             }`}
//           >
//             <span className="material-symbols-outlined text-xl" style={is_bookmarked ? { fontVariationSettings: "'FILL' 1" } : {}}>
//               bookmark
//             </span>
//           </button>
//         )}
//       </div>

//       <div>
//         {/* Recurring Badge */}
//         {is_recurring && (
//             <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400 mb-3 border border-purple-200 dark:border-purple-800/50">
//                 <span className="material-symbols-outlined" style={{ fontSize: '12px' }}>update</span>
//                 Recurs Annually
//             </span>
//         )}

//         <p className="text-slate-900 dark:text-slate-50 text-base font-bold leading-normal pr-16">
//           {title}
//         </p>
//         <p className="text-slate-500 dark:text-slate-400 text-sm font-normal leading-normal mt-2 line-clamp-3">
//           {description}
//         </p>
//       </div>

//       <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between">
//         <div className="flex items-center gap-1.5 text-slate-500 dark:text-slate-400">
//           <span className="material-symbols-outlined text-[16px]">
//             {isExpired ? 'event_busy' : 'calendar_today'}
//           </span>
//           <p className={`text-xs font-medium ${isExpired ? 'text-red-500' : ''}`}>
//             {isExpired ? 'Cycle Closed' : `Deadline: ${end_date || 'Rolling'}`}
//           </p>
//         </div>
        
//         {/* Expired + Recurring CTA */}
//         {isExpired && is_recurring && !is_watched && (
//            <button 
//              onClick={(e) => { e.preventDefault(); e.stopPropagation(); onToggleWatch(id); }}
//              className="text-xs font-semibold text-blue-600 hover:text-blue-800 dark:text-blue-400 flex items-center gap-1"
//            >
//              Remind Me <span aria-hidden="true">&rarr;</span>
//            </button>
//         )}
//       </div>
//     </div>
//   );
// };

// export default ScholarshipCard;

import React from "react";

const ScholarshipCard = ({
  scholarship,
  onToggleBookmark,
  onToggleWatch,
}) => {
  const {
    id,
    title,
    description,
    end_date,
    reward,
    is_bookmarked,
    is_recurring,
    is_watched,
    status,
    tags,
  } = scholarship;

  const isExpired = status === "expired";

  // Deadline urgency — highlight if within 14 days
  const daysUntilDeadline = (() => {
    if (!end_date || isExpired) return null;
    const diff = Math.ceil((new Date(end_date) - new Date()) / (1000 * 60 * 60 * 24));
    return diff >= 0 ? diff : null;
  })();
  const isUrgent = daysUntilDeadline !== null && daysUntilDeadline <= 14;

  return (
    <div
      className={`
        relative flex flex-col justify-between h-full rounded-xl border bg-white p-5
        shadow-sm hover:shadow-md transition-all duration-200
        dark:bg-slate-900
        ${isExpired
          ? "border-slate-200 dark:border-slate-800 opacity-75"
          : "border-slate-200 dark:border-slate-800 hover:-translate-y-0.5"
        }
      `}
    >
      {/* Top action buttons */}
      <div className="absolute top-4 right-4 flex gap-1.5">
        {is_recurring && (
          <button
            onClick={(e) => { e.preventDefault(); e.stopPropagation(); onToggleWatch(id); }}
            className={`
              flex h-8 w-8 items-center justify-center rounded-full transition-all duration-150
              ${is_watched
                ? "text-blue-600 bg-blue-100 dark:bg-blue-900/40 dark:text-blue-400 scale-110"
                : "text-slate-400 hover:bg-blue-50 hover:text-blue-600 dark:hover:bg-slate-800"
              }
            `}
            title={is_watched ? "Watching for next cycle" : "Remind me next cycle"}
            aria-pressed={is_watched}
          >
            <span
              className="material-symbols-outlined text-xl"
              style={is_watched ? { fontVariationSettings: "'FILL' 1" } : {}}
            >
              notifications
            </span>
          </button>
        )}

        {!isExpired && (
          <button
            onClick={(e) => { e.preventDefault(); e.stopPropagation(); onToggleBookmark(id, is_bookmarked); }}
            className={`
              flex h-8 w-8 items-center justify-center rounded-full transition-all duration-150
              ${is_bookmarked
                ? "text-primary bg-primary/10 scale-110"
                : "text-slate-400 hover:bg-primary/10 hover:text-primary dark:hover:bg-slate-800"
              }
            `}
            title={is_bookmarked ? "Remove bookmark" : "Bookmark"}
            aria-pressed={is_bookmarked}
            aria-label={is_bookmarked ? "Remove bookmark" : "Bookmark this scholarship"}
          >
            <span
              className="material-symbols-outlined text-xl"
              style={is_bookmarked ? { fontVariationSettings: "'FILL' 1" } : {}}
            >
              bookmark
            </span>
          </button>
        )}
      </div>

      {/* Card body */}
      <div>
        {/* Badges row */}
        <div className="flex flex-wrap items-center gap-1.5 mb-3 pr-16 min-h-[22px]">
          {is_recurring && (
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400 border border-purple-200 dark:border-purple-800/50">
              <span className="material-symbols-outlined" style={{ fontSize: "12px" }}>update</span>
              Recurs Annually
            </span>
          )}
          {isExpired && (
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400 border border-slate-200 dark:border-slate-700">
              <span className="material-symbols-outlined" style={{ fontSize: "12px" }}>event_busy</span>
              Cycle Closed
            </span>
          )}
          {isUrgent && !isExpired && (
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 border border-amber-200 dark:border-amber-800/50">
              <span className="material-symbols-outlined" style={{ fontSize: "12px" }}>schedule</span>
              {daysUntilDeadline === 0 ? "Due today" : `${daysUntilDeadline}d left`}
            </span>
          )}
        </div>

        {/* Title */}
        <p className="text-slate-900 dark:text-slate-50 text-base font-bold leading-normal pr-16">
          {title}
        </p>

        {/* Reward */}
        {/* {reward && (
          <p className="text-primary font-semibold text-sm mt-1">{reward}</p>
        )} */}
        <p className="text-primary font-semibold text-sm mt-1">
          {reward && reward.length > 100 ? reward.slice(0, 100) + "..." : reward}
        </p>

        {/* Description */}
        {/* <p className="text-slate-500 dark:text-slate-400 text-sm font-normal leading-normal mt-2 line-clamp-3">
          {description}
        </p> */}

        {/* Tags — up to 2 */}
        {tags?.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-3">
            {tags.slice(0, 2).map((tag, i) => (
              <span
                key={i}
                className="px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 text-xs font-medium"
              >
                {tag.name || tag}
              </span>
            ))}
            {tags.length > 2 && (
              <span className="px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-400 text-xs">
                +{tags.length - 2}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-slate-500 dark:text-slate-400">
          <span className="material-symbols-outlined text-[16px]">
            {isExpired ? "event_busy" : "calendar_today"}
          </span>
          <p className={`text-xs font-medium ${isUrgent && !isExpired ? "text-amber-600 dark:text-amber-400" : isExpired ? "text-slate-400" : ""}`}>
            {isExpired
              ? "Cycle Closed"
              : daysUntilDeadline === 0
                ? "Due today"
                : `Deadline: ${end_date || "Rolling"}`
            }
          </p>
        </div>

        {/* Bookmark status hint */}
        {is_bookmarked && !isExpired && (
          <span className="text-xs font-medium text-primary flex items-center gap-1">
            <span
              className="material-symbols-outlined text-[14px]"
              style={{ fontVariationSettings: "'FILL' 1" }}
            >
              bookmark
            </span>
            Saved
          </span>
        )}

        {/* Expired + recurring CTA */}
        {isExpired && is_recurring && !is_watched && (
          <button
            onClick={(e) => { e.preventDefault(); e.stopPropagation(); onToggleWatch(id); }}
            className="text-xs font-semibold text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 flex items-center gap-1 transition-colors"
          >
            Remind Me <span aria-hidden="true">&rarr;</span>
          </button>
        )}

        {/* Expired + recurring + already watching */}
        {isExpired && is_recurring && is_watched && (
          <span className="text-xs font-medium text-blue-600 dark:text-blue-400 flex items-center gap-1">
            <span
              className="material-symbols-outlined text-[14px]"
              style={{ fontVariationSettings: "'FILL' 1" }}
            >
              notifications
            </span>
            Watching
          </span>
        )}
      </div>
    </div>
  );
};

export default ScholarshipCard;