import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { api } from "../api";
import { Icon, SubjectIcon } from "../components/Icon";
import { Empty, ErrorMessage, Loader, SkeletonRows, Tabs } from "../components/ui";
import { formatDay, useApi } from "../hooks";
import { useI18n } from "../i18n";

function LessonMeta({ lesson }) {
  return (
    <span className="small muted">
      {lesson.subject} · {lesson.grade}
    </span>
  );
}

function NoteRow({ note, onRemove }) {
  const { t, lang } = useI18n();
  return (
    <li className="my-notes-row">
      <Link className="list-link" to={`/lessons/${note.lesson.slug}`}>
        <div className="icon-tile">
          <SubjectIcon name={note.lesson.icon} />
        </div>
        <div className="grow" style={{ minWidth: 0 }}>
          <strong className="truncate" style={{ display: "block" }}>
            {note.lesson.title}
          </strong>
          <LessonMeta lesson={note.lesson} />
          <p className="note-snippet">{note.body}</p>
          <span className="small muted">{t("notes.updated", { date: formatDay(note.updated_at, lang) })}</span>
        </div>
      </Link>
      <button type="button" className="btn btn-sm btn-ghost" onClick={() => onRemove(note)} aria-label={t("notes.deleteNote")}>
        <Icon name="trash" size={16} />
      </button>
    </li>
  );
}

function BookmarkRow({ bookmark, onRemove }) {
  const { t } = useI18n();
  return (
    <li className="my-notes-row">
      <Link className="list-link" to={`/lessons/${bookmark.lesson.slug}`}>
        <div className="icon-tile">
          <SubjectIcon name={bookmark.lesson.icon} />
        </div>
        <div className="grow" style={{ minWidth: 0 }}>
          <strong className="truncate" style={{ display: "block" }}>
            {bookmark.lesson.title}
          </strong>
          <LessonMeta lesson={bookmark.lesson} />
        </div>
      </Link>
      <button type="button" className="btn btn-sm btn-ghost" onClick={() => onRemove(bookmark)} aria-label={t("notes.removeBookmark")}>
        <Icon name="trash" size={16} />
      </button>
    </li>
  );
}

function NotesTab() {
  const { t } = useI18n();
  const [text, setText] = useState("");
  const [query, setQuery] = useState("");
  const [error, setError] = useState(null);
  const state = useApi("/notes/", { params: { q: query || undefined } }, [query]);

  // Search as the student types, but wait until they pause so one letter isn't one request.
  useEffect(() => {
    const id = setTimeout(() => setQuery(text.trim()), 300);
    return () => clearTimeout(id);
  }, [text]);

  async function remove(note) {
    setError(null);
    try {
      await api(`/notes/${note.id}/`, { method: "DELETE" });
      state.setData((list) => list.filter((n) => n.id !== note.id));
    } catch (e) {
      setError(e);
    }
  }

  return (
    <>
      <form className="search-inline" role="search" onSubmit={(e) => e.preventDefault()}>
        <label className="sr-only" htmlFor="notes-search">
          {t("notes.search")}
        </label>
        <Icon name="search" size={16} />
        <input id="notes-search" type="search" value={text} placeholder={t("notes.search")} onChange={(e) => setText(e.target.value)} />
      </form>
      <ErrorMessage error={error} />
      <Loader state={state} skeleton={<SkeletonRows count={4} />}>
        {(list) =>
          list.length ? (
            <ul className="list stagger" style={{ marginTop: 14 }}>
              {list.map((note) => (
                <NoteRow key={note.id} note={note} onRemove={remove} />
              ))}
            </ul>
          ) : query ? (
            <Empty icon="search">{t("notes.noSearch", { q: query })}</Empty>
          ) : (
            <Empty icon="notebook">{t("notes.noNotes")}</Empty>
          )
        }
      </Loader>
    </>
  );
}

function BookmarksTab() {
  const { t } = useI18n();
  const [error, setError] = useState(null);
  const state = useApi("/bookmarks/");

  async function remove(bookmark) {
    setError(null);
    try {
      await api(`/bookmarks/${bookmark.id}/`, { method: "DELETE" });
      state.setData((list) => list.filter((b) => b.id !== bookmark.id));
    } catch (e) {
      setError(e);
    }
  }

  return (
    <>
      <ErrorMessage error={error} />
      <Loader state={state} skeleton={<SkeletonRows count={4} />}>
        {(list) =>
          list.length ? (
            <ul className="list stagger" style={{ marginTop: 14 }}>
              {list.map((bookmark) => (
                <BookmarkRow key={bookmark.id} bookmark={bookmark} onRemove={remove} />
              ))}
            </ul>
          ) : (
            <Empty icon="bookmarkOff">{t("notes.noBookmarks")}</Empty>
          )
        }
      </Loader>
    </>
  );
}

export default function MyNotes() {
  const { t } = useI18n();
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") === "bookmarks" ? "bookmarks" : "notes";

  return (
    <>
      <div className="page-header">
        <h1 className="title-with-icon">
          <Icon name="notebook" size={28} /> {t("nav.notes")}
        </h1>
      </div>
      <Tabs
        value={tab}
        onChange={(value) => setParams(value === "notes" ? {} : { tab: value })}
        tabs={[
          { value: "notes", label: t("notes.tabNotes") },
          { value: "bookmarks", label: t("notes.tabBookmarks") },
        ]}
      />
      <div style={{ marginTop: 14 }}>{tab === "bookmarks" ? <BookmarksTab /> : <NotesTab />}</div>
    </>
  );
}
