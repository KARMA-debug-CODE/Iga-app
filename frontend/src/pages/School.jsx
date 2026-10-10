// The school administrator's area: subscription, members, payments and receipts.
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";

import { api } from "../api";
import { useAuth } from "../auth";
import { Icon } from "../components/Icon";
import { Empty, ErrorMessage, Loader, Tabs, useToast } from "../components/ui";
import { formatDate, formatDay, formatMoney, useApi } from "../hooks";
import { useI18n } from "../i18n";

function daysUntil(date) {
  return Math.ceil((new Date(date).getTime() - Date.now()) / 86_400_000);
}


// Shown instead of the dashboard while the school or this administrator waits for verification.
function WaitingForVerification() {
  const { user, reloadUser } = useAuth();
  const { t } = useI18n();
  const [checking, setChecking] = useState(false);
  const schoolPending = user.school && !user.school.verified;
  const checkAgain = () => {
    setChecking(true);
    reloadUser()
      .catch(() => {})
      .finally(() => setChecking(false));
  };
  if (user.school?.suspended) {
    return (
      <div className="card" style={{ maxWidth: 640 }}>
        <h1 className="title-with-icon" style={{ marginTop: 0 }}>
          <Icon name="warning" size={28} /> {t("school.suspendedTitle")}
        </h1>
        <p>{t("school.suspendedText", { school: user.school.name })}</p>
      </div>
    );
  }
  return (
    <div className="card" style={{ maxWidth: 640 }}>
      <h1 className="title-with-icon" style={{ marginTop: 0 }}>
        <Icon name="hourglass" size={28} /> {t("school.waitingTitle")}
      </h1>
      <p>{schoolPending ? t("school.waitingSchool", { school: user.school.name }) : t("school.waitingAdmin", { school: user.school?.name || "" })}</p>
      <p className="small muted">{t("school.waitingHelp")}</p>
      <button className="btn btn-secondary" onClick={checkAgain} disabled={checking}>
        <Icon name="refresh" size={16} /> {t("school.checkAgain")}
      </button>
    </div>
  );
}

export function SubscriptionCard({ school }) {
  const { t, lang } = useI18n();
  const sub = school.subscription;
  const left = sub.paid_until ? daysUntil(sub.paid_until) : null;
  const tone = { active: left <= 7 ? "warn" : "good", grace: "warn", expired: "bad", none: "bad" }[sub.state];
  return (
    <div className={`card subscription-card ${tone}`}>
      <div className="spread">
        <h2 style={{ margin: 0 }}>{t("billing.subscription")}</h2>
        <span className={`pill ${tone === "good" ? "pill-success" : tone === "warn" ? "pill-warn" : "pill-danger"}`}>{t(`billing.state.${sub.state}`)}</span>
      </div>
      <p style={{ margin: "10px 0" }}>
        {sub.state === "active" && t("billing.activeUntil", { date: formatDay(sub.paid_until, lang), n: left })}
        {sub.state === "grace" && t("billing.graceUntil", { date: formatDay(sub.grace_ends, lang) })}
        {sub.state === "expired" && t("billing.expiredOn", { date: formatDay(sub.paid_until, lang) })}
        {sub.state === "none" && t("billing.never")}
      </p>
      <p className="small muted" style={{ marginTop: 0 }}>
        {t("billing.priceLine", { price: formatMoney(school.pricing.prices.USD || Object.values(school.pricing.prices)[0], school.pricing.prices.USD ? "USD" : Object.keys(school.pricing.prices)[0], lang) })}
      </p>
      <Link className="btn" to="/school/billing">
        {sub.state === "active" ? t("billing.renew") : t("billing.subscribeNow")}
      </Link>
    </div>
  );
}

function JoinCode({ school, onChange }) {
  const { t } = useI18n();
  const [toast, showToast] = useToast();
  const [error, setError] = useState(null);
  async function regenerate() {
    if (!window.confirm(t("school.newCodeConfirm"))) return;
    try {
      const data = await api("/school/new-code/", { method: "POST" });
      onChange(data.join_code);
      showToast(t("school.newCodeDone"));
    } catch (err) {
      setError(err);
    }
  }
  return (
    <div className="card">
      {toast}
      <h2 style={{ marginTop: 0 }}>{t("school.codeTitle")}</h2>
      <span className="code-display">{school.join_code}</span>
      <p className="small muted">{t("school.codeExplain")}</p>
      <ErrorMessage error={error} />
      <div className="row">
        <button
          className="btn btn-sm btn-secondary"
          onClick={() => navigator.clipboard?.writeText(school.join_code).then(() => showToast(t("school.copied")))}
        >
          <Icon name="copy" size={16} /> {t("school.copy")}
        </button>
        <button className="btn btn-sm btn-ghost" onClick={regenerate}>
          <Icon name="refresh" size={16} /> {t("school.newCode")}
        </button>
      </div>
    </div>
  );
}

