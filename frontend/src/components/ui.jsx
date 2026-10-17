import { useEffect, useLayoutEffect, useRef, useState } from "react";

import { useI18n } from "../i18n";
import { useCountUp } from "../motion";
import { Icon } from "./Icon";

export function Spinner() {
  const { t } = useI18n();
  return (
    <div role="status" aria-live="polite">
      <div className="spinner" />
      <span className="sr-only">{t("common.loading")}</span>
    </div>
  );
}

export function ErrorMessage({ error, onRetry }) {
  const { t } = useI18n();
  if (!error) return null;
  return (
    <div className="alert alert-error" role="alert">
      <div>{error.message || t("common.error")}</div>
      {onRetry && (
        <button className="btn btn-sm btn-secondary" style={{ marginTop: 8 }} onClick={onRetry}>
          {t("common.retry")}
        </button>
      )}
    </div>
  );
}

/** A placeholder shaped like what is loading, with a light passing over it. Screen readers hear "Loading". */
export function Skeleton({ className = "", children }) {
  const { t } = useI18n();
  return (
    <div role="status" aria-live="polite">
      <span className="sr-only">{t("common.loading")}</span>
      <div className={className} aria-hidden="true">
        {children}
      </div>
    </div>
  );
}

const many = (count, render) => Array.from({ length: count }, (_, i) => render(i));

/** Cards with an icon and two lines (subjects, classes); `progress` adds a bar like the subjects' one. */
export function SkeletonCards({ count = 6, layout = "grid", progress = false }) {
  return (
    <Skeleton className={layout}>
      {many(count, (i) => (
        <div className="card skeleton" key={i}>
          <div className="sk-row">
            <span className="sk sk-tile" />
            <span className="sk-lines">
              <span className="sk sk-title" />
              <span className="sk" style={{ width: "40%" }} />
            </span>
          </div>
          {progress && <span className="sk sk-bar" style={{ marginTop: 14 }} />}
        </div>
      ))}
    </Skeleton>
  );
}

/** Rows in a card (a leaderboard, a list of lessons): `lead` is "tile", "dot" or "rank" (a rank and an avatar). */
export function SkeletonRows({ count = 6, lead = "tile", trail = true }) {
  return (
    <div className="card skeleton skeleton-list">
      {many(count, (i) => (
        <div className="sk-row" key={i}>
          {lead === "rank" && <span className="sk sk-circle" />}
          <span className={`sk ${lead === "tile" ? "sk-tile" : "sk-circle"}`} style={lead === "dot" ? { width: 22, height: 22 } : undefined} />
          <span className="sk-lines">
            <span className="sk" style={{ width: `${70 - (i % 3) * 12}%` }} />
            {lead !== "rank" && <span className="sk" style={{ width: "30%", height: 10 }} />}
          </span>
          {trail && <span className="sk sk-pill" />}
        </div>
      ))}
    </div>
  );
}

/** Renders loading / error states, then `children(data)`. `skeleton` is shown while loading (else a spinner). */
export function Loader({ state, children, skeleton }) {
  if (state.loading && !state.data) return skeleton || <Spinner />;
  if (state.error) return <ErrorMessage error={state.error} onRetry={state.reload} />;
  if (!state.data) return null;
  return children(state.data);
}

export function Empty({ icon = "inbox", children }) {
  return (
    <div className="empty">
      <div className="big">
        <Icon name={icon} size={40} strokeWidth={1.6} />
      </div>
      <p>{children}</p>
    </div>
  );
}

export function Progress({ value, max = 100, label }) {
  const pct = max ? Math.min(100, Math.round((value / max) * 100)) : 0;
  return (
    <div className="progress" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label={label}>
      <span style={{ width: `${pct}%` }} />
    </div>
  );
}

export function Toast({ message, onDone, ms = 2600 }) {
  useEffect(() => {
    if (!message) return undefined;
    const id = setTimeout(onDone, ms);
    return () => clearTimeout(id);
  }, [message, onDone, ms]);
  if (!message) return null;
  return (
    <div className="toast" role="status">
      {message}
    </div>
  );
}

