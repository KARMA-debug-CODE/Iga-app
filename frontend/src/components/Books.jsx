// Books for a lesson or a unit: the official REB textbook first, then free open textbooks.
// They are links to the publishers' own sites, so they need internet (they are not saved offline).
import { useI18n } from "../i18n";

// Licences that books.json repeats, shown in the reader's language; any other licence is shown as written.
const LICENCE_KEYS = {
  "© REB, free to read": "books.licence.reb",
  "Public domain": "books.licence.publicDomain",
  "CC BY or CC BY-NC (varies by story)": "books.licence.storybook",
};

function icon(book) {
  if (book.kind === "teacher_guide") return "🧑🏽‍🏫";
  if (book.kind === "video") return "🎬";
  if (book.kind === "link") return "🔗";
  if (book.kind === "textbook") return book.is_official ? "📕" : "📗";
  return "📄";
}

/** The official textbooks among `books`, for linking a unit that has no Iga lesson yet. */
export function officialTextbooks(books) {
  return (books || []).filter((b) => b.is_official && (b.kind === "textbook" || b.kind === "teacher_guide"));
}

/** The unit's title in the book's own language, so students can find it in the book. */
function unitTitleFor(book, unit) {
  if (book.language === "fr") return unit.title_fr || unit.title;
  return unit.title_en || unit.title;
}

/** `unit` (optional) adds "look for this unit" to official textbooks. */
export default function BookList({ books, unit }) {
  const { t, lang } = useI18n();
  if (!books?.length) return null;
  return (
    <div className="card books">
      <ul className="list">
        {books.map((book) => {
          const description = (lang === "fr" && book.description_fr) || book.description;
          const meta = [
            book.publisher,
            t(`books.lang.${book.language}`),
            book.format && t(`books.format.${book.format}`),
            LICENCE_KEYS[book.licence] ? t(LICENCE_KEYS[book.licence]) : book.licence,
          ].filter(Boolean);
          return (
            <li key={book.id}>
              <a className="list-link" href={book.file_url || book.url} target="_blank" rel="noopener noreferrer">
                <div className="icon-tile" aria-hidden>
                  {icon(book)}
                </div>
                <div className="grow">
                  <strong>{book.title}</strong>
                  {book.is_official && <span className="pill pill-success book-pill">{t("learn.official")}</span>}
                  {description && <div className="small">{description}</div>}
                  {book.is_official && unit && book.kind === "textbook" && (
                    <div className="small book-hint">🔎 {t("books.lookFor", { unit: unitTitleFor(book, unit) })}</div>
                  )}
                  {meta.length > 0 && <div className="small muted">{meta.join(" · ")}</div>}
                </div>
                <span aria-hidden>↗</span>
              </a>
            </li>
          );
        })}
      </ul>
      <p className="small muted" style={{ margin: "8px 0 0" }}>
        {t("books.note")}
      </p>
    </div>
  );
}
