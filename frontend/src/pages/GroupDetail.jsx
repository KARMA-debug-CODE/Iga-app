import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api } from "../api";
import { useAuth } from "../auth";
import Markdown from "../components/Markdown";
import { Empty, ErrorMessage, Loader, Tabs, useToast } from "../components/ui";
import { formatDate, useApi } from "../hooks";
import { useI18n } from "../i18n";

const POLL_MS = 4000;

function mergeMessages(current, incoming) {
  const byId = new Map(current.map((m) => [m.id, m]));
  for (const m of incoming) byId.set(m.id, m);
  return [...byId.values()].sort((a, b) => a.id - b.id);
}

function Chat({ group }) {
  const { user } = useAuth();
  const { t, lang } = useI18n();
  const [messages, setMessages] = useState([]);
  const [body, setBody] = useState("");
  const [error, setError] = useState(null);
  const [toast, showToast] = useToast();
  const log = useRef(null);
  const lastId = useRef(0);
  const inFlight = useRef(false);

  const poll = useCallback(async () => {
    // One request at a time, and merge by id, so overlapping polls never duplicate messages.
    if (inFlight.current) return;
    inFlight.current = true;
    try {
      const data = await api(`/groups/${group.id}/messages/`, { params: lastId.current ? { after: lastId.current } : {} });
      const fresh = data.messages || [];
      if (fresh.length) lastId.current = Math.max(lastId.current, ...fresh.map((m) => m.id));
      const hidden = new Set(data.hidden_ids || []);
      setMessages((current) =>
        mergeMessages(current, fresh).map((m) => (hidden.has(m.id) && !m.is_hidden ? { ...m, is_hidden: true, body: t("groups.removed") } : m)),
      );
    } catch {
      /* keep polling quietly; the offline banner explains network problems */
    } finally {
      inFlight.current = false;
    }
  }, [group.id, t]);

  useEffect(() => {
    poll();
    const id = setInterval(() => document.visibilityState === "visible" && poll(), POLL_MS);
    return () => clearInterval(id);
  }, [poll]);

  useEffect(() => {
    if (log.current) log.current.scrollTop = log.current.scrollHeight;
  }, [messages.length]);

  async function send(e) {
    e.preventDefault();
    if (!body.trim()) return;
    setError(null);
    try {
      const sent = await api(`/groups/${group.id}/messages/`, { method: "POST", body: { body } });
      setBody("");
      // Don't move the poll cursor: others may have posted just before this message.
      setMessages((current) => mergeMessages(current, [sent]));
    } catch (err) {
      setError(err);
    }
  }

  async function report(message) {
    const reason = window.prompt(t("groups.reportReason"));
    if (reason === null) return;
    try {
      await api(`/messages/${message.id}/report/`, { method: "POST", body: { reason } });
      showToast(t("groups.reported"));
    } catch (err) {
      setError(err);
    }
  }

  async function hide(message) {
    try {
      const updated = await api(`/messages/${message.id}/hide/`, { method: "POST" });
      setMessages((list) => list.map((m) => (m.id === message.id ? updated : m)));
    } catch (err) {
      setError(err);
    }
  }

  return (
    <div className="card chat">
      {toast}
      <div className="chat-log" ref={log} aria-live="polite">
        {messages.length === 0 && <Empty icon="💬">{t("groups.typeMessage")}</Empty>}
        {messages.map((m) => {
          const mine = m.author?.id === user.id;
          return (
            <div key={m.id} className={`bubble ${mine ? "mine" : ""} ${m.is_hidden ? "hidden" : ""}`}>
              <div className="meta">
                <strong>{mine ? t("board.you") : m.author?.name || "—"}</strong>
                {m.author?.role === "teacher" && <span className="pill pill-blue">🧑🏽‍🏫</span>}
                <span>{formatDate(m.created_at, lang)}</span>
                {!mine && !m.is_hidden && <button onClick={() => report(m)}>{t("groups.report")}</button>}
                {group.can_moderate && !m.is_hidden && <button onClick={() => hide(m)}>{t("groups.hide")}</button>}
              </div>
              <div>{m.body}</div>
            </div>
          );
        })}
      </div>
      <ErrorMessage error={error} />
      <form className="chat-form" onSubmit={send}>
        <label className="sr-only" htmlFor="chat-input">
          {t("groups.typeMessage")}
        </label>
        <input id="chat-input" value={body} onChange={(e) => setBody(e.target.value)} placeholder={t("groups.typeMessage")} maxLength={2000} autoComplete="off" />
        <button className="btn">{t("groups.send")}</button>
      </form>
    </div>
  );
}