export function useToast() {
  const [message, setMessage] = useState("");
  const node = <Toast message={message} onDone={() => setMessage("")} />;
  return [node, setMessage];
}

/** A whole number that counts up once when it first appears (see useCountUp); `id` remembers it for the visit. */
export function CountUp({ value, id, format = String }) {
  const shown = useCountUp(value, id);
  const target = Math.round(Number(value)) || 0;
  if (shown === target) return format(target);
  // While it counts, screen readers get the real number only.
  return (
    <>
      <span aria-hidden="true">{format(shown)}</span>
      <span className="sr-only">{format(target)}</span>
    </>
  );
}

/** Where the active tab's underline goes: its left edge and width, in the tab list. */
function useTabIndicator(listRef, key) {
  const [bar, setBar] = useState(null);
  useLayoutEffect(() => {
    const list = listRef.current;
    if (!list) return undefined;
    const place = () => {
      const active = list.querySelector('[role="tab"][aria-selected="true"]');
      if (!active || !active.offsetWidth) {
        setBar(null);
        return;
      }
      // Placed at once the first time; slides after that.
      setBar((old) => ({ left: active.offsetLeft, width: active.offsetWidth, moving: Boolean(old) }));
    };
    place();
    if (typeof ResizeObserver !== "function") return undefined;
    const observer = new ResizeObserver(place); // a wider screen or another language moves the tabs
    observer.observe(list);
    return () => observer.disconnect();
  }, [listRef, key]);
  return bar;
}

export function Tabs({ tabs, value, onChange }) {
  const listRef = useRef(null);
  const bar = useTabIndicator(listRef, `${value}|${tabs.map((tab) => `${tab.value}:${tab.label}`).join("|")}`);
  return (
    <div className={`tabs ${bar ? "has-indicator" : ""}`} role="tablist" ref={listRef}>
      {tabs.map((tab) => (
        <button
          key={tab.value}
          role="tab"
          aria-selected={value === tab.value}
          className={`tab ${value === tab.value ? "active" : ""}`}
          onClick={() => onChange(tab.value)}
        >
          {tab.label}
        </button>
      ))}
      {bar && (
        <span
          className={`tab-indicator ${bar.moving ? "is-moving" : ""}`}
          aria-hidden="true"
          style={{ transform: `translateX(${bar.left}px) scaleX(${bar.width / 100})` }}
        />
      )}
    </div>
  );
}

export const GRADES = ["S1", "S2", "S3", "S4", "S5", "S6"];

export function GradeChips({ value, onChange, grades = GRADES, allowAll = false }) {
  const { t } = useI18n();
  return (
    <div className="chips" role="group" aria-label={t("learn.chooseGrade")}>
      {allowAll && (
        <button className={`chip ${!value ? "active" : ""}`} onClick={() => onChange("")}>
          {t("practice.all")}
        </button>
      )}
      {grades.map((g) => (
        <button key={g} className={`chip ${value === g ? "active" : ""}`} aria-pressed={value === g} onClick={() => onChange(g)}>
          {g}
        </button>
      ))}
    </div>
  );
}

export function Logo({ size = 34 }) {
  return (
    <svg className="brand-mark" width={size} height={size} viewBox="0 0 64 64" aria-hidden>
      <defs>
        <clipPath id="iga-logo-clip">
          <rect width="64" height="64" rx="16" />
        </clipPath>
      </defs>
      <g clipPath="url(#iga-logo-clip)">
        <rect width="64" height="64" fill="#00A1DE" />
        <rect y="50" width="64" height="7" fill="#FAD201" />
        <rect y="57" width="64" height="7" fill="#20603D" />
      </g>
      <circle cx="46" cy="18" r="8" fill="#FAD201" />
      <circle cx="22" cy="16" r="5.5" fill="#fff" />
      <rect x="17" y="25" width="10" height="21" rx="3" fill="#fff" />
    </svg>
  );
}

export function scoreClass(pct) {
  if (pct === null || pct === undefined) return "pill";
  if (pct >= 75) return "pill pill-success";
  if (pct >= 50) return "pill pill-warn";
  return "pill pill-danger";
}