export function SchoolHome() {
  const { user } = useAuth();
  const { t } = useI18n();
  const ready = user.school_status === "approved" && user.school?.verified;
  const state = useApi("/school/", { skip: !ready });
  if (!ready) return <WaitingForVerification />;
  return (
    <Loader state={state}>
      {(school) => (
        <>
          <div className="page-header">
            <h1 className="title-with-icon">
              <Icon name="school" size={28} /> {school.name}
            </h1>
            <p>
              {school.district}
              {school.province && ` · ${school.province}`}
            </p>
          </div>
          <div className="stats">
            <Link to="/school/members?status=approved&role=student" className="card card-link stat">
              <strong>{school.counts.students}</strong>
              <span className="small muted">{t("school.students")}</span>
            </Link>
            <Link to="/school/members?status=approved&role=teacher" className="card card-link stat">
              <strong>{school.counts.teachers}</strong>
              <span className="small muted">{t("school.teachers")}</span>
            </Link>
            <Link to="/school/members?status=pending" className={`card card-link stat ${school.counts.pending ? "attention" : ""}`}>
              <strong>{school.counts.pending}</strong>
              <span className="small muted">{t("school.pendingRequests")}</span>
            </Link>
          </div>
          <section className="section grid-2">
            <SubscriptionCard school={school} />
            <JoinCode school={school} onChange={(code) => state.setData((s) => ({ ...s, join_code: code }))} />
          </section>
        </>
      )}
    </Loader>
  );
}

