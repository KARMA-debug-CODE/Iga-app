import { useState } from "react";
import { Link } from "react-router-dom";

import { api, newIdempotencyKey, results, saveFile } from "../api";
import { Icon } from "../components/Icon";
import { Empty, ErrorMessage, Loader, Tabs } from "../components/ui";
import { formatDate, formatDay, formatMoney, formatNumber, useApi } from "../hooks";
import { useI18n } from "../i18n";
import { safeUrl } from "../safeUrl";

const ROLE_KEYS = { student: "auth.student", teacher: "auth.teacher", parent: "auth.parent", school_admin: "auth.schoolAdmin", admin: "auth.admin" };

/** Translate a key built from an API value, showing `fallback` for values the dictionaries don't know yet. */
function tOr(t, key, fallback) {
  const text = t(key);
  return text === key ? fallback : text;
}

/** Santa's AI and the code runner, the costly services: use today and over 30 days, and their limits. */
function CostlyServices({ santa, runner }) {
  const { t, lang } = useI18n();
  const n = (value) => formatNumber(value, lang);
  const limit = (value) => (value ? n(value) : t("admin.limit.none"));
  const rows = (period) => [
    ["admin.santa.questions", n(period.questions)],
    ["admin.santa.tokens", `${n(period.input_tokens)} / ${n(period.output_tokens)}`],
    ["admin.santa.students", n(period.students)],
    ["admin.santa.limited", n(period.limited)],
  ];
  return (
    <div className="card costly-services">
      <h3>{t("admin.santa.title")}</h3>
      <div className="grid-2">
        {[
          ["admin.santa.today", santa.today],
          ["admin.santa.last30", santa.last_30_days],
        ].map(([label, period]) => (
          <div key={label}>
            <h4>{t(label)}</h4>
            <ul className="list">
              {rows(period).map(([key, value]) => (
                <li key={key} className="spread">
                  <span>{t(key)}</span>
                  <strong>{value}</strong>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      {santa.top_schools_today.length > 0 && (
        <>
          <h4>{t("admin.santa.topSchools")}</h4>
          <ol>
            {santa.top_schools_today.map((school) => (
              <li key={school.school}>
                {school.school}{" "}
                <span className="muted small">
                  {t("admin.santa.schoolUse", { questions: n(school.questions), tokens: n(school.tokens), students: n(school.students) })}
                </span>
              </li>
            ))}
          </ol>
        </>
      )}
      <h4>{t("admin.santa.limits")}</h4>
      <ul className="list">
        {Object.entries(santa.limits).map(([key, value]) => (
          <li key={key} className="spread">
            <span>{t(`admin.limit.${key}`)}</span>
            <strong>{limit(value)}</strong>
          </li>
        ))}
      </ul>
      {runner && (
        <>
          <h3 style={{ marginTop: 16 }}>{t("admin.runner.title")}</h3>
          <ul className="list">
            {[
              ["admin.runner.runs", n(runner.today.runs)],
              ["admin.runner.cpu", n(runner.today.cpu_seconds)],
              ["admin.runner.students", n(runner.today.students)],
              ["admin.runner.limited", n(runner.today.limited)],
              ["admin.runner.dailyRuns", limit(runner.limits.daily_runs)],
              ["admin.runner.dailyCpu", limit(runner.limits.daily_cpu_seconds)],
            ].map(([key, value]) => (
              <li key={key} className="spread">
                <span>{t(key)}</span>
                <strong>{value}</strong>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

function Stats({ state }) {
  const { t } = useI18n();
  return (
    <Loader state={state}>
      {(s) => (
        <div className="stack">
          {s.subscriptions && <SubscriptionStats subs={s.subscriptions} />}
          <div className="stats">
            {Object.entries(s.users_by_role).map(([role, n]) => (
              <div className="card stat" key={role}>
                <strong>{n}</strong>
                <span className="muted small">{tOr(t, `admin.roleCount.${role}`, `${role}s`)}</span>
              </div>
            ))}
            <div className="card stat">
              <strong>{s.active_last_7_days}</strong>
              <span className="muted small">{t("admin.activeWeek")}</span>
            </div>
            <div className="card stat">
              <strong>{s.content.awaiting_review}</strong>
              <span className="muted small">{t("admin.awaitingReview")}</span>
            </div>
          </div>
          <div className="grid-2">
            <div className="card">
              <h3>{t("admin.content")}</h3>
              <ul className="list">
                {Object.entries(s.content).map(([k, v]) => (
                  <li key={k} className="spread">
                    <span>{tOr(t, `admin.count.${k}`, k.replace(/_/g, " "))}</span>
                    <strong>{v}</strong>
                  </li>
                ))}
              </ul>
            </div>
            <div className="card">
              <h3>{t("admin.activity7")}</h3>
              <ul className="list">
                {Object.entries(s.activity_last_7_days).map(([k, v]) => (
                  <li key={k} className="spread">
                    <span>{tOr(t, `admin.count.${k}`, k.replace(/_/g, " "))}</span>
                    <strong>{v}</strong>
                  </li>
                ))}
              </ul>
              <h3 style={{ marginTop: 16 }}>{t("admin.studentsByGrade")}</h3>
              <div className="row">
                {Object.entries(s.students_by_grade).map(([g, n]) => (
                  <span key={g} className="pill">
                    {g || "—"}: {n}
                  </span>
                ))}
              </div>
            </div>
            <div className="card">
              <h3>{t("admin.popularLessons")}</h3>
              <ol>
                {s.popular_lessons.map((l) => (
                  <li key={l.title}>
                    {l.title} <span className="muted small">({l.count})</span>
                  </li>
                ))}
              </ol>
            </div>
            {s.santa && <CostlyServices santa={s.santa} runner={s.code_runner} />}
            <div className="card">
              <h3>{t("admin.popularLabs")}</h3>
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
  const { t, lang } = useI18n();
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
        <input type="search" placeholder={t("admin.searchUsers")} value={q} onChange={(e) => setQ(e.target.value)} style={{ maxWidth: 260 }} />
      </div>
      <Loader state={state}>
        {(data) => {
          const list = results(data);
          if (!list.length) return <Empty icon="ok">{t("admin.nothing")}</Empty>;
          return (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>{t("admin.col.user")}</th>
                    <th>{t("admin.col.role")}</th>
                    <th>{t("admin.col.school")}</th>
                    <th>{t("admin.col.joined")}</th>
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
                        {ROLE_KEYS[u.role] ? t(ROLE_KEYS[u.role]) : u.role} {u.grade}
                        {u.role === "teacher" && !u.teacher_approved && <span className="pill pill-warn">{t("admin.pending")}</span>}
                        {!u.is_active && <span className="pill pill-danger">{t("admin.disabled")}</span>}
                      </td>
                      <td>{u.school}</td>
                      <td className="small">{formatDate(u.date_joined, lang)}</td>
                      <td>
                        <div className="row">
                          {u.role === "teacher" && !u.teacher_approved && (
                            <button className="btn btn-sm btn-success" onClick={() => update(u, { teacher_approved: true })}>
                              {t("admin.approve")}
                            </button>
                          )}
                          <button className="btn btn-sm btn-secondary" onClick={() => update(u, { is_active: !u.is_active })}>
                            {u.is_active ? t("admin.disable") : t("admin.enable")}
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
  const { t, lang } = useI18n();
  const state = useApi("/admin/review/");
  async function decide(item, approve) {
    await api("/admin/review/decide/", { method: "POST", body: { type: item.type, id: item.id, approve } });
    state.setData((list) => list.filter((x) => !(x.type === item.type && x.id === item.id)));
  }
  return (
    <Loader state={state}>
      {(items) =>
        items.length === 0 ? (
          <Empty icon="ok">{t("admin.nothing")}</Empty>
        ) : (
          <div className="stack">
            {items.map((item) => (
              <div className="card spread" key={`${item.type}-${item.id}`}>
                <div>
                  <span className="pill">{tOr(t, `admin.type.${item.type}`, item.type)}</span> <strong>{item.title}</strong>
                  <div className="small muted">
                    {item.subject} · {item.grade} · {item.author} · {formatDate(item.updated_at, lang)}
                  </div>
                  {item.type === "lesson" && <Link to={`/lessons/${item.slug}`}>{t("teach.preview")} →</Link>}
                  {item.url && (
                    <a href={safeUrl(item.url)} target="_blank" rel="noopener noreferrer">
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
  const { t, lang } = useI18n();
  const state = useApi("/admin/moderation/");
  async function resolve(report, hide) {
    await api(`/admin/moderation/${report.id}/resolve/`, { method: "POST", body: { hide } });
    state.setData((list) => list.filter((r) => r.message.id !== report.message.id));
  }
  return (
    <Loader state={state}>
      {(reports) =>
        reports.length === 0 ? (
          <Empty icon="ok">{t("admin.nothing")}</Empty>
        ) : (
          <div className="stack">
            {reports.map((r) => (
              <div className="card" key={r.id}>
                <div className="small muted">
                  {r.message.group} · {t("admin.reportedBy", { name: r.reporter })} · {formatDate(r.created_at, lang)}
                </div>
                <blockquote className="alert" style={{ margin: "8px 0" }}>
                  <strong>{r.message.author}:</strong> {r.message.body}
                </blockquote>
                <div className="small">{t("admin.reason", { reason: r.reason })}</div>
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
  const { t, lang } = useI18n();
  // "Security" shows sign-ins, lockouts, password and 2FA changes, refused and throttled requests.
  const [security, setSecurity] = useState(false);
  const state = useApi("/admin/audit/", { params: security ? { security: 1 } : undefined });
  return (
    <div className="stack">
      <div className="chips wrap">
        <button type="button" className={`chip ${!security ? "active" : ""}`} aria-pressed={!security} onClick={() => setSecurity(false)}>
          {t("admin.auditAll")}
        </button>
        <button type="button" className={`chip ${security ? "active" : ""}`} aria-pressed={security} onClick={() => setSecurity(true)}>
          {t("admin.auditSecurity")}
        </button>
      </div>
      <Loader state={state}>
        {(entries) => (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>{t("admin.col.when")}</th>
                  <th>{t("admin.col.who")}</th>
                  <th>{t("admin.col.action")}</th>
                  <th>{t("admin.col.target")}</th>
                  <th>{t("admin.col.ip")}</th>
                  <th>{t("admin.col.details")}</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((e) => (
                  <tr key={e.id}>
                    <td className="small">{formatDate(e.created_at, lang)}</td>
                    <td>{e.actor || "—"}</td>
                    <td>
                      <code>{e.action}</code>
                    </td>
                    <td className="small">{e.target}</td>
                    <td className="small">{e.ip || "—"}</td>
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
    </div>
  );
}

function SchoolDetail({ id, onChanged }) {
  const { t, lang } = useI18n();
  const state = useApi(`/admin/schools/${id}/`, {}, [id]);
  const members = useApi(`/admin/schools/${id}/members/`, {}, [id]);
  const [form, setForm] = useState({ months: 1, amount: "200", currency: "USD", note: "", external_reference: "" });
  // One key per payment being recorded: a double click or a resend after an error records it once.
  const [paymentKey, setPaymentKey] = useState(newIdempotencyKey);
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
  // A registration that isn't a real school: deleted, and whoever registered it is released.
  async function reject() {
    if (!window.confirm(t("admin.rejectSchoolConfirm"))) return;
    setBusy(true);
    setError(null);
    try {
      await api(`/admin/schools/${id}/reject/`, { method: "POST" });
      onChanged();
    } catch (err) {
      setError(err);
      setBusy(false);
    }
  }
  const recordPayment = (e) => {
    e.preventDefault();
    run(async () => {
      await api(`/admin/schools/${id}/payments/`, { method: "POST", body: form, headers: { "Idempotency-Key": paymentKey } });
      setForm((f) => ({ ...f, note: "", external_reference: "" }));
      setPaymentKey(newIdempotencyKey());
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
              ` · ${t("billing.until", { date: formatDay(school.subscription.paid_until, lang) })}`} ·{" "}
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
                <Icon name="check" size={16} /> {t(school.status === "pending" ? "admin.verify" : "admin.reinstate")}
              </button>
            )}
            {school.status === "pending" && (
              <button className="btn btn-sm btn-danger" disabled={busy} onClick={reject}>
                {t("admin.rejectSchool")}
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
                <Icon name="check" size={16} /> {t("admin.approveAdmins", { n: pendingAdmins.length })}
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
                  maxLength={300}
                  placeholder={t("admin.paymentNoteHint")}
                />
              </label>
              <label>
                {t("admin.externalReference")}
                <input
                  value={form.external_reference}
                  onChange={(e) => setForm({ ...form, external_reference: e.target.value })}
                  maxLength={100}
                  placeholder={t("admin.externalReferenceHint")}
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
                    <th>{t("admin.gross")}</th>
                    <th>{t("admin.providerFee")}</th>
                    <th>{t("admin.net")}</th>
                    <th>{t("billing.months")}</th>
                    <th>{t("billing.method")}</th>
                    <th>{t("billing.status")}</th>
                  </tr>
                </thead>
                <tbody>
                  {school.payments.map((p) => (
                    <tr key={p.reference}>
                      <td>{formatDay(p.paid_at || p.created_at, lang)}</td>
                      <td>{formatMoney(p.amount, p.currency, lang)}</td>
                      <td>{p.gross_amount == null ? "—" : formatMoney(p.gross_amount, p.currency, lang)}</td>
                      <td>{p.provider_fee == null ? "—" : formatMoney(p.provider_fee, p.currency, lang)}</td>
                      <td>{p.net_amount == null ? "—" : formatMoney(p.net_amount, p.currency, lang)}</td>
                      <td>{p.months}</td>
                      <td>
                        {t(`billing.provider.${p.provider}`)}
                        {p.external_reference && ` · ${p.external_reference}`}
                        {p.note && ` · ${p.note}`}
                      </td>
                      <td>{t(`billing.paymentStatus.${p.status}`)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <Ledger school={school} busy={busy} run={run} />
        </div>
      )}
    </Loader>
  );
}

const EMPTY_CORRECTION = { kind: "refund", amount: "", currency: "USD", months: 0, corrects: "", note: "" };

/** The school's money ledger: entries are never changed; a refund or a correction is a new entry. */
function Ledger({ school, busy, run }) {
  const { t, lang } = useI18n();
  const [form, setForm] = useState(EMPTY_CORRECTION);
  const [key, setKey] = useState(newIdempotencyKey);
  const [open, setOpen] = useState(false);

  const record = (e) => {
    e.preventDefault();
    run(async () => {
      const body = { ...form, months: Number(form.months) || 0, corrects: form.corrects ? Number(form.corrects) : null };
      await api(`/admin/schools/${school.id}/ledger/`, { method: "POST", body, headers: { "Idempotency-Key": key } });
      setForm(EMPTY_CORRECTION);
      setKey(newIdempotencyKey());
      setOpen(false);
    });
  };

  return (
    <div className="stack" style={{ gap: 8 }}>
      <div className="spread">
        <strong>{t("admin.ledger")}</strong>
        <button className="btn btn-sm btn-secondary" type="button" onClick={() => setOpen(!open)} aria-expanded={open}>
          {t("admin.addCorrection")}
        </button>
      </div>
      <p className="small muted" style={{ margin: 0 }}>
        {t("admin.ledgerHelp")}
      </p>
      {open && (
        <form className="form" onSubmit={record}>
          <div className="form-row">
            <label>
              {t("admin.entryKind")}
              <select value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}>
                <option value="refund">{t("admin.ledgerKind.refund")}</option>
                <option value="correction">{t("admin.ledgerKind.correction")}</option>
              </select>
            </label>
            <label>
              {t("billing.amount")}
              <input
                type="number"
                step="0.01"
                value={form.amount}
                onChange={(e) => setForm({ ...form, amount: e.target.value })}
                required
                placeholder={form.kind === "refund" ? "-200" : "0"}
              />
            </label>
            <label>
              {t("field.currency")}
              <select value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })}>
                <option>USD</option>
                <option>RWF</option>
              </select>
            </label>
            <label>
              {t("billing.months")}
              <input
                type="number"
                min="-24"
                max="24"
                value={form.months}
                onChange={(e) => setForm({ ...form, months: e.target.value })}
              />
            </label>
            <label>
              {t("admin.corrects")}
              <input
                type="number"
                min="1"
                value={form.corrects}
                onChange={(e) => setForm({ ...form, corrects: e.target.value })}
              />
            </label>
          </div>
          <label>
            {t("admin.correctionNote")}
            <input value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} required maxLength={300} />
          </label>
          <span className="small muted">{t("admin.correctionHelp")}</span>
          <button className="btn btn-sm" disabled={busy}>
            {t("admin.record")}
          </button>
        </form>
      )}
      {school.ledger.length === 0 ? (
        <span className="small muted">{t("admin.ledgerEmpty")}</span>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>{t("billing.date")}</th>
                <th>{t("admin.entryKind")}</th>
                <th>{t("admin.gross")}</th>
                <th>{t("admin.providerFee")}</th>
                <th>{t("admin.net")}</th>
                <th>{t("billing.months")}</th>
                <th>{t("field.note")}</th>
              </tr>
            </thead>
            <tbody>
              {school.ledger.map((e) => (
                <tr key={e.sequence}>
                  <td>{e.sequence}</td>
                  <td>{formatDay(e.created_at, lang)}</td>
                  <td>
                    {tOr(t, `admin.ledgerKind.${e.kind}`, e.kind)}
                    {e.corrects && ` (#${e.corrects})`}
                  </td>
                  <td>{formatMoney(e.gross_amount, e.currency, lang)}</td>
                  <td>{formatMoney(e.provider_fee, e.currency, lang)}</td>
                  <td>{formatMoney(e.net_amount, e.currency, lang)}</td>
                  <td>{e.months}</td>
                  <td className="small">
                    {[e.reference, e.note, e.actor_name].filter(Boolean).join(" · ")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function LedgerExport() {
  const { t } = useI18n();
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  async function download() {
    setBusy(true);
    setError(null);
    try {
      const blob = await api("/admin/ledger/export/", { as: "blob" });
      saveFile(blob, `iga-ledger-${new Date().toISOString().slice(0, 10)}.csv`);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <button className="btn btn-sm btn-secondary" disabled={busy} onClick={download}>
        <Icon name="download" size={16} /> {t("admin.exportLedger")}
      </button>
      <ErrorMessage error={error} />
    </>
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
        <LedgerExport />
      </div>
      <Loader state={state}>
        {(list) =>
          list.length === 0 ? (
            <Empty icon="school">{t("admin.noSchools")}</Empty>
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
                      {s.subscription.paid_until && ` · ${formatDay(s.subscription.paid_until, lang)}`}
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

/** {currency: {gross, fees, net}} -> {currency: one of them}. */
const ledgerColumn = (totals, column) => Object.fromEntries(Object.entries(totals || {}).map(([c, v]) => [c, v[column]]));

function SubscriptionStats({ subs }) {
  const { t, lang } = useI18n();
  const fmt = (byCurrency) =>
    Object.entries(byCurrency)
      .map(([currency, value]) => formatMoney(value, currency, lang))
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
      {subs.ledger && (
        <>
          <div className="card stat">
            <strong>{fmt(ledgerColumn(subs.ledger.all_time, "fees"))}</strong>
            <span className="muted small">{t("admin.feesTotal")}</span>
          </div>
          <div className="card stat">
            <strong>{fmt(ledgerColumn(subs.ledger.all_time, "net"))}</strong>
            <span className="muted small">{t("admin.netTotal")}</span>
          </div>
        </>
      )}
    </div>
  );
}

export default function Admin() {
  const { t } = useI18n();
  const [tab, setTab] = useState("stats");
  const stats = useApi("/admin/stats/");
  // The Django admin has a secret address, given only to platform administrators (none when it is off).
  const djangoAdmin = stats.data?.django_admin_url;
  return (
    <>
      <div className="page-header spread">
        <h1 className="title-with-icon" style={{ margin: 0 }}>
          <Icon name="admin" size={28} /> {t("admin.title")}
        </h1>
        {djangoAdmin && (
          <a className="btn btn-secondary btn-sm" href={djangoAdmin} target="_blank" rel="noopener noreferrer">
            {t("admin.djangoAdmin")} <Icon name="external" size={16} />
          </a>
        )}
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
      {tab === "stats" && <Stats state={stats} />}
      {tab === "schools" && <Schools />}
      {tab === "users" && <Users />}
      {tab === "review" && <Review />}
      {tab === "moderation" && <Moderation />}
      {tab === "audit" && <Audit />}
    </>
  );
}
