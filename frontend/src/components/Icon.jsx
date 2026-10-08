// Line icons (Lucide, ISC licence) used instead of emojis everywhere in the app. Each icon is imported by
// name so only the icons the app uses end up in the download.
import {
  Code2,
  Database,
  Keyboard,
  Play,
  RotateCcw,
  Square,
  Terminal,
} from "lucide-react";

const ICONS = {
  code: Code2,
  cpp: Terminal,
  database: Database,
  java: Terminal,
  keyboard: Keyboard,
  play: Play,
  python: Terminal,
  reset: RotateCcw,
  stop: Square,
};

/** <Icon name="play" /> — decorative by default; pass `label` when the icon is the only content. */
export function Icon({ name, size = 18, label, className = "", strokeWidth = 2 }) {
  const Component = ICONS[name];
  if (!Component) return null;
  return (
    <Component
      className={`icon ${className}`}
      size={size}
      strokeWidth={strokeWidth}
      aria-hidden={label ? undefined : true}
      aria-label={label}
      role={label ? "img" : undefined}
      focusable="false"
    />
  );
}

export const ICON_NAMES = Object.keys(ICONS);
