import React, { useState } from "react";

// ── Tooltip wrapper ────────────────────────────────────────────────────────────
// Simple CSS-only tooltip so users always know what a button does.
function Tip({ label, children }) {
  return (
    <div className="relative group/tip">
      {children}
      <div className="
        pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2
        whitespace-nowrap rounded-md bg-slate-900 dark:bg-slate-700
        px-2 py-1 text-[10px] font-medium tracking-wide text-white
        opacity-0 group-hover/tip:opacity-100 transition-opacity duration-150 z-50
        shadow-lg
      ">
        {label}
        <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-900 dark:border-t-slate-700" />
      </div>
    </div>
  );
}

const ScholarshipCard = ({ scholarship, onToggleBookmark, onToggleSave, onToggleWatch }) => {
  const {
    id,
    title,
    end_date,
    reward,
    is_bookmarked,
    is_saved,
    is_recurring,
    is_watched,
    status,
    tags,
    level,
  } = scholarship;

  const isExpired = status === "expired";

  const daysUntilDeadline = (() => {
    if (!end_date || isExpired) return null;
    const diff = Math.ceil((new Date(end_date) - new Date()) / (1000 * 60 * 60 * 24));
    return diff >= 0 ? diff : null;
  })();

  const urgency =
    daysUntilDeadline === null ? "none"
    : daysUntilDeadline === 0  ? "today"
    : daysUntilDeadline <= 3   ? "critical"   // red
    : daysUntilDeadline <= 14  ? "soon"        // amber
    : "ok";                                    // green

  const deadlineColour = {
    none:     "text-slate-400 dark:text-slate-500",
    today:    "text-red-600 dark:text-red-400 font-semibold",
    critical: "text-red-500 dark:text-red-400 font-semibold",
    soon:     "text-amber-600 dark:text-amber-400 font-medium",
    ok:       "text-slate-500 dark:text-slate-400",
  }[urgency];

  const deadlineText =
    isExpired          ? "Cycle closed"
    : urgency === "today" ? "Due today"
    : end_date         ? end_date
    : "Rolling";

  // Truncate reward to keep cards compact
  const rewardText = reward
    ? (reward.length > 60 ? reward.slice(0, 60) + "…" : reward)
    : null;

  const stop = (e) => { e.preventDefault(); e.stopPropagation(); };

  return (
    <article className={`
      group relative flex flex-col
      rounded-2xl border bg-white dark:bg-slate-900
      shadow-sm hover:shadow-md
      transition-all duration-200
      ${isExpired
        ? "border-slate-200 dark:border-slate-800 opacity-60"
        : "border-slate-200 dark:border-slate-800 hover:-translate-y-0.5"
      }
    `}>

      {/* ── Urgency accent line at top ───────────────────────────────────── */}
      {!isExpired && urgency !== "none" && urgency !== "ok" && (
        <div className={`
          h-0.5 rounded-t-2xl w-full
          ${urgency === "critical" || urgency === "today" ? "bg-red-500" : "bg-amber-400"}
        `} />
      )}

      {/* ── Card body ────────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-2 p-4 flex-1">

        {/* Top row: badges + recurring indicator */}
        <div className="flex items-center gap-1.5 flex-wrap min-h-[20px]">
          {is_recurring && (
            <span className="inline-flex items-center gap-0.5 px-2 py-0.5 rounded-full text-[10px] font-semibold tracking-wide bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300 border border-violet-200 dark:border-violet-800/40">
              <span className="material-symbols-outlined" style={{ fontSize: "10px" }}>autorenew</span>
              Annual
            </span>
          )}
          {isExpired && (
            <span className="inline-flex items-center gap-0.5 px-2 py-0.5 rounded-full text-[10px] font-semibold tracking-wide bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400 border border-slate-200 dark:border-slate-700">
              Closed
            </span>
          )}
          {(urgency === "critical" || urgency === "today") && (
            <span className="inline-flex items-center gap-0.5 px-2 py-0.5 rounded-full text-[10px] font-semibold tracking-wide bg-red-50 text-red-600 dark:bg-red-900/20 dark:text-red-400 border border-red-200 dark:border-red-800/40">
              <span className="material-symbols-outlined" style={{ fontSize: "10px" }}>schedule</span>
              {urgency === "today" ? "Due today" : `${daysUntilDeadline}d left`}
            </span>
          )}
          {urgency === "soon" && (
            <span className="inline-flex items-center gap-0.5 px-2 py-0.5 rounded-full text-[10px] font-semibold tracking-wide bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400 border border-amber-200 dark:border-amber-800/40">
              <span className="material-symbols-outlined" style={{ fontSize: "10px" }}>schedule</span>
              {daysUntilDeadline}d left
            </span>
          )}
        </div>

        {/* Title — 2 lines max, no overflow causing card growth */}
        <h3 className="text-[13px] font-bold leading-snug text-slate-900 dark:text-slate-50 line-clamp-2">
          {title}
        </h3>

        {/* Reward */}
        {rewardText && (
          <p className="text-[12px] font-semibold text-emerald-600 dark:text-emerald-400 line-clamp-1">
            {rewardText}
          </p>
        )}

        {/* Tags — 2 max */}
        {tags?.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-0.5">
            {tags.slice(0, 2).map((tag, i) => (
              <span
                key={i}
                className="px-1.5 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 text-[10px] font-medium"
              >
                {tag.name || tag}
              </span>
            ))}
            {tags.length > 2 && (
              <span className="px-1.5 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-400 text-[10px]">
                +{tags.length - 2}
              </span>
            )}
          </div>
        )}
      </div>

      {/* ── Footer: deadline + actions ───────────────────────────────────── */}
      <div className="px-4 pb-3 flex items-center justify-between gap-2 border-t border-slate-100 dark:border-slate-800 pt-3">

        {/* Deadline */}
        <div className={`flex items-center gap-1 text-[11px] ${deadlineColour} min-w-0`}>
          <span className="material-symbols-outlined flex-shrink-0" style={{ fontSize: "13px" }}>
            {isExpired ? "event_busy" : "calendar_today"}
          </span>
          <span className="truncate">{deadlineText}</span>
        </div>

        {/* Action buttons — always labelled */}
        <div className="flex items-center gap-1 flex-shrink-0">

          {/* WATCH — only for recurring scholarships */}
          {is_recurring && (
            <Tip label={is_watched ? "Stop watching" : "Notify me next cycle"}>
              <button
                onClick={(e) => { stop(e); onToggleWatch?.(id); }}
                aria-pressed={is_watched}
                aria-label={is_watched ? "Stop watching" : "Watch for next cycle"}
                className={`
                  flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-semibold
                  transition-all duration-150
                  ${is_watched
                    ? "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300"
                    : "bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 hover:bg-blue-50 hover:text-blue-600 dark:hover:bg-blue-900/20 dark:hover:text-blue-400"
                  }
                `}
              >
                <span
                  className="material-symbols-outlined"
                  style={{ fontSize: "12px", ...(is_watched ? { fontVariationSettings: "'FILL' 1" } : {}) }}
                >
                  notifications
                </span>
                <span className="hidden sm:inline">{is_watched ? "Watching" : "Watch"}</span>
              </button>
            </Tip>
          )}

          {/* APPLY — saves as pending application */}
          {!isExpired && (
            <Tip label={is_saved ? "In your applications" : "Save as pending application"}>
              <button
                onClick={(e) => { stop(e); onToggleSave?.(id, is_saved); }}
                aria-pressed={is_saved}
                aria-label={is_saved ? "Remove from applications" : "Add to applications"}
                className={`
                  flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-semibold
                  transition-all duration-150
                  ${is_saved
                    ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300"
                    : "bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 hover:bg-emerald-50 hover:text-emerald-600 dark:hover:bg-emerald-900/20 dark:hover:text-emerald-400"
                  }
                `}
              >
                <span
                  className="material-symbols-outlined"
                  style={{ fontSize: "12px", ...(is_saved ? { fontVariationSettings: "'FILL' 1" } : {}) }}
                >
                  {is_saved ? "task_alt" : "add_task"}
                </span>
                <span className="hidden sm:inline">{is_saved ? "Applying" : "Apply"}</span>
              </button>
            </Tip>
          )}

          {/* BOOKMARK — save for later reading */}
          {!isExpired && (
            <Tip label={is_bookmarked ? "Remove bookmark" : "Bookmark for later"}>
              <button
                onClick={(e) => { stop(e); onToggleBookmark?.(id, is_bookmarked); }}
                aria-pressed={is_bookmarked}
                aria-label={is_bookmarked ? "Remove bookmark" : "Bookmark this scholarship"}
                className={`
                  flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-semibold
                  transition-all duration-150
                  ${is_bookmarked
                    ? "bg-primary/10 text-primary dark:bg-primary/20"
                    : "bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 hover:bg-primary/10 hover:text-primary dark:hover:bg-primary/10"
                  }
                `}
              >
                <span
                  className="material-symbols-outlined"
                  style={{ fontSize: "12px", ...(is_bookmarked ? { fontVariationSettings: "'FILL' 1" } : {}) }}
                >
                  bookmark
                </span>
                <span className="hidden sm:inline">{is_bookmarked ? "Saved" : "Save"}</span>
              </button>
            </Tip>
          )}

          {/* EXPIRED + RECURRING: only show Watch CTA */}
          {isExpired && is_recurring && (
            <Tip label={is_watched ? "Already watching" : "Get notified when this reopens"}>
              <button
                onClick={(e) => { stop(e); onToggleWatch?.(id); }}
                disabled={is_watched}
                className={`
                  flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-semibold
                  transition-all duration-150
                  ${is_watched
                    ? "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300 cursor-default"
                    : "bg-slate-100 dark:bg-slate-800 text-slate-500 hover:bg-blue-50 hover:text-blue-600 dark:hover:bg-blue-900/20 dark:hover:text-blue-400"
                  }
                `}
              >
                <span
                  className="material-symbols-outlined"
                  style={{ fontSize: "12px", ...(is_watched ? { fontVariationSettings: "'FILL' 1" } : {}) }}
                >
                  notifications
                </span>
                <span className="hidden sm:inline">{is_watched ? "Watching" : "Notify me"}</span>
              </button>
            </Tip>
          )}
        </div>
      </div>

    </article>
  );
};

export default ScholarshipCard;