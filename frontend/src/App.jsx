import { lazy, Suspense, useEffect } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import { useAuth } from "./auth";
import Layout from "./components/Layout";
import { Spinner } from "./components/ui";
import { useI18n } from "./i18n";
import Dashboard from "./pages/Dashboard";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Register from "./pages/Register";

const Subjects = lazy(() => import("./pages/Subjects"));
const Subject = lazy(() => import("./pages/Subject"));
const Lesson = lazy(() => import("./pages/Lesson"));
const Labs = lazy(() => import("./pages/Labs"));
const Lab = lazy(() => import("./pages/Lab"));
const Practice = lazy(() => import("./pages/Practice"));
const QuizPlayer = lazy(() => import("./pages/QuizPlayer"));
const Classes = lazy(() => import("./pages/Classes"));
const ClassDetail = lazy(() => import("./pages/ClassDetail"));
const Groups = lazy(() => import("./pages/Groups"));
const GroupDetail = lazy(() => import("./pages/GroupDetail"));
const Leaderboard = lazy(() => import("./pages/Leaderboard"));
const Profile = lazy(() => import("./pages/Profile"));
const Teach = lazy(() => import("./pages/Teach"));
const Marking = lazy(() => import("./pages/Marking"));
const Admin = lazy(() => import("./pages/Admin"));
const Search = lazy(() => import("./pages/Search"));
const Playground = lazy(() => import("./pages/Playground"));
const NotFound = lazy(() => import("./pages/NotFound"));

function RequireAuth({ children, teacher = false, admin = false }) {
  const { user, isTeacher, isAdmin } = useAuth();
  const location = useLocation();
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  if (admin && !isAdmin) return <Navigate to="/" replace />;
  if (teacher && !isTeacher) return <Navigate to="/" replace />;
  return children;
}

function RedirectToLogin() {
  const location = useLocation();
  return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
}

function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => window.scrollTo(0, 0), [pathname]);
  return null;
}

export default function App() {
  const { user, ready } = useAuth();
  const { lang, setLang } = useI18n();

  // Follow the language saved on the account when someone logs in.
  useEffect(() => {
    if (user?.preferred_language && user.preferred_language !== lang) setLang(user.preferred_language);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id]);

  if (!ready) return <Spinner />;

  const page = (element, opts) => <RequireAuth {...opts}>{element}</RequireAuth>;

  return (
    <>
      <ScrollToTop />
      <Suspense fallback={<Spinner />}>
        <Routes>
          <Route path="/login" element={user ? <Navigate to="/" replace /> : <Login />} />
          <Route path="/register" element={user ? <Navigate to="/" replace /> : <Register />} />
          {!user && <Route path="/" element={<Landing />} />}
          <Route element={user ? <Layout /> : <RedirectToLogin />}>
            <Route path="/" element={page(<Dashboard />)} />
            <Route path="/learn" element={page(<Subjects />)} />
            <Route path="/learn/:code" element={page(<Subject />)} />
            <Route path="/lessons/:slug" element={page(<Lesson />)} />
            <Route path="/labs" element={page(<Labs />)} />
            <Route path="/labs/:slug" element={page(<Lab />)} />
            <Route path="/practice" element={page(<Practice />)} />
            <Route path="/attempts/:id" element={page(<QuizPlayer />)} />
            <Route path="/classes" element={page(<Classes />)} />
            <Route path="/classes/:id" element={page(<ClassDetail />)} />
            <Route path="/groups" element={page(<Groups />)} />
            <Route path="/groups/:id" element={page(<GroupDetail />)} />
            <Route path="/leaderboard" element={page(<Leaderboard />)} />
            <Route path="/profile" element={page(<Profile />)} />
            <Route path="/search" element={page(<Search />)} />
            <Route path="/playground" element={page(<Playground />)} />
            <Route path="/teach" element={page(<Teach />, { teacher: true })} />
            <Route path="/marking" element={page(<Marking />, { teacher: true })} />
            <Route path="/admin" element={page(<Admin />, { admin: true })} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </Suspense>
    </>
  );
}