export function SchoolMembers() {
  const { t, lang } = useI18n();
  const [params, setParams] = useSearchParams();
  const statusFilter = params.get("status") || "pending";
  const role = params.get("role") || "";
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(() => new Set());
  const [error, setError] = useState(null);
  const [toast, showToast] = useToast();
  const state = useApi("/school/members/", { params: { status: statusFilter, role, q: query } }, [statusFilter, role, query]);
  const members = useMemo(() => state.data || [], [state.data]);
  // Only people on screen can be acted on, even if the selection was made from an older list.
  const chosen = members.filter((m) => selected.has(m.id)).map((m) => m.id);

  function setFilter(next) {
    setSelected(new Set());
    setParams({ ...Object.fromEntries(params), ...next });
  }

  async function decide(approve) {
    setError(null);
    try {
      const res = await api("/school/members/decide/", { method: "POST", body: { ids: chosen, approve } });
      showToast(t(approve ? "school.approvedN" : "school.rejectedN", { n: res.changed.length }));
      setSelected(new Set());
      state.reload();
    } catch (err) {
      setError(err);
    }
  }

  async function confirmTeacher(member) {
    setError(null);
    try {
      await api("/school/members/decide/", { method: "POST", body: { ids: [member.id], approve: true } });
      showToast(t("school.teacherConfirmed", { name: member.display_name }));
      state.reload();
    } catch (err) {
      setError(err);
    }
  }

  async function remove(member) {
    if (!window.confirm(t("school.removeConfirm", { name: member.display_name }))) return;
    setError(null);
    try {
      await api(`/school/members/${member.id}/remove/`, { method: "POST" });
      state.reload();
    } catch (err) {
      setError(err);
    }
  }

  const toggle = (id) =>
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  return (
    <>
      {toast}
      <div className="page-header">
        <h1 className="title-with-icon">
          <Icon name="members" size={28} /> {t("school.members")}
        </h1>
        <p>{t("school.membersHelp")}</p>
      </div>
      <Tabs
        value={statusFilter}
        onChange={(value) => setFilter({ status: value })}
        tabs={[
          { value: "pending", label: t("school.tab.pending") },
          { value: "approved", label: t("school.tab.approved") },
          { value: "rejected", label: t("school.tab.rejected") },
        ]}
      />
      <div className="form-row" style={{ marginBottom: 12 }}>
        <label>
          {t("school.role")}
          <select value={role} onChange={(e) => setFilter({ role: e.target.value })}>
            <option value="">{t("practice.all")}</option>
            <option value="student">{t("auth.student")}</option>
            <option value="teacher">{t("auth.teacher")}</option>
            <option value="school_admin">{t("auth.schoolAdmin")}</option>
          </select>
        </label>
        <label>
          {t("school.searchMembers")}
          <input
            value={query}
            onChange={(e) => {
              setSelected(new Set()); // never act on people the search has hidden
              setQuery(e.target.value);
            }}
          />
        </label>
      </div>
      <ErrorMessage error={error} />
      {statusFilter === "pending" && members.length > 0 && (
        <div className="row" style={{ marginBottom: 12 }}>
          <button className="btn btn-sm btn-secondary" onClick={() => setSelected(new Set(members.map((m) => m.id)))}>
            {t("school.selectAll")}
          </button>
          <button className="btn btn-sm btn-success" disabled={!chosen.length} onClick={() => decide(true)}>
            <Icon name="check" size={16} /> {t("school.approve")} ({chosen.length})
          </button>
          <button className="btn btn-sm btn-danger" disabled={!chosen.length} onClick={() => decide(false)}>
            {t("school.reject")}
          </button>
        </div>
      )}
      <Loader state={state}>
        {() =>
          members.length === 0 ? (
            <Empty icon="members">{t("school.noMembers")}</Empty>
          ) : (
            <div className="card">
              <ul className="list">
                {members.map((m) => (
                  <li key={m.id} className="spread">
                    <label className="row" style={{ flexWrap: "nowrap", minWidth: 0, fontWeight: 400 }}>
                      {statusFilter === "pending" && <input type="checkbox" checked={selected.has(m.id)} onChange={() => toggle(m.id)} />}
                      <span style={{ minWidth: 0 }}>
                        <strong>{m.display_name}</strong> <span className="small muted">@{m.username}</span>
                        <div className="small muted">
                          {t(`auth.${m.role === "school_admin" ? "schoolAdmin" : m.role}`)}
                          {m.grade && ` · ${m.grade}`} · {formatDate(m.school_approved_at || m.date_joined, lang)}
                        </div>
                        {m.needs_teacher_confirmation && <span className="pill pill-warn small">{t("school.teacherUnconfirmed")}</span>}
                      </span>
                    </label>
                    <div className="row" style={{ flexWrap: "nowrap" }}>
                      {m.needs_teacher_confirmation && (
                        <button className="btn btn-sm btn-success" onClick={() => confirmTeacher(m)}>
                          <Icon name="check" size={16} /> {t("school.confirmTeacher")}
                        </button>
                      )}
                      {statusFilter !== "pending" && m.role !== "school_admin" && (
                        <button className="btn btn-sm btn-ghost" onClick={() => remove(m)}>
                          {t("classes.remove")}
                        </button>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )
        }
      </Loader>
    </>
  );
}

export function SchoolBilling() {
  const { t, lang } = useI18n();
  const navigate = useNavigate();
  const school = useApi("/school/");
  const payments = useApi("/school/payments/");
  const [months, setMonths] = useState(1);
  const [currency, setCurrency] = useState("USD");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  async function pay() {
    setBusy(true);
    setError(null);
    try {
      const res = await api("/billing/checkout/", { method: "POST", body: { months, currency } });
      // Hosted checkout pages live on the provider's site; the dev checkout is one of our routes.
      const url = new URL(res.checkout_url, window.location.origin);
      if (url.origin === window.location.origin) navigate(url.pathname + url.search);
      else window.location.assign(res.checkout_url);
    } catch (err) {
      setError(err);
      setBusy(false);
    }
  }

  return (
    <>
      <div className="page-header">
        <h1 className="title-with-icon">
          <Icon name="billing" size={28} /> {t("billing.title")}
        </h1>
        <p>{t("billing.help")}</p>
      </div>
      <Loader state={school}>
        {(s) => {
          const prices = s.pricing.prices;
          const unit = Number(prices[currency] ?? Object.values(prices)[0]);
          return (
            <div className="grid-2">
              <SubscriptionCard school={s} />
              <div className="card form">
                <h2 style={{ marginTop: 0 }}>{t("billing.pay")}</h2>
                <div>
                  <div style={{ fontWeight: 600, fontSize: "0.92rem", marginBottom: 6 }}>{t("billing.months")}</div>
                  <div className="chips wrap">
                    {s.pricing.month_options.map((n) => (
                      <button type="button" key={n} className={`chip ${months === n ? "active" : ""}`} aria-pressed={months === n} onClick={() => setMonths(n)}>
                        {t("billing.monthsN", { n })}
                      </button>
                    ))}
                  </div>
                </div>
                {Object.keys(prices).length > 1 && (
                  <label>
                    {t("billing.currency")}
                    <select value={currency} onChange={(e) => setCurrency(e.target.value)}>
                      {Object.keys(prices).map((c) => (
                        <option key={c} value={c}>
                          {c === "RWF" ? t("billing.rwf") : t("billing.usd")}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
                <div className="billing-total">
                  <span>{t("billing.total")}</span>
                  <strong>{formatMoney(unit * months, currency, lang)}</strong>
                </div>
                <p className="small muted" style={{ margin: 0 }}>
                  {t("billing.covers", { n: months })}
                </p>
                <ErrorMessage error={error} />
                {s.pricing.online ? (
                  <button className="btn" onClick={pay} disabled={busy}>
                    {busy ? t("common.loading") : `${t("billing.payNow")} →`}
                  </button>
                ) : (
                  <div className="alert">{t("billing.offlineOnly")}</div>
                )}
                {s.pricing.provider === "dev" && <p className="small muted">{t("billing.devNote")}</p>}
                <p className="small muted" style={{ margin: 0 }}>
                  {t("billing.bankTransfer")}
                </p>
              </div>
            </div>
          );
        }}
      </Loader>

      <h2 className="section">{t("billing.history")}</h2>
      <Loader state={payments}>
        {(list) =>
          list.length === 0 ? (
            <Empty icon="receipt">{t("billing.noPayments")}</Empty>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th scope="col">{t("billing.date")}</th>
                    <th scope="col">{t("billing.period")}</th>
                    <th scope="col">{t("billing.amount")}</th>
                    <th scope="col">{t("billing.status")}</th>
                    <th scope="col">{t("billing.receipt")}</th>
                  </tr>
                </thead>
                <tbody>
                  {list.map((p) => (
                    <tr key={p.reference}>
                      <td>{formatDay(p.paid_at || p.created_at, lang)}</td>
                      <td>{p.period_start ? `${formatDay(p.period_start, lang)} → ${formatDay(p.period_end, lang)}` : t("billing.monthsN", { n: p.months })}</td>
                      <td>{formatMoney(p.amount, p.currency, lang)}</td>
                      <td>
                        <span className={`pill ${p.status === "succeeded" ? "pill-success" : p.status === "pending" ? "pill-warn" : ""}`}>
                          {t(`billing.paymentStatus.${p.status}`)}
                        </span>
                      </td>
                      <td>
                        {p.status === "succeeded" && (
                          <Link to={`/school/billing/receipt/${p.reference}`} className="with-icon">
                            <Icon name="receipt" size={16} /> {t("billing.view")}
                          </Link>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        }
      </Loader>
    </>
  );
}

// Where the provider sends the browser back. The server asks the provider what happened.
export function BillingReturn() {
  const { t } = useI18n();
  const { reloadUser } = useAuth();
  const [params] = useSearchParams();
  // Flutterwave adds status, tx_ref and transaction_id to our return link (with "&", or a second
  // "?" that ends up inside ref). Only the server's answer counts: the transaction id tells it which
  // attempt to check, and the status only decides what to say while the server still says pending.
  const [refValue, extra = ""] = (params.get("ref") || "").split("?");
  const extraParams = new URLSearchParams(extra);
  const gateway = (name) => params.get(name) || extraParams.get(name) || "";
  const reference = gateway("tx_ref") || refValue;
  const transactionId = gateway("transaction_id");
  const gatewayCancelled = ["cancelled", "failed"].includes(gateway("status"));
  const [payment, setPayment] = useState(null);
  const [error, setError] = useState(null);
  const tries = useRef(0);

  useEffect(() => {
    if (!reference) return undefined;
    let alive = true;
    let timer;
    async function check() {
      try {
        const data = await api(`/billing/payments/${encodeURIComponent(reference)}/confirm/`, {
          method: "POST",
          body: transactionId ? { transaction_id: transactionId } : {},
        });
        if (!alive) return;
        setPayment(data);
        if (data.status === "succeeded") reloadUser().catch(() => {});
        // Mobile money approvals can take a while: keep asking for about two minutes.
        if (data.status === "pending" && !gatewayCancelled && tries.current < 24) {
          tries.current += 1;
          timer = setTimeout(check, 5000);
        }
      } catch (err) {
        if (alive) setError(err);
      }
    }
    check();
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [reference, transactionId, gatewayCancelled, reloadUser]);

  // The payer left the checkout or ran out of attempts: say so rather than "being confirmed"
  // (the server closes the payment later, and still applies a success if one turns up).
  const status = payment?.status === "pending" && gatewayCancelled ? "cancelled" : payment?.status;
  return (
    <div className="card" style={{ maxWidth: 560, margin: "0 auto", textAlign: "center" }}>
      {error ? (
        <ErrorMessage error={error} />
      ) : !payment ? (
        <p>{t("billing.checking")}</p>
      ) : (
        <>
          <Icon
            name={{ succeeded: "ok", pending: "hourglass" }[status] || "warning"}
            size={48}
            strokeWidth={1.6}
            style={{ color: { succeeded: "var(--success)", pending: "var(--warn)" }[status] || "var(--danger)" }}
          />
          <h1>{t(`billing.result.${status}`)}</h1>
          <p>{t(`billing.resultHelp.${status}`)}</p>
        </>
      )}
      <div className="row" style={{ justifyContent: "center" }}>
        <Link className="btn" to="/school/billing">
          {t("billing.backToBilling")}
        </Link>
        {status === "succeeded" && (
          <Link className="btn btn-secondary" to={`/school/billing/receipt/${encodeURIComponent(reference)}`}>
            <Icon name="receipt" size={16} /> {t("billing.receipt")}
          </Link>
        )}
      </div>
    </div>
  );
}

// A stand-in for the provider's checkout page in development (BILLING_DEV_MODE).
export function DevCheckout() {
  const { t, lang } = useI18n();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const reference = params.get("ref");
  const state = useApi(`/billing/payments/${reference}/`, { skip: !reference }, [reference]);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  async function finish(outcome) {
    setBusy(true);
    setError(null);
    try {
      await api(`/billing/dev/${reference}/complete/`, { method: "POST", body: { outcome } });
      navigate(`/school/billing/return?ref=${reference}`, { replace: true });
    } catch (err) {
      setError(err);
      setBusy(false);
    }
  }

  return (
    <div className="card" style={{ maxWidth: 480, margin: "0 auto" }}>
      <div className="alert alert-warn">{t("billing.devBanner")}</div>
      <Loader state={state}>
        {(p) => (
          <>
            <h1>{p.school_name}</h1>
            <p>
              {t("billing.monthsN", { n: p.months })} · <strong>{formatMoney(p.amount, p.currency, lang)}</strong>
            </p>
            <ErrorMessage error={error} />
            <div className="row">
              <button className="btn btn-success" disabled={busy} onClick={() => finish("success")}>
                <Icon name="check" size={16} /> {t("billing.devPay")}
              </button>
              <button className="btn btn-ghost" disabled={busy} onClick={() => finish("cancel")}>
                {t("common.cancel")}
              </button>
            </div>
          </>
        )}
      </Loader>
    </div>
  );
}

export function Receipt() {
  const { reference } = useParams();
  const { t, lang } = useI18n();
  const state = useApi(`/billing/payments/${reference}/`, {}, [reference]);
  return (
    <Loader state={state}>
      {(p) => (
        <div className="card receipt" style={{ maxWidth: 640 }}>
          <div className="spread">
            <h1 className="title-with-icon" style={{ margin: 0 }}>
              <Icon name="receipt" size={28} /> {t("billing.receiptTitle")}
            </h1>
            <button className="btn btn-sm btn-secondary no-print" onClick={() => window.print()}>
              <Icon name="print" size={16} /> {t("roster.print")}
            </button>
          </div>
          <dl className="receipt-lines">
            <dt>{t("billing.school")}</dt>
            <dd>{p.school_name}</dd>
            <dt>{t("billing.reference")}</dt>
            <dd>
              <code>{p.reference}</code>
            </dd>
            <dt>{t("billing.date")}</dt>
            <dd>{formatDay(p.paid_at, lang)}</dd>
            <dt>{t("billing.period")}</dt>
            <dd>
              {formatDay(p.period_start, lang)} → {formatDay(p.period_end, lang)} ({t("billing.monthsN", { n: p.months })})
            </dd>
            <dt>{t("billing.amount")}</dt>
            <dd>
              <strong>{formatMoney(p.amount, p.currency, lang)}</strong>
            </dd>
            <dt>{t("billing.method")}</dt>
            <dd>
              {t(`billing.provider.${p.provider}`)}
              {p.note && ` · ${p.note}`}
            </dd>
            {p.paid_by && (
              <>
                <dt>{t("billing.paidBy")}</dt>
                <dd>{p.paid_by}</dd>
              </>
            )}
          </dl>
          <p className="small muted">{t("billing.receiptNote")}</p>
        </div>
      )}
    </Loader>
  );
}
