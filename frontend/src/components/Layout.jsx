import { Suspense, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../auth";
import { useOnline } from "../hooks";
import { useI18n } from "../i18n";
import ErrorBoundary from "./ErrorBoundary";
import { Logo, Spinner } from "./ui";

export default function Layout() {
  const { user, isTeacher, isAdmin } = useAuth();
  const { t } = useI18n();
  const online = useOnline();
  const navigate = useNavigate();
  const location = useLocation();
  const [query, setQuery] = useState("");

  const primary = [
    { to: "/", icon: "🏠", label: t("nav.home"), end: true },
    { to: "/learn", icon: "📚", label: t("nav.learn") },
    { to: "/labs", icon: "🔬", label: t("nav.labs") },
    { to: "/practice", icon: "📝", label: t("nav.practice") },
    { to: "/groups", icon: "👥", label: t("nav.groups") },
  ];
  const secondary = [
    { to: "/classes", icon: "🏫", label: t("nav.classes") },
    { to: "/leaderboard", icon: "🏆", label: t("nav.leaderboard") },
    { to: "/playground", icon: "💻", label: t("nav.playground") },
    ...(isTeacher
      ? [
          { to: "/teach", icon: "🧑🏽‍🏫", label: t("nav.teach") },
          { to: "/marking", icon: "✅", label: t("nav.marking") },
        ]
      : []),
    ...(isAdmin ? [{ to: "/admin", icon: "🛡️", label: t("nav.admin") }] : []),
    { to: "/profile", icon: "⚙️", label: t("nav.profile") },
  ];

  const initials = (user?.first_name?.[0] || user?.username?.[0] || "?").toUpperCase();

  function submitSearch(event) {
    event.preventDefault();
    if (query.trim()) navigate(`/search?q=${encodeURIComponent(query.trim())}`);
  }

  return (
    <>
      <header className="topbar">
        <div className="flag-stripe" />
        <div className="topbar-inner">
          <Link to="/" className="brand" aria-label="Iga home">
            <Logo />
            <span>Iga</span>
          </Link>
          <form className="search-box" role="search" onSubmit={submitSearch}>
            <label className="sr-only" htmlFor="global-search">
              {t("nav.search")}
            </label>
            <input
              id="global-search"
              type="search"
              placeholder={t("nav.search")}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </form>
          <Link to="/profile" className="avatar" aria-label={t("nav.profile")} title={user?.display_name}>
            {initials}
          </Link>
        </div>
        {!online && <div className="offline-banner">{t("common.offline")}</div>}
      </header>

      <div className="layout">
        <aside className="sidebar" aria-label="Main">
          <nav>
            {primary.map((item) => (
              <NavLink key={item.to} to={item.to} end={item.end}>
                <span aria-hidden>{item.icon}</span>
                {item.label}
              </NavLink>
            ))}
            <hr />
            {secondary.map((item) => (
              <NavLink key={item.to} to={item.to}>
                <span aria-hidden>{item.icon}</span>
                {item.label}
              </NavLink>
            ))}
          </nav>
        </aside>
        <main className="main" id="main">
          <ErrorBoundary resetKey={location.pathname}>
            <Suspense fallback={<Spinner />}>
              <Outlet />
            </Suspense>
          </ErrorBoundary>
        </main>
      </div>

      <nav className="bottom-nav" aria-label="Main">
        {primary.map((item) => (
          <NavLink key={item.to} to={item.to} end={item.end}>
            <span className="icon" aria-hidden>
              {item.icon}
            </span>
            {item.label}
          </NavLink>
        ))}
      </nav>
    </>
  );
}
