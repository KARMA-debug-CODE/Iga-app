import { useEffect, useRef, useState } from "react";

import { confirmIdentity, setStepUpHandler } from "../api";
import { useAuth } from "../auth";
import { useI18n } from "../i18n";

/**
 * Privileged actions (the admin area, school membership and billing decisions, resetting a student's
 * password) need a password confirmed in the last few minutes. When the server asks for it, this dialog
 * asks for the password (and the 2FA code when it is on), then the action carries on by itself.
 */
export default function StepUpDialog() {
  const { user } = useAuth();
  const { t } = useI18n();
  const [pending, setPending] = useState(null);
  const [form, setForm] = useState({ password: "", otp: "" });
  const [needOtp, setNeedOtp] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const passwordRef = useRef(null);

  useEffect(() => {
    setStepUpHandler(
      () =>
        new Promise((resolve, reject) => {
          setForm({ password: "", otp: "" });
          setError("");
          setPending({ resolve, reject });
        }),
    );
    return () => setStepUpHandler(null);
  }, []);

  useEffect(() => {
    if (pending) passwordRef.current?.focus();
  }, [pending]);

  if (!pending) return null;
  const showOtp = needOtp || Boolean(user?.totp_enabled);

  function close(ok) {
    if (ok) pending.resolve();
    else pending.reject(new Error("cancelled"));
    setPending(null);
    setForm({ password: "", otp: "" });
  }

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await confirmIdentity(form.password, showOtp ? form.otp : "");
      close(true);
    } catch (err) {
      if (err.data?.otp_required) setNeedOtp(true);
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" onKeyDown={(e) => e.key === "Escape" && close(false)}>
      <div className="card modal" role="dialog" aria-modal="true" aria-labelledby="step-up-title">
        <h2 id="step-up-title" style={{ marginTop: 0 }}>
          {t("stepUp.title")}
        </h2>
        <p className="muted">{t("stepUp.intro")}</p>
        <form className="form" onSubmit={submit}>
          <label>
            {t("auth.password")}
            <input
              ref={passwordRef}
              type="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              autoComplete="current-password"
              required
            />
          </label>
          {showOtp && (
            <label>
              {t("auth.otp")}
              <input
                value={form.otp}
                onChange={(e) => setForm({ ...form, otp: e.target.value })}
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={8}
                required
              />
            </label>
          )}
          {error && (
            <div className="alert alert-error" role="alert">
              {error}
            </div>
          )}
          <div className="row" style={{ justifyContent: "flex-end", gap: 8 }}>
            <button type="button" className="btn btn-secondary" onClick={() => close(false)} disabled={busy}>
              {t("common.cancel")}
            </button>
            <button className="btn" disabled={busy}>
              {t("stepUp.confirm")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
