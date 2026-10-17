import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "../api";
import { useApi, useOnline } from "../hooks";
import { useI18n } from "../i18n";
import { pendingNote, saveNote, syncNotes } from "../notes-offline";
import { ErrorMessage } from "./ui";
import { Icon } from "./Icon";

const NOTE_MAX = 5000;
const SAVE_DELAY = 800;

function BookmarkToggle({ slug, state, onChange }) {
  const { t } = useI18n();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function toggle() {
    setBusy(true);
    setError(null);
    try {
      if (state.bookmarked) {
        await api(`/bookmarks/${state.bookmark_id}/`, { method: "DELETE" });
        onChange({ bookmarked: false, bookmark_id: null });
      } else {
        const bookmark = await api("/bookmarks/", { method: "POST", body: { lesson: slug } });
        onChange({ bookmarked: true, bookmark_id: bookmark.id });
      }
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <button
        type="button"
        className={`btn btn-sm ${state.bookmarked ? "" : "btn-secondary"}`}
        aria-pressed={state.bookmarked}
        disabled={busy}
        onClick={toggle}
      >
        <Icon name={state.bookmarked ? "bookmarkOn" : "bookmarkOff"} size={16} />
        {state.bookmarked ? t("notes.bookmarked") : t("notes.bookmark")}
      </button>
      <ErrorMessage error={error} />
    </>
  );
}

function statusText(status, t) {
  if (status === "saving") return { icon: "hourglass", text: t("notes.saving") };
  if (status === "saved") return { icon: "check", text: t("notes.saved") };
  if (status === "queued") return { icon: "offline", text: t("notes.queued") };
  return null;
}

function NoteEditor({ slug, initialBody }) {
  const { t } = useI18n();
  const online = useOnline();
  const [body, setBody] = useState(() => pendingNote(slug) ?? initialBody ?? "");
  const [status, setStatus] = useState(() => (pendingNote(slug) != null ? "queued" : "idle"));
  const [error, setError] = useState(null);
  const timer = useRef(null);
  const latest = useRef(body);

  const flush = useCallback(async () => {
    clearTimeout(timer.current);
    setStatus("saving");
    setError(null);
    try {
      const result = await saveNote(slug, latest.current);
      setStatus(result.queued ? "queued" : "saved");
    } catch (e) {
      setError(e);
      setStatus("idle");
    }
  }, [slug]);

  function change(value) {
    setBody(value);
    latest.current = value;
    setStatus("editing");
    clearTimeout(timer.current);
    timer.current = setTimeout(flush, SAVE_DELAY);
  }

  // When the connection comes back, send anything this device is still holding.
  useEffect(() => {
    if (online && pendingNote(slug) != null) {
      syncNotes().then((sent) => {
        if (sent.includes(slug)) setStatus("saved");
      });
    }
  }, [online, slug]);

  useEffect(() => () => clearTimeout(timer.current), []);

  const info = statusText(status, t);
  return (
    <div className="note-editor">
      <label className="sr-only" htmlFor={`note-${slug}`}>
        {t("notes.editorLabel")}
      </label>
      <textarea
        id={`note-${slug}`}
        value={body}
        maxLength={NOTE_MAX}
        rows={5}
        placeholder={t("notes.placeholder")}
        onChange={(e) => change(e.target.value)}
        onBlur={() => status === "editing" && flush()}
      />
      <div className="spread small muted" style={{ marginTop: 6 }}>
        <span className="with-icon" aria-live="polite">
          {info && (
            <>
              <Icon name={info.icon} size={14} /> {info.text}
            </>
          )}
        </span>
        <span>{t("notes.counter", { n: body.length, max: NOTE_MAX })}</span>
      </div>
      <ErrorMessage error={error} />
    </div>
  );
}

export default function LessonNotes({ slug }) {
  const { t } = useI18n();
  const state = useApi(`/my-notes/${slug}/`, {}, [slug]);
  // Appear once the lesson's note state is known, so the section doesn't flash in empty.
  if (state.loading && !state.data) return null;
  const data = state.data; // null if the request failed (e.g. offline): still show the editor.

  return (
    <section className="section card lesson-notes" id="notes" aria-labelledby="notes-heading">
      <div className="spread" style={{ alignItems: "center", flexWrap: "wrap", gap: 8 }}>
        <h2 id="notes-heading" className="title-with-icon" style={{ margin: 0 }}>
          <Icon name="notebook" /> {t("notes.sectionTitle")}
        </h2>
        {data && <BookmarkToggle slug={slug} state={data} onChange={(patch) => state.setData((d) => ({ ...d, ...patch }))} />}
      </div>
      <p className="small muted with-icon" style={{ marginTop: 8 }}>
        <Icon name="lock" size={14} /> {t("notes.private")}
      </p>
      <NoteEditor slug={slug} initialBody={data?.note?.body || ""} />
    </section>
  );
}
