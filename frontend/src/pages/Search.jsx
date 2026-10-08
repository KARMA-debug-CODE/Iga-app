import { Link, useSearchParams } from "react-router-dom";

import { Icon, SubjectIcon } from "../components/Icon";
import { LockBadge } from "../components/Locked";
import { Empty, Loader } from "../components/ui";
import { useApi } from "../hooks";
import { useI18n } from "../i18n";

export default function Search() {
  const [params] = useSearchParams();
  const q = params.get("q") || "";
  const { t, lang } = useI18n();
  const state = useApi("/search/", { params: { q, lang } });
  return (
    <>
      <div className="page-header">
        <h1>
          {t("search.title")}: “{q}”
        </h1>
      </div>
      <Loader state={state}>
        {(r) => {
          const total = r.lessons.length + r.simulations.length + r.quizzes.length + r.subjects.length;
          if (!total) return <Empty icon="search">{t("search.none", { q })}</Empty>;
          return (
            <div className="stack">
              {r.subjects.length > 0 && (
                <div className="card">
                  <h2>{t("learn.subjects")}</h2>
                  <ul className="list">
                    {r.subjects.map((s) => (
                      <li key={s.code}>
                        <Link to={`/learn/${s.code}`} className="with-icon">
                          <SubjectIcon name={s.icon} size={18} /> {s.name}
                        </Link>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {r.lessons.length > 0 && (
                <div className="card">
                  <h2 className="title-with-icon">
                    <Icon name="learn" /> {t("nav.learn")}
                  </h2>
                  <ul className="list">
                    {r.lessons.map((l) => (
                      <li key={l.slug}>
                        <Link to={`/lessons/${l.slug}`} className="with-icon">
                          <SubjectIcon name={l.icon} size={18} /> {l.title}
                        </Link>{" "}
                        <span className="small muted">
                          · {l.subject} {l.grade}
                        </span>{" "}
                        {l.locked && <LockBadge />}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {r.simulations.length > 0 && (
                <div className="card">
                  <h2 className="title-with-icon">
                    <Icon name="labs" /> {t("nav.labs")}
                  </h2>
                  <ul className="list">
                    {r.simulations.map((s) => (
                      <li key={s.slug}>
                        <Link to={`/labs/${s.slug}`}>{s.title}</Link>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {r.quizzes.length > 0 && (
                <div className="card">
                  <h2 className="title-with-icon">
                    <Icon name="practice" /> {t("nav.practice")}
                  </h2>
                  <ul className="list">
                    {r.quizzes.map((q2) => (
                      <li key={q2.id}>
                        {/* A locked quiz can't be started: show it with its lock instead of a start link. */}
                        <Link to={q2.locked ? "/practice" : `/practice?start=${q2.id}`}>{q2.title}</Link>{" "}
                        <span className="small muted">· {q2.subject}</span> {q2.locked && <LockBadge />}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          );
        }}
      </Loader>
    </>
  );
}