function Notes({ group }) {
  const { t, lang } = useI18n();
  const state = useApi(`/groups/${group.id}/notes/`);
  const [form, setForm] = useState({ title: "", body: "" });
  const [error, setError] = useState(null);
  async function submit(e) {
    e.preventDefault();
    setError(null);
    try {
      await api(`/groups/${group.id}/notes/`, { method: "POST", body: form });
      setForm({ title: "", body: "" });
      state.reload();
    } catch (err) {
      setError(err);
    }
  }
  return (
    <div className="grid-2">
      <Loader state={state}>
        {(notes) =>
          notes.length ? (
            <div className="stack">
              {notes.map((n) => (
                <div className="card" key={n.id}>
                  <strong>{n.title}</strong>
                  <div className="small muted">
                    {n.author_name} · {formatDate(n.created_at, lang)}
                  </div>
                  <Markdown interactive={false}>{n.body}</Markdown>
                </div>
              ))}
            </div>
          ) : (
            <Empty icon="🗒️">—</Empty>
          )
        }
      </Loader>
      <form className="card form" onSubmit={submit}>
        <h3>{t("groups.newNote")}</h3>
        <label>
          {t("groups.noteTitle")}
          <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
        </label>
        <label>
          {t("groups.noteBody")}
          <textarea rows={6} value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} required />
        </label>
        <ErrorMessage error={error} />
        <button className="btn">{t("common.save")}</button>
      </form>
    </div>
  );
}

export default function GroupDetail() {
  const { id } = useParams();
  const { t } = useI18n();
  const navigate = useNavigate();
  const [tab, setTab] = useState("chat");
  const state = useApi(`/groups/${id}/`);

  return (
    <Loader state={state}>
      {(group) => (
        <>
          <div className="breadcrumb">
            <Link to="/groups">{t("groups.title")}</Link> <span>›</span> <span>{group.name}</span>
          </div>
          <div className="page-header spread">
            <div>
              <h1 style={{ margin: 0 }}>
                {group.subject_icon} {group.name}
              </h1>
              <p>{group.description}</p>
            </div>
            {group.join_code && (
              <div className="small">
                {t("groups.code")}: <span className="pill pill-blue">{group.join_code}</span>
              </div>
            )}
          </div>
          {!group.is_member ? (
            <button
              className="btn"
              onClick={async () => {
                await api(`/groups/${id}/join/`, { method: "POST" });
                state.reload();
              }}
            >
              {t("groups.join")}
            </button>
          ) : (
            <>
              <Tabs
                value={tab}
                onChange={setTab}
                tabs={[
                  { value: "chat", label: `💬 ${t("groups.chat")}` },
                  { value: "notes", label: `🗒️ ${t("groups.notes")}` },
                  { value: "members", label: `👥 ${t("groups.members")} (${group.members?.length || 0})` },
                ]}
              />
              {tab === "chat" && <Chat group={group} />}
              {tab === "notes" && <Notes group={group} />}
              {tab === "members" && (
                <div className="card">
                  <ul className="list">
                    {(group.members || []).map((m) => (
                      <li key={m.id} className="spread">
                        <span>
                          <strong>{m.display_name}</strong> {m.group_role === "owner" && <span className="pill pill-warn">★</span>}
                        </span>
                        <span className="small muted">{m.role === "teacher" ? `🧑🏽‍🏫 ${t("auth.teacher")}` : m.grade}</span>
                      </li>
                    ))}
                  </ul>
                  <button
                    className="btn btn-danger btn-sm"
                    style={{ marginTop: 12 }}
                    onClick={async () => {
                      await api(`/groups/${id}/leave/`, { method: "POST" });
                      navigate("/groups");
                    }}
                  >
                    {t("groups.leave")}
                  </button>
                </div>
              )}
              <p className="small muted" style={{ marginTop: 12 }}>
                ⓘ {t("groups.rules")}
              </p>
            </>
          )}
        </>
      )}
    </Loader>
  );
}
