import { useState } from "react";

import { api } from "../api";
import { Icon } from "../components/Icon";
import { Empty, ErrorMessage, Loader, Progress } from "../components/ui";
import { formatDay, useApi } from "../hooks";
import { useI18n } from "../i18n";

const MAX_GOAL = 50;
const MAX_EXAMS = 10;

function daysUntil(dateStr) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const target = new Date(`${dateStr}T00:00:00`);
  return Math.round((target - today) / 86400000);
}

function countdownLabel(days, t) {
  if (days <= 0) return t("planner.examToday");
  return t("planner.daysLeft", { n: days });
}

function WeeklyGoal({ data, reload }) {
  const { t } = useI18n();
  const [goal, setGoal] = useState(data.weekly_goal_lessons);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [saved, setSaved] = useState(false);
  const done = data.summary.lessons_this_week;

  async function save(e) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      await api("/planner/", { method: "PUT", body: { weekly_goal_lessons: Number(goal) } });
      setSaved(true);
      reload();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card form" onSubmit={save}>
      <h2 className="title-with-icon">
        <Icon name="target" /> {t("planner.weeklyGoal")}
      </h2>
      <p className="muted small">{t("planner.weeklyGoalHelp")}</p>
      <div className="row" style={{ alignItems: "flex-end" }}>
        <label style={{ maxWidth: 160 }}>
          {t("planner.lessonsPerWeek")}
          <input
            type="number"
            min={1}
            max={MAX_GOAL}
            value={goal}
            onChange={(e) => {
              setGoal(e.target.value);
              setSaved(false);
            }}
            inputMode="numeric"
          />
        </label>
        <button className="btn" disabled={busy || !goal || Number(goal) === data.weekly_goal_lessons}>
          <Icon name="save" size={16} /> {t("common.save")}
        </button>
      </div>
      <div style={{ marginTop: 6 }}>
        <div className="spread small">
          <span>{t("planner.weekProgress", { done, goal: data.weekly_goal_lessons })}</span>
          {done >= data.weekly_goal_lessons && (
            <span className="pill pill-success">
              <Icon name="check" size={13} /> {t("planner.goalReached")}
            </span>
          )}
        </div>
        <Progress value={done} max={data.weekly_goal_lessons} label={t("planner.weeklyGoal")} />
      </div>
      <ErrorMessage error={error} />
      {saved && (
        <div className="alert alert-success" role="status">
          {t("common.saved")}
        </div>
      )}
    </form>
  );
}

function Exams({ data, reload }) {
  const { t, lang } = useI18n();
  const exams = [...data.exams].sort((a, b) => a.date.localeCompare(b.date));
  const [title, setTitle] = useState("");
  const [date, setDate] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const today = new Date().toISOString().slice(0, 10);

  async function add(e) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/planner/exams/", { method: "POST", body: { title: title.trim(), date } });
      setTitle("");
      setDate("");
      reload();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  async function remove(id) {
    setError(null);
    try {
      await api(`/planner/exams/${id}/`, { method: "DELETE" });
      reload();
    } catch (err) {
      setError(err);
    }
  }

  return (
    <div className="card">
      <h2 className="title-with-icon">
        <Icon name="calendar" /> {t("planner.exams")}
      </h2>
      <p className="muted small">{t("planner.examsHelp")}</p>
      {exams.length ? (
        <ul className="list" style={{ marginTop: 10 }}>
          {exams.map((exam) => {
            const days = daysUntil(exam.date);
            return (
              <li key={exam.id} className="spread">
                <div style={{ minWidth: 0 }}>
                  <strong className="truncate" style={{ display: "block" }}>
                    {exam.title}
                  </strong>
                  <span className="small muted">{formatDay(exam.date, lang)}</span>
                </div>
                <div className="row">
                  <span className={`pill ${days <= 7 ? "pill-warn" : ""}`}>{countdownLabel(days, t)}</span>
                  <button type="button" className="btn btn-sm btn-ghost" onClick={() => remove(exam.id)} aria-label={t("planner.removeExam")}>
                    <Icon name="trash" size={16} />
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      ) : (
        <Empty icon="calendar">{t("planner.noExams")}</Empty>
      )}
      {exams.length < MAX_EXAMS ? (
        <form className="form" style={{ marginTop: 14 }} onSubmit={add}>
          <div className="form-row">
            <label>
              {t("planner.examTitle")}
              <input value={title} onChange={(e) => setTitle(e.target.value)} maxLength={120} required placeholder={t("planner.examTitlePlaceholder")} />
            </label>
            <label>
              {t("planner.examDate")}
              <input type="date" value={date} min={today} onChange={(e) => setDate(e.target.value)} required />
            </label>
          </div>
          <ErrorMessage error={error} />
          <div>
            <button className="btn btn-secondary" disabled={busy || !title.trim() || !date}>
              <Icon name="plus" size={16} /> {t("planner.addExam")}
            </button>
          </div>
        </form>
      ) : (
        <>
          <ErrorMessage error={error} />
          <p className="small muted" style={{ marginTop: 10 }}>
            {t("planner.maxExams", { n: MAX_EXAMS })}
          </p>
        </>
      )}
    </div>
  );
}

export default function Planner() {
  const { t } = useI18n();
  const state = useApi("/planner/");
  return (
    <>
      <div className="page-header">
        <h1 className="title-with-icon">
          <Icon name="target" size={28} /> {t("planner.pageTitle")}
        </h1>
        <p>{t("planner.pageIntro")}</p>
      </div>
      <Loader state={state}>
        {(data) => (
          <div className="grid-2">
            <WeeklyGoal data={data} reload={state.reload} />
            <Exams data={data} reload={state.reload} />
          </div>
        )}
      </Loader>
    </>
  );
}
