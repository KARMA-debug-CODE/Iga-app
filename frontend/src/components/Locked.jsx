// Shown where premium content would be. Explains why it's locked and what the student can do,
// without making anyone feel bad that their school hasn't paid.
import { Link } from "react-router-dom";

import { useAuth } from "../auth";
import { useI18n } from "../i18n";

const ACTIONS = {
  no_school: { to: "/profile#school", key: "access.chooseSchool" },
  rejected: { to: "/profile#school", key: "access.chooseSchool" },
  not_subscribed: null,
  expired: null,
  pending_approval: null,
  school_not_verified: null,
  school_suspended: null,
  not_eligible: null,
};

export function accessReason(user) {
  return user?.access?.reason || "no_school";
}

export function LockedNotice({ reason: given, compact = false }) {
  const { user } = useAuth();
  const { t } = useI18n();
  const reason = given || accessReason(user);
  const school = user?.school?.name;
  const action = ACTIONS[reason];
  const isSchoolAdmin = user?.role === "school_admin" && user?.school_status === "approved";
  return (
    <div className={`locked-notice ${compact ? "compact" : "card"}`} role="note">
      <div className="locked-icon" aria-hidden>
        🔒
      </div>
      <div>
        <strong>{t("access.title")}</strong>
        <p className="small" style={{ margin: "4px 0 0" }}>
          {t(`access.reason.${reason}`, { school: school || "" })}
        </p>
        {!compact && (
          <div className="row" style={{ marginTop: 10 }}>
            {isSchoolAdmin ? (
              <Link className="btn btn-sm" to="/school/billing">
                {t("access.subscribe")}
              </Link>
            ) : (
              action && (
                <Link className="btn btn-sm" to={action.to}>
                  {t(action.key)}
                </Link>
              )
            )}
            <Link className="btn btn-sm btn-secondary" to="/learn">
              {t("access.freeLessons")}
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}

// A small banner for the dashboard when the account doesn't have full access.
export function AccessBanner() {
  const { user } = useAuth();
  const { t } = useI18n();
  if (!user || user.offline || user.access?.premium || !["student", "teacher"].includes(user.role)) return null;
  const reason = accessReason(user);
  const action = ACTIONS[reason];
  return (
    <div className="alert alert-warn access-banner" role="status">
      <span>
        🔓 {t(`access.banner.${reason}`, { school: user.school?.name || "" })}
      </span>
      {action && (
        <Link className="btn btn-sm" to={action.to}>
          {t(action.key)}
        </Link>
      )}
    </div>
  );
}

export function LockBadge() {
  const { t } = useI18n();
  return (
    <span className="pill pill-lock" title={t("access.title")}>
      🔒 {t("access.locked")}
    </span>
  );
}
