// Profile avatars: an illustrated person drawn from a few choices (never a photo). The counts must match
// backend/apps/accounts/avatar.py. A user who hasn't built one gets a stable avatar made from their id.
import { useId } from "react";

export const AVATAR_PARTS = {
  bg: 10,
  skin: 6,
  hair: 10,
  hairColor: 6,
  eyes: 5,
  mouth: 5,
  extra: 5,
  top: 8,
};

const BG = ["#DBEAFE", "#DCFCE7", "#FEF3C7", "#FFE4E6", "#EDE9FE", "#FFEDD5", "#CCFBF1", "#E2E8F0", "#FCE7F3", "#ECFCCB"];
const SKIN = ["#F5D0B0", "#E2AE84", "#C48A5C", "#A26A42", "#7A4A2C", "#57311E"];
const HAIR = ["#17120F", "#3A2417", "#6B4226", "#9C5A2E", "#D9A54C", "#A3A3A3"];
const TOP = ["#1D4ED8", "#047857", "#B45309", "#7F1D1D", "#F1F5F9", "#475569", "#6D28D9", "#EA580C"];

// A small deterministic random generator, so the default avatar never changes for a user.
function seeded(seed) {
  let a = 0;
  for (const ch of String(seed)) a = (Math.imul(a ^ ch.charCodeAt(0), 2654435761) + 1) >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** The full avatar for a user: their choices, with any missing part filled from their id. */
export function avatarFor(user) {
  const random = seeded(user?.id ?? user?.username ?? "iga");
  const base = {};
  for (const [part, count] of Object.entries(AVATAR_PARTS)) base[part] = Math.floor(random() * count);
  base.extra = random() < 0.7 ? 0 : base.extra; // most default avatars without glasses or earrings
  return { ...base, ...(user?.avatar || {}) };
}

export function randomAvatar() {
  const random = seeded(`${Date.now()}-${Math.random()}`);
  const avatar = {};
  for (const [part, count] of Object.entries(AVATAR_PARTS)) avatar[part] = Math.floor(random() * count);
  return avatar;
}

function HairBack({ style, color }) {
  switch (style) {
    case 3: // afro
      return <circle cx="50" cy="38" r="29" fill={color} />;
    case 4: // braids
      return (
        <g fill={color}>
          <rect x="24" y="34" width="9" height="46" rx="4.5" />
          <rect x="67" y="34" width="9" height="46" rx="4.5" />
          <rect x="29" y="40" width="7" height="40" rx="3.5" opacity="0.85" />
          <rect x="64" y="40" width="7" height="40" rx="3.5" opacity="0.85" />
        </g>
      );
    case 6: // long
      return <path d="M27 40 C27 20 73 20 73 40 L76 78 C66 84 34 84 24 78 Z" fill={color} />;
    default:
      return null;
  }
}

function HairFront({ style, color, top }) {
  switch (style) {
    case 1: // short
      return <path d="M29 45 C28 24 72 24 71 45 C67 35 59 31 50 31 C41 31 33 35 29 45 Z" fill={color} />;
    case 2: // buzz cut
      return <path d="M31 40 C32 26 68 26 69 40 C64 34 57 32 50 32 C43 32 36 34 31 40 Z" fill={color} opacity="0.75" />;
    case 3: // afro (front edge)
      return <path d="M28 44 C26 22 74 22 72 44 C66 34 58 30 50 30 C42 30 34 34 28 44 Z" fill={color} />;
    case 4: // braids (top)
      return <path d="M29 44 C28 24 72 24 71 44 C66 33 58 30 50 30 C42 30 34 33 29 44 Z" fill={color} />;
    case 5: // bun
      return (
        <g fill={color}>
          <circle cx="50" cy="17" r="9" />
          <path d="M29 43 C28 24 72 24 71 43 C66 33 58 30 50 30 C42 30 34 33 29 43 Z" />
        </g>
      );
    case 6: // long (front, side parting)
      return <path d="M28 46 C26 22 74 22 72 46 C69 36 63 30 54 30 C50 36 40 40 28 46 Z" fill={color} />;
    case 7: // twists
      return (
        <g fill={color}>
          {[30, 37, 44, 51, 58, 65, 70].map((x, i) => (
            <circle key={x} cx={x} cy={i === 0 || i === 6 ? 36 : 28 - (i % 2) * 2} r="6" />
          ))}
          <path d="M29 42 C29 28 71 28 71 42 C66 35 58 33 50 33 C42 33 34 35 29 42 Z" />
        </g>
      );
    case 8: // headwrap
      return (
        <g>
          <path d="M26 42 C24 16 76 16 74 42 C68 33 59 30 50 30 C41 30 32 33 26 42 Z" fill={top === "#F1F5F9" ? "#0F766E" : top} />
          <circle cx="66" cy="20" r="7" fill={top === "#F1F5F9" ? "#0F766E" : top} />
          <path d="M30 38 C40 30 60 30 70 38" stroke="#FDE68A" strokeWidth="2" fill="none" opacity="0.8" />
        </g>
      );
    case 9: // cap
      return (
        <g fill={top === "#F1F5F9" ? "#1D4ED8" : top}>
          <path d="M29 40 C29 21 71 21 71 40 Z" />
          <path d="M50 38 L82 40 C82 44 60 44 50 42 Z" />
        </g>
      );
    default:
      return null;
  }
}

function Eyes({ style }) {
  const dark = "#1F2937";
  switch (style) {
    case 1: // happy
      return (
        <g stroke={dark} strokeWidth="2.4" fill="none" strokeLinecap="round">
          <path d="M39 49 Q42 45 45 49" />
          <path d="M55 49 Q58 45 61 49" />
        </g>
      );
    case 2: // wink
      return (
        <g fill={dark} stroke={dark} strokeWidth="2.4" strokeLinecap="round">
          <circle cx="42" cy="48" r="2.6" />
          <path d="M55 49 Q58 46 61 49" fill="none" />
        </g>
      );
    case 3: // wide
      return (
        <g>
          <circle cx="42" cy="48" r="4.2" fill="#fff" />
          <circle cx="58" cy="48" r="4.2" fill="#fff" />
          <circle cx="42.6" cy="48.4" r="2.2" fill={dark} />
          <circle cx="58.6" cy="48.4" r="2.2" fill={dark} />
        </g>
      );
    case 4: // calm
      return (
        <g stroke={dark} strokeWidth="2.4" strokeLinecap="round">
          <path d="M39 48.5 H45" />
          <path d="M55 48.5 H61" />
        </g>
      );
    default:
      return (
        <g fill={dark}>
          <circle cx="42" cy="48" r="2.6" />
          <circle cx="58" cy="48" r="2.6" />
        </g>
      );
  }
}

function Mouth({ style }) {
  const dark = "#7C2D12";
  switch (style) {
    case 1: // grin
      return (
        <g>
          <path d="M42 57 Q50 66 58 57 Z" fill={dark} />
          <path d="M43.5 57.6 H56.5 L55.6 59 H44.4 Z" fill="#fff" />
        </g>
      );
    case 2: // neutral
      return <path d="M45 59 H55" stroke={dark} strokeWidth="2.2" strokeLinecap="round" />;
    case 3: // surprised
      return <ellipse cx="50" cy="59" rx="3.2" ry="4" fill={dark} />;
    case 4: // smirk
      return <path d="M44 59 Q52 62 57 56" stroke={dark} strokeWidth="2.2" fill="none" strokeLinecap="round" />;
    default: // smile
      return <path d="M43 57 Q50 63 57 57" stroke={dark} strokeWidth="2.4" fill="none" strokeLinecap="round" />;
  }
}

function Extra({ style }) {
  switch (style) {
    case 1: // round glasses
      return (
        <g stroke="#111827" strokeWidth="1.8" fill="rgba(255,255,255,0.15)">
          <circle cx="42" cy="48" r="6" />
          <circle cx="58" cy="48" r="6" />
          <path d="M48 48 H52" />
        </g>
      );
    case 2: // square glasses
      return (
        <g stroke="#111827" strokeWidth="1.8" fill="rgba(255,255,255,0.15)">
          <rect x="35.5" y="43" width="12" height="10" rx="2" />
          <rect x="52.5" y="43" width="12" height="10" rx="2" />
          <path d="M47.5 47 H52.5" />
        </g>
      );
    case 3: // earrings
      return (
        <g fill="#F59E0B">
          <circle cx="29.5" cy="55" r="2.2" />
          <circle cx="70.5" cy="55" r="2.2" />
        </g>
      );
    case 4: // freckles
      return (
        <g fill="#7C4A2D" opacity="0.55">
          {[
            [37, 54],
            [40, 56],
            [36, 57],
            [63, 54],
            [60, 56],
            [64, 57],
          ].map(([x, y]) => (
            <circle key={`${x}-${y}`} cx={x} cy={y} r="0.9" />
          ))}
        </g>
      );
    default:
      return null;
  }
}

/** <Avatar user={user} size={40} /> or <Avatar avatar={{...}} /> */
export default function Avatar({ user, avatar, size = 40, title, className = "" }) {
  const a = avatar ? { ...avatarFor(user), ...avatar } : avatarFor(user);
  const skin = SKIN[a.skin] ?? SKIN[0];
  const hair = HAIR[a.hairColor] ?? HAIR[0];
  const top = TOP[a.top] ?? TOP[0];
  const label = title ?? user?.display_name ?? user?.name ?? "";
  const id = `avatar-clip-${useId().replace(/:/g, "")}`;
  return (
    <svg
      className={`avatar-svg ${className}`}
      width={size}
      height={size}
      viewBox="0 0 100 100"
      role={label ? "img" : undefined}
      aria-label={label || undefined}
      aria-hidden={label ? undefined : true}
    >
      <defs>
        <clipPath id={id}>
          <circle cx="50" cy="50" r="50" />
        </clipPath>
      </defs>
      <g clipPath={`url(#${id})`}>
        <rect width="100" height="100" fill={BG[a.bg] ?? BG[0]} />
        <HairBack style={a.hair} color={hair} />
        <path d="M16 104 C16 82 32 73 50 73 C68 73 84 82 84 104 Z" fill={top} />
        <path
          d="M42 73 L50 83 L58 73"
          fill="none"
          stroke={top === "#F1F5F9" ? "#94A3B8" : "#F8FAFC"}
          strokeWidth="2.4"
          strokeLinejoin="round"
        />
        <rect x="44" y="62" width="12" height="12" rx="4" fill={skin} />
        <circle cx="30" cy="49" r="4.5" fill={skin} />
        <circle cx="70" cy="49" r="4.5" fill={skin} />
        <ellipse cx="50" cy="46" rx="20.5" ry="23" fill={skin} />
        <HairFront style={a.hair} color={hair} top={top} />
        <g stroke={hair} strokeWidth="2" strokeLinecap="round" opacity="0.9">
          <path d="M38 42 Q42 40 46 42" fill="none" />
          <path d="M54 42 Q58 40 62 42" fill="none" />
        </g>
        <Eyes style={a.eyes} />
        <Mouth style={a.mouth} />
        <Extra style={a.extra} />
      </g>
    </svg>
  );
}
