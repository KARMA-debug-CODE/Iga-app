import { useState } from "react";
import { Link } from "react-router-dom";

import { api, results } from "../api";
import { Empty, ErrorMessage, Loader, Tabs } from "../components/ui";
import { formatDate, useApi } from "../hooks";
import { useI18n } from "../i18n";

function Stats() {
  const state = useApi("/admin/stats/");
  return (
    <Loader state={state}>
      {(s) => (
        <div className="stack">
          {s.subscriptions && <SubscriptionStats subs={s.subscriptions} />}
          <div className="stats">
            {Object.entries(s.users_by_role).map(([role, n]) => (
              <div className="card stat" key={role}>
                <strong>{n}</strong>
                <span className="muted small">{role}s</span>
              </div>
            ))}
            <div className="card stat">
              <strong>{s.active_last_7_days}</strong>
              <span className="muted small">active this week</span>
            </div>
            <div className="card stat">
              <strong>{s.content.awaiting_review}</strong>
              <span className="muted small">awaiting review</span>
            </div>
          </div>
          <div className="grid-2">
            <div className="card">
              <h3>Content</h3>
              <ul className="list">
                {Object.entries(s.content).map(([k, v]) => (
                  <li key={k} className="spread">
                    <span>{k.replace(/_/g, " ")}</span>
                    <strong>{v}</strong>
                  </li>
                ))}
              </ul>
            </div>
            <div className="card">
              <h3>Activity (7 days)</h3>
              <ul className="list">
                {Object.entries(s.activity_last_7_days).map(([k, v]) => (
                  <li key={k} className="spread">
                    <span>{k.replace(/_/g, " ")}</span>
                    <strong>{v}</strong>
                  </li>
                ))}
              </ul>
              <h3 style={{ marginTop: 16 }}>Students by grade</h3>
              <div className="row">
                {Object.entries(s.students_by_grade).map(([g, n]) => (
                  <span key={g} className="pill">
                    {g || "—"}: {n}
                  </span>
                ))}
              </div>
            </div>
            <div className="card">
              <h3>Popular lessons</h3>
              <ol>
                {s.popular_lessons.map((l) => (
                  <li key={l.title}>
                    {l.title} <span className="muted small">({l.count})</span>
                  </li>
                ))}
              </ol>
            </div>
            <div className="card">
              <h3>Popular labs</h3>
              <ol>
                {s.popular_simulations.map((l) => (
                  <li key={l.title}>
                    {l.title} <span className="muted small">({l.count})</span>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        </div>
      )}
    </Loader>
  );
}

function Users() {
  const { t } = useI18n();
  const [pending, setPending] = useState(true);
  const [q, setQ] = useState("");
  const state = useApi("/admin/users/", { params: { pending_teachers: pending ? 1 : undefined, q } });
  async function update(user, patch) {
    await api(`/admin/users/${user.id}/`, { method: "PATCH", body: patch });
    state.reload();
  }
  return (
    <>
      <div className="row" style={{ marginBottom: 12 }}>
        <label className="check">
          <input type="checkbox" checked={pending} onChange={(e) => setPending(e.target.checked)} />
          {t("admin.pendingTeachers")}
        </label>
        <input type="search" placeholder="Search users" value={q} onChange={(e) => setQ(e.target.value)} style={{ maxWidth: 260 }} />
      </div>
      <Loader state={state}>
        {(data) => {
          const list = results(data);
          if (!list.length) return <Empty icon="✅">{t("admin.nothing")}</Empty>;
          return (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>User</th>
                    <th>Role</th>
                    <th>School</th>
                    <th>Joined</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {list.map((u) => (
                    <tr key={u.id}>
                      <td>
                        <strong>
                          {u.first_name} {u.last_name}
                        </strong>
                        <div className="small muted">
                          @{u.username} {u.email}
                        </div>
                      </td>
                      <td>
                        {u.role} {u.grade}
                        {u.role === "teacher" && !u.teacher_approved && <span className="pill pill-warn">pending</span>}
                        {!u.is_active && <span className="pill pill-danger">disabled</span>}
                      </td>
                      <td>{u.school}</td>
                      <td className="small">{formatDate(u.date_joined)}</td>
                      <td>
                        <div className="row">
                          {u.role === "teacher" && !u.teacher_approved && (
                            <button className="btn btn-sm btn-success" onClick={() => update(u, { teacher_approved: true })}>
                              {t("admin.approve")}
                            </button>
                          )}
                          <button className="btn btn-sm btn-secondary" onClick={() => update(u, { is_active: !u.is_active })}>
                            {u.is_active ? "Disable" : "Enable"}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        }}
      </Loader>
    </>
  );
}

function Review() {
  const { t } = useI18n();
  const state = useApi("/admin/review/");
  async function decide(item, approve) {
    await api("/admin/review/decide/", { method: "POST", body: { type: item.type, id: item.id, approve } });
    state.setData((list) => list.filter((x) => !(x.type === item.type && x.id === item.id)));
  }
  return (
    <Loader state={state}>
      {(items) =>
        items.length === 0 ? (
          <Empty icon="✅">{t("admin.nothing")}</Empty>
        ) : (
          <div className="stack">
            {items.map((item) => (
              <div className="card spread" key={`${item.type}-${item.id}`}>
                <div>
                  <span className="pill">{item.type}</span> <strong>{item.title}</strong>
                  <div className="small muted">
                    {item.subject} · {item.grade} · {item.author} · {formatDate(item.updated_at)}
                  </div>
                  {item.type === "lesson" && <Link to={`/lessons/${item.slug}`}>Preview →</Link>}
                  {item.url && (
                    <a href={item.url} target="_blank" rel="noopener noreferrer">
                      {item.url}
                    </a>
                  )}
                </div>
                <div className="row">
                  <button className="btn btn-sm btn-success" onClick={() => decide(item, true)}>
                    {t("admin.approve")}
                  </button>
                  <button className="btn btn-sm btn-danger" onClick={() => decide(item, false)}>
                    {t("admin.reject")}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )
      }
    </Loader>
  );
}

function Moderation() {
  const { t } = useI18n();
  const state = useApi("/admin/moderation/");
  async function resolve(report, hide) {
    await api(`/admin/moderation/${report.id}/resolve/`, { method: "POST", body: { hide } });
    state.setData((list) => list.filter((r) => r.message.id !== report.message.id));
  }
  return (
    <Loader state={state}>
      {(reports) =>
        reports.length === 0 ? (
          <Empty icon="🕊️">{t("admin.nothing")}</Empty>
        ) : (
          <div className="stack">
            {reports.map((r) => (
              <div className="card" key={r.id}>
                <div className="small muted">
                  {r.message.group} · reported by {r.reporter} · {formatDate(r.created_at)}
                </div>
                <blockquote className="alert" style={{ margin: "8px 0" }}>
                  <strong>{r.message.author}:</strong> {r.message.body}
                </blockquote>
                <div className="small">Reason: {r.reason}</div>
                <div className="row" style={{ marginTop: 10 }}>
                  <button className="btn btn-sm btn-danger" onClick={() => resolve(r, true)}>
                    {t("admin.hideMessage")}
                  </button>
                  <button className="btn btn-sm btn-secondary" onClick={() => resolve(r, false)}>
                    {t("admin.dismiss")}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )
      }
    </Loader>
  );
}

function Audit() {
  const state = useApi("/admin/audit/");
  return (
    <Loader state={state}>
      {(entries) => (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>When</th>
                <th>Who</th>
                <th>Action</th>
                <th>Target</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e) => (
                <tr key={e.id}>
                  <td className="small">{formatDate(e.created_at)}</td>
                  <td>{e.actor || "—"}</td>
                  <td>
                    <code>{e.action}</code>
                  </td>
                  <td className="small">{e.target}</td>
                  <td className="small">
                    <code>{JSON.stringify(e.details)}</code>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Loader>
  );
}

function SchoolDetail({ id, onChanged }) {
  const { t, lang } = useI18n();
  const state = useApi(`/admin/schools/${id}/`, {}, [id]);
  const members = useApi(`/admin/schools/${id}/members/`, {}, [id]);
  const [form, setForm] = useState({ months: 1, amount: "200", currency: "USD", note: "" });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  async function run(fn) {
    setBusy(true);
    setError(null);
    try {
      await fn();
      state.reload();
      members.reload();
      onChanged();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }
  const act = (action) => run(() => api(`/admin/schools/${id}/${action}/`, { method: "POST" }));
  const recordPayment = (e) => {
    e.preventDefault();
    run(async () => {
      await api(`/admin/schools/${id}/payments/`, { method: "POST", body: form });
      setForm((f) => ({ ...f, note: "" }));
    });
  };
  const pendingAdmins = (members.data || []).filter((m) => m.role === "school_admin" && m.school_status === "pending");

  return (
    <Loader state={state}>
      {(school) => (
        <div className="card stack" style={{ gap: 12 }}>
          <div className="spread">
            <div>
              <h3 style={{ margin: 0 }}>{school.name}</h3>
              <span className="small muted">
                {school.district} · {school.phone} {school.email && `· ${school.email}`}
              </span>
            </div>
            <span className="pill">{t(`admin.schoolStatus.${school.status}`)}</span>
          </div>
          <div className="small">
            {t(`billing.state.${school.subscription.state}`)}
            {school.subscription.paid_until &&
              ` · ${t("billing.until", { date: formatDate(school.subscription.paid_until, lang) })}`} ·{" "}
            {t("admin.codeIs", { code: school.join_code })}
          </div>
          <div className="small">
            <strong>{t("admin.schoolAdmins")}:</strong>{" "}
            {school.admins.length
              ? school.admins.map((a) => `${a.name} (${a.email || a.username}, ${t(`school.status.${a.status || "none"}`)})`).join(", ")
              : "—"}
          </div>
          <ErrorMessage error={error} />
          <div className="row">
            {school.status !== "verified" && (
              <button
                className="btn btn-sm btn-success"
                disabled={busy}
                onClick={() => act(school.status === "pending" ? "verify" : "reinstate")}
              >
                ✓ {t(school.status === "pending" ? "admin.verify" : "admin.reinstate")}
              </button>
            )}
            {school.status === "verified" && (
              <button
                className="btn btn-sm btn-danger"
                disabled={busy}
                onClick={() => window.confirm(t("admin.suspendConfirm")) && act("suspend")}
              >
                {t("admin.suspend")}
              </button>
            )}
            {pendingAdmins.length > 0 && (
              <button
                className="btn btn-sm"
                disabled={busy}
                onClick={() =>
                  run(() =>
                    api(`/admin/schools/${id}/members/`, { method: "POST", body: { ids: pendingAdmins.map((m) => m.id), approve: true } }),
                  )
                }
              >
                ✓ {t("admin.approveAdmins", { n: pendingAdmins.length })}
              </button>
            )}
          </div>
          {school.status === "verified" && (
            <form className="form" onSubmit={recordPayment}>
              <strong>{t("admin.recordPayment")}</strong>
              <div className="form-row">
                <label>
                  {t("billing.months")}
                  <input
                    type="number"
                    min="1"
                    max="24"
                    value={form.months}
                    onChange={(e) => setForm({ ...form, months: Number(e.target.value) })}
                  />
                </label>
                <label>
                  {t("billing.amount")}
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={form.amount}
                    onChange={(e) => setForm({ ...form, amount: e.target.value })}
                  />
                </label>
                <label>
                  {t("billing.currency")}
                  <select value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })}>
                    <option>USD</option>
                    <option>RWF</option>
                  </select>
                </label>
              </div>
              <label>
                {t("admin.paymentNote")}
                <input
                  value={form.note}
                  onChange={(e) => setForm({ ...form, note: e.target.value })}
                  required
                  placeholder={t("admin.paymentNoteHint")}
                />
              </label>
              <button className="btn btn-sm" disabled={busy}>
                {t("admin.record")}
              </button>
            </form>
          )}
          {school.payments.length > 0 && (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>{t("billing.date")}</th>
                    <th>{t("billing.amount")}</th>
                    <th>{t("billing.months")}</th>
                    <th>{t("billing.method")}</th>
                    <th>{t("billing.status")}</th>
                  </tr>
                </thead>
                <tbody>
                  {school.payments.map((p) => (
                    <tr key={p.reference}>
                      <td>{formatDate(p.paid_at || p.created_at, lang)}</td>
                      <td>
                        {p.amount} {p.currency}
                      </td>
                      <td>{p.months}</td>
                      <td>
                        {t(`billing.provider.${p.provider}`)}
                        {p.note && ` · ${p.note}`}
                      </td>
                      <td>{t(`billing.paymentStatus.${p.status}`)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </Loader>
  );
}

function Schools() {
  const { t, lang } = useI18n();
  const [status, setStatus] = useState("pending");
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(null);
  const state = useApi("/admin/schools/", { params: { status, q: query } }, [status, query]);
  return (
    <div className="stack">
      <div className="row">
        <div className="chips">
          {["pending", "verified", "suspended", ""].map((s) => (
            <button
              key={s || "all"}
              className={`chip ${status === s ? "active" : ""}`}
              aria-pressed={status === s}
              onClick={() => setStatus(s)}
            >
              {s ? t(`admin.schoolStatus.${s}`) : t("practice.all")}
            </button>
          ))}
        </div>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t("school.search")}
          aria-label={t("school.search")}
          style={{ maxWidth: 260 }}
        />
      </div>
      <Loader state={state}>
        {(list) =>
          list.length === 0 ? (
            <Empty icon="🏫">{t("admin.noSchools")}</Empty>
          ) : (
            <div className="stack">
              {list.map((s) => (
                <div key={s.id}>
                  <button
                    className="card card-link spread"
                    style={{ width: "100%", textAlign: "left", font: "inherit" }}
                    onClick={() => setOpen(open === s.id ? null : s.id)}
                  >
                    <span>
                      <strong>{s.name}</strong>{" "}
                      <span className="small muted">
                        · {s.district} · {t("admin.membersN", { n: s.members })}
                      </span>
                    </span>
                    <span className="small">
                      {t(`billing.state.${s.subscription.state}`)}
                      {s.subscription.paid_until && ` · ${formatDate(s.subscription.paid_until, lang)}`}
                    </span>
                  </button>
                  {open === s.id && <SchoolDetail id={s.id} onChanged={state.reload} />}
                </div>
              ))}
            </div>
          )
        }
      </Loader>
    </div>
  );
}

function SubscriptionStats({ subs }) {
  const { t } = useI18n();
  const fmt = (byCurrency) =>
    Object.entries(byCurrency)
      .map(([c, v]) => `${v} ${c}`)
      .join(" + ") || "0";
  return (
    <div className="stats">
      <div className="card stat">
        <strong>{subs.active_schools}</strong>
        <span className="muted small">{t("admin.activeSchools")}</span>
      </div>
      <div className="card stat">
        <strong>{subs.pending_schools}</strong>
        <span className="muted small">{t("admin.pendingSchools")}</span>
      </div>
      <div className="card stat">
        <strong>{fmt(subs.this_month)}</strong>
        <span className="muted small">{t("admin.revenueMonth")}</span>
      </div>
      <div className="card stat">
        <strong>{fmt(subs.all_time)}</strong>
        <span className="muted small">{t("admin.revenueTotal")}</span>
      </div>
    </div>
  );
}

export default function Admin() {
  const { t } = useI18n();
  const [tab, setTab] = useState("stats");
  return (
    <>
      <div className="page-header spread">
        <h1 style={{ margin: 0 }}>🛡️ {t("admin.title")}</h1>
        <a className="btn btn-secondary btn-sm" href="/django-admin/" target="_blank" rel="noopener noreferrer">
          {t("admin.djangoAdmin")} ↗
        </a>
      </div>
      <Tabs
        value={tab}
        onChange={setTab}
        tabs={[
          { value: "stats", label: t("admin.stats") },
          { value: "schools", label: t("admin.schools") },
          { value: "users", label: t("admin.users") },
          { value: "review", label: t("admin.review") },
          { value: "moderation", label: t("admin.moderation") },
          { value: "audit", label: t("admin.audit") },
        ]}
      />
      {tab === "stats" && <Stats />}
      {tab === "schools" && <Schools />}
      {tab === "users" && <Users />}
      {tab === "review" && <Review />}
      {tab === "moderation" && <Moderation />}
      {tab === "audit" && <Audit />}
    </>
  );
}
