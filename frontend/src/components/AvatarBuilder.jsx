import { useState } from "react";

import { api } from "../api";
import { useAuth } from "../auth";
import { useI18n } from "../i18n";
import Avatar, { AVATAR_PARTS, avatarFor, randomAvatar } from "./Avatar";
import { Icon } from "./Icon";
import { ErrorMessage } from "./ui";

const ORDER = ["skin", "hair", "hairColor", "eyes", "mouth", "extra", "top", "bg"];

/** Build an avatar: a big preview, and for each part a row of small previews to choose from. */
export default function AvatarBuilder({ onSaved }) {
  const { user, setUser } = useAuth();
  const { t } = useI18n();
  const [choice, setChoice] = useState(() => avatarFor(user));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const changed = JSON.stringify(choice) !== JSON.stringify(avatarFor(user));

  async function save() {
    setBusy(true);
    setError(null);
    try {
      const updated = await api("/auth/me/", { method: "PATCH", body: { avatar: choice } });
      setUser(updated);
      onSaved?.();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="avatar-builder">
      <div className="avatar-preview">
        <Avatar user={user} avatar={choice} size={160} />
        <div className="row" style={{ justifyContent: "center" }}>
          <button type="button" className="btn btn-sm btn-secondary" onClick={() => setChoice(randomAvatar())}>
            <Icon name="shuffle" /> {t("avatar.surprise")}
          </button>
          <button type="button" className="btn btn-sm" onClick={save} disabled={busy || !changed}>
            <Icon name="save" /> {t("common.save")}
          </button>
        </div>
        <ErrorMessage error={error} />
      </div>
      <div className="avatar-parts">
        {ORDER.map((part) => (
          <fieldset key={part} className="avatar-part">
            <legend>{t(`avatar.part.${part}`)}</legend>
            <div className="avatar-options" role="radiogroup" aria-label={t(`avatar.part.${part}`)}>
              {Array.from({ length: AVATAR_PARTS[part] }, (_, value) => (
                <button
                  key={value}
                  type="button"
                  role="radio"
                  aria-checked={choice[part] === value}
                  aria-label={t("avatar.option", { part: t(`avatar.part.${part}`), n: value + 1 })}
                  className={`avatar-option ${choice[part] === value ? "selected" : ""}`}
                  onClick={() => setChoice({ ...choice, [part]: value })}
                >
                  <Avatar avatar={{ ...choice, [part]: value }} size={48} title="" />
                </button>
              ))}
            </div>
          </fieldset>
        ))}
      </div>
    </div>
  );
}
