import { Suspense, useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../auth";
import { useOnline } from "../hooks";
import { useI18n } from "../i18n";
import Avatar from "./Avatar";
import ErrorBoundary from "./ErrorBoundary";
import { Icon } from "./Icon";
import { Logo, Spinner } from "./ui";

const NAV_KEY = "iga.navHidden";

function savedNavHidden() {
  try {
    return localStorage.getItem(NAV_KEY) === "1";
  } catch {
    return false;
  }
}

export default function Layout() {
  const { user, isTeacher, isAdmin, notice, clearNotice } = useAuth();
  const { t } = useI18n();
  const online = useOnline();
  const navigate = useNavigate();
  const location = useLocation();
  const [query, setQuery] = useState("");
  const [navHidden, setNavHidden] = useState(savedNavHidden);

  useEffect(() => {
    try {
      if (navHidden) localStorage.setItem(NAV_KEY, "1");
      else localStorage.removeItem(NAV_KEY);
    } catch {
      // Private windows may refuse storage; the choice then lasts until the page reloads.
    }
  }, [navHidden]);

  const isParent = user?.role === "parent";
  const isSchoolAdmin = user?.role === "school_admin";
  const schoolNav = isSchoolAdmin && user.school_status === "approved";
  const primary = isSchoolAdmin
    ? [
        { to: "/", icon: "home", label: t("nav.home"), end: true },
        ...(schoolNav
          ? [
              { to: "/school/members", icon: "members", label: t("nav.members") },
              { to: "/school/billing", icon: "billing", label: t("nav.billing") },
            ]
          : []),
        { to: "/learn", icon: "learn", label: t("nav.learn") },
        { to: "/profile", icon: "profile", label: t("nav.profile") },
      ]
    : [
        { to: "/", icon: "home", label: t("nav.home"), end: true },
        { to: "/learn", icon: "learn", label: t("nav.learn") },
        { to: "/labs", icon: "labs", label: t("nav.labs") },
        { to: "/practice", icon: "practice", label: t("nav.practice") },
        isParent ? { to: "/profile", icon: "profile", label: t("nav.profile") } : { to: "/groups", icon: "groups", label: t("nav.groups") },
      ];
  const secondary = isSchoolAdmin
    ? [
        { to: "/labs", icon: "labs", label: t("nav.labs") },
        { to: "/practice", icon: "practice", label: t("nav.practice") },
        { to: "/playground", icon: "playground", label: t("nav.playground") },
        { to: "/calculator", icon: "calculator", label: t("nav.calculator") },
        { to: "/ask", icon: "santa", label: t("nav.ask") },
      ]
    : [
        ...(isParent
          ? []
          : [
              { to: "/classes", icon: "classes", label: t("nav.classes") },
              { to: "/leaderboard", icon: "leaderboard", label: t("nav.leaderboard") },
            ]),
        { to: "/playground", icon: "playground", label: t("nav.playground") },
        { to: "/calculator", icon: "calculator", label: t("nav.calculator") },
        { to: "/ask", icon: "santa", label: t("nav.ask") },
        ...(isTeacher
          ? [
              { to: "/teach", icon: "teach", label: t("nav.teach") },
              { to: "/marking", icon: "marking", label: t("nav.marking") },
            ]
          : []),
        ...(isAdmin ? [{ to: "/admin", icon: "admin", label: t("nav.admin") }] : []),
        ...(isParent ? [] : [{ to: "/profile", icon: "profile", label: t("nav.profile") }]),
      ];

  function submitSearch(event) {
    event.preventDefault();
    if (query.trim()) navigate(`/search?q=${encodeURIComponent(query.trim())}`);
  }

  return (
    <>
      <header className="topbar">
        <div className="flag-stripe" />
        <div className="topbar-inner">
          <button
            type="button"
            className="nav-toggle"
            onClick={() => setNavHidden((hidden) => !hidden)}
            aria-pressed={navHidden}
            aria-controls="main-nav"
            title={navHidden ? t("nav.show") : t("nav.hide")}
          >
            <Icon name={navHidden ? "sidebarOpen" : "sidebarClose"} size={20} />
            <span className="sr-only">{navHidden ? t("nav.show") : t("nav.hide")}</span>
          </button>
          <Link to="/" className="brand" aria-label={t("a11y.home")}>
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
            <Avatar user={user} size={38} title="" />
          </Link>
        </div>
        {!online && <div className="offline-banner">{t("common.offline")}</div>}
        {notice?.key === "deletionCancelled" && (
          <div className="notice-banner" role="status">
            <span>{t(`notice.${notice.key}`, notice)}</span>
            <button type="button" className="btn btn-ghost btn-sm" onClick={clearNotice} aria-label={t("notice.close")}>
              <Icon name="close" size={18} />
            </button>
          </div>
        )}
      </header>

      <div className={`layout ${navHidden ? "nav-hidden" : ""}`}>
        <aside className="sidebar" id="main-nav" aria-label={t("a11y.mainNav")} hidden={navHidden}>
          <nav>
            {primary.map((item) => (
              <NavLink key={item.to} to={item.to} end={item.end}>
                <Icon name={item.icon} size={20} />
                {item.label}
              </NavLink>
            ))}
            <hr />
            {secondary.map((item) => (
              <NavLink key={item.to} to={item.to}>
                <Icon name={item.icon} size={20} />
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

      {!navHidden && (
        <nav className="bottom-nav" aria-label={t("a11y.mainNav")}>
          {primary.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end}>
              <Icon name={item.icon} size={22} className="nav-icon" />
              {item.label}
            </NavLink>
          ))}
        </nav>
      )}
    </>
  );
}
