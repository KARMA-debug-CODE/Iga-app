import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { api, results } from "../api";
import { useAuth } from "../auth";
import { Icon, SubjectIcon } from "../components/Icon";
import { Empty, ErrorMessage, Loader, Tabs } from "../components/ui";
import { useApi } from "../hooks";
import { useI18n } from "../i18n";

function GroupCard({ group, onJoin }) {
  const { t } = useI18n();
  return (
    <div className="card">
      <div className="row" style={{ flexWrap: "nowrap" }}>
        <div className="icon-tile">
          <SubjectIcon name={group.subject_icon || "groups"} />
        </div>
        <div style={{ minWidth: 0, flex: 1 }}>
          <Link to={`/groups/${group.id}`} style={{ color: "inherit", textDecoration: "none" }}>
            <strong>{group.name}</strong>
          </Link>
          <div className="small muted">
            {[group.grade, group.subject_name, t("groups.membersCount", { n: group.member_count })].filter(Boolean).join(" · ")}
          </div>
        </div>
        {group.is_private && (
          <span className="pill" title={t("groups.private")}>
            <Icon name="lock" size={14} label={t("groups.private")} />
          </span>
        )}
      </div>
      {group.description && <p className="small" style={{ margin: "10px 0 0" }}>{group.description}</p>}
      <div style={{ marginTop: 12 }}>
        {group.is_member ? (
          <Link className="btn btn-sm btn-secondary" to={`/groups/${group.id}`}>
            {t("groups.chat")} →
          </Link>
        ) : (
          <button className="btn btn-sm" onClick={() => onJoin(group)}>
            {t("groups.join")}
          </button>
        )}
      </div>
    </div>
  );
}

export default function Groups() {
  const { user } = useAuth();
  const { t } = useI18n();
  const navigate = useNavigate();
  const [tab, setTab] = useState("mine");
  const state = useApi("/groups/", { params: tab === "mine" ? { mine: 1 } : { grade: user.grade } });
  const [form, setForm] = useState({ name: "", description: "", is_private: false });
  const [code, setCode] = useState("");
  const [error, setError] = useState(null);

  async function join(group) {
    setError(null);
    try {
      await api(`/groups/${group.id}/join/`, { method: "POST" });
      navigate(`/groups/${group.id}`);
    } catch (e) {
      setError(e);
    }
  }

  async function joinByCode(e) {
    e.preventDefault();
    setError(null);
    try {
      const group = await api("/groups/join-by-code/", { method: "POST", body: { code } });
      navigate(`/groups/${group.id}`);
    } catch (err) {
      setError(err);
    }
  }

  async function create(e) {
    e.preventDefault();
    setError(null);
    try {
      const group = await api("/groups/", { method: "POST", body: { ...form, grade: user.grade || "" } });
      navigate(`/groups/${group.id}`);
    } catch (err) {
      setError(err);
    }
  }

  return (
    <>
      <div className="page-header">
        <h1 className="title-with-icon">
          <Icon name="groups" size={28} /> {t("groups.title")}
        </h1>
        <p>{t("groups.rules")}</p>
      </div>
      <ErrorMessage error={error} />
      <div className="grid-2">
        <div>
          <Tabs
            value={tab}
            onChange={setTab}
            tabs={[
              { value: "mine", label: t("groups.mine") },
              { value: "discover", label: t("groups.discover") },
            ]}
          />
          <Loader state={state}>
            {(data) => {
              const list = results(data);
              if (!list.length) return <Empty icon="groups">{t("groups.empty")}</Empty>;
              return (
                <div className="stack">
                  {list.map((g) => (
                    <GroupCard key={g.id} group={g} onJoin={join} />
                  ))}
                </div>
              );
            }}
          </Loader>
        </div>
        <div className="stack">
          <form className="card form" onSubmit={create}>
            <h2>{t("groups.create")}</h2>
            <label>
              {t("groups.name")}
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required maxLength={120} />
            </label>
            <label>
              {t("groups.description")}
              <textarea rows={2} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </label>
            <label className="check">
              <input type="checkbox" checked={form.is_private} onChange={(e) => setForm({ ...form, is_private: e.target.checked })} />
              {t("groups.private")}
            </label>
            <button className="btn">{t("common.create")}</button>
          </form>
          <form className="card form" onSubmit={joinByCode}>
            <h2>{t("groups.joinByCode")}</h2>
            <input value={code} onChange={(e) => setCode(e.target.value.toUpperCase())} placeholder="ABC234" required style={{ fontFamily: "var(--mono)", letterSpacing: "0.2em" }} />
            <button className="btn btn-secondary">{t("groups.join")}</button>
          </form>
        </div>
      </div>
    </>
  );
}
