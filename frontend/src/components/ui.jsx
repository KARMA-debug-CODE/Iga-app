import { useEffect, useState } from "react";

import { useI18n } from "../i18n";
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

/** Renders loading / error states, then `children(data)`. */
export function Loader({ state, children }) {
  if (state.loading && !state.data) return <Spinner />;
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

export function Tabs({ tabs, value, onChange }) {
  return (
    <div className="tabs" role="tablist">
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
