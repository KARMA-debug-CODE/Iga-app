import { useCallback, useEffect, useRef, useState } from "react";

import { useI18n } from "../i18n";
import { MOTION_MS, prefersReducedMotion } from "../motion";
import { Icon } from "./Icon";

const RAYS = 10;
const COLOURS = ["burst-blue", "burst-yellow", "burst-green"];

/**
 * A ring and rays that burst once around their parent (which is position: relative), in the flag's colours.
 * Decorative: nothing is drawn when the reader asks for less motion.
 */
export function Burst({ size = 96 }) {
  if (prefersReducedMotion()) return null;
  return (
    <svg className="burst" viewBox="-50 -50 100 100" style={{ "--burst-size": `${size}px` }} aria-hidden="true" focusable="false">
      <circle className="burst-ring" r="40" />
      {Array.from({ length: RAYS }, (_, i) => (
        <g key={i} transform={`rotate(${(360 / RAYS) * i})`}>
          <line className={`burst-ray ${COLOURS[i % COLOURS.length]}`} x1="0" y1="-30" x2="0" y2="-40" />
        </g>
      ))}
    </svg>
  );
}

/** What a lesson or quiz earned ({level, badges} from the server), one celebration each. */
export function celebrationsFor(rewards) {
  if (!rewards) return [];
  return [
    ...(rewards.level ? [{ kind: "level", level: rewards.level }] : []),
    ...(rewards.badges || []).map((code) => ({ kind: "badge", code })),
  ];
}

/** A new level or badge: a small card that pops in above the toasts and goes by itself. */
export function Celebration({ item, onDone, ms = 3200 }) {
  const { t } = useI18n();
  const [leaving, setLeaving] = useState(false);
  useEffect(() => {
    const out = setTimeout(() => setLeaving(true), ms - MOTION_MS.base);
    const end = setTimeout(onDone, ms);
    return () => {
      clearTimeout(out);
      clearTimeout(end);
    };
  }, [onDone, ms]);
  const text =
    item.kind === "level" ? t("celebrate.level", { level: item.level }) : t("celebrate.badge", { name: t(`badge.${item.code}.name`) });
  return (
    <div className={`celebration ${leaving ? "is-leaving" : ""}`} role="status">
      <span className="celebration-medal">
        {item.kind === "level" ? <span className="celebrate-pop">{item.level}</span> : <Icon name="award" size={20} className="celebrate-pop" />}
        <Burst size={84} />
      </span>
      <span className="celebration-text">{text}</span>
    </div>
  );
}

/** Returns [node, celebrate]: render `node` once, call `celebrate(rewards)` after a lesson or quiz. */
export function useCelebrations() {
  const [queue, setQueue] = useState([]);
  const nextId = useRef(0);
  const celebrate = useCallback((rewards) => {
    const items = celebrationsFor(rewards).map((item) => ({ ...item, id: ++nextId.current }));
    if (items.length) setQueue((q) => [...q, ...items]);
  }, []);
  const done = useCallback(() => setQueue((q) => q.slice(1)), []);
  const node = queue.length ? <Celebration key={queue[0].id} item={queue[0]} onDone={done} /> : null;
  return [node, celebrate];
}
