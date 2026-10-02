import { useState } from "react";

import { results } from "../api";
import { Empty, Loader, Tabs } from "../components/ui";
import { useApi } from "../hooks";
import { useI18n } from "../i18n";

const MEDALS = ["🥇", "🥈", "🥉"];

export default function Leaderboard() {
  const { t } = useI18n();
  const [scope, setScope] = useState("grade");
  const [period, setPeriod] = useState("week");
  const [classroom, setClassroom] = useState("");
  const classes = useApi("/classes/");
  const classList = results(classes.data);
  const state = useApi("/leaderboard/", { params: { scope, period, classroom: scope === "class" ? classroom || classList[0]?.id : undefined }, skip: scope === "class" && !classList.length });

  return (
    <div style={{ maxWidth: 720 }}>
      <div className="page-header">
        <h1>🏆 {t("board.title")}</h1>
      </div>
      <Tabs
        value={period}
        onChange={setPeriod}
        tabs={[
          { value: "week", label: t("board.week") },
          { value: "all", label: t("board.allTime") },
        ]}
      />
      <div className="chips" style={{ marginBottom: 14 }}>
        {[
          ["grade", t("board.grade")],
          ["school", t("board.school")],
          ...(classList.length ? [["class", t("board.class")]] : []),
        ].map(([value, label]) => (
          <button key={value} className={`chip ${scope === value ? "active" : ""}`} onClick={() => setScope(value)}>
            {label}
          </button>
        ))}
        {scope === "class" && (
          <select value={classroom || classList[0]?.id || ""} onChange={(e) => setClassroom(e.target.value)} style={{ width: "auto" }}>
            {classList.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        )}
      </div>
      <Loader state={state}>
        {(board) =>
          board.entries.length === 0 ? (
            <Empty icon="🏁">{t("board.empty")}</Empty>
          ) : (
            <div className="card">
              <ol className="list">
                {board.entries.map((e) => (
                  <li key={e.user_id} className={`row ${e.is_me ? "me-row" : ""}`} style={{ flexWrap: "nowrap" }}>
                    <span className="rank">{MEDALS[e.rank - 1] || e.rank}</span>
                    <span style={{ flex: 1, minWidth: 0 }} className="truncate">
                      <strong>{e.name}</strong> {e.is_me && <span className="pill pill-warn">{t("board.you")}</span>}
                      <span className="small muted"> · {e.grade}</span>
                    </span>
                    <strong>{t("board.points", { n: e.points })}</strong>
                  </li>
                ))}
              </ol>
              {board.me && board.me.rank > 50 && (
                <p className="me-row" style={{ marginTop: 10, padding: 8 }}>
                  #{board.me.rank} · {board.me.name} · {t("board.points", { n: board.me.points })}
                </p>
              )}
            </div>
          )
        }
      </Loader>
    </div>
  );
}
