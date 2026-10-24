import { lazy, Suspense, useEffect } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import { useAuth } from "./auth";
import ErrorBoundary from "./components/ErrorBoundary";
import Layout from "./components/Layout";
import StepUpDialog from "./components/StepUpDialog";
import { Spinner } from "./components/ui";
import { useI18n } from "./i18n";
import { useMaintenance } from "./maintenance";
import ConsentGate from "./pages/ConsentGate";
import Dashboard from "./pages/Dashboard";
import FirstLogin from "./pages/FirstLogin";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Maintenance from "./pages/Maintenance";
import Register from "./pages/Register";

const Subjects = lazy(() => import("./pages/Subjects"));
const Subject = lazy(() => import("./pages/Subject"));
const Lesson = lazy(() => import("./pages/Lesson"));
const Labs = lazy(() => import("./pages/Labs"));
const Lab = lazy(() => import("./pages/Lab"));
const Practice = lazy(() => import("./pages/Practice"));
const QuizPlayer = lazy(() => import("./pages/QuizPlayer"));
const Planner = lazy(() => import("./pages/Planner"));
const MyNotes = lazy(() => import("./pages/MyNotes"));
const TeachingPacks = lazy(() => import("./pages/TeachingPacks"));
const TeachingPack = lazy(() => import("./pages/TeachingPack"));
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
const CalculatorPage = lazy(() => import("./pages/Calculator"));
const Ask = lazy(() => import("./pages/Ask"));
const NotFound = lazy(() => import("./pages/NotFound"));
const ChildReport = lazy(() => import("./pages/Children"));
const QuizAnalytics = lazy(() => import("./pages/QuizAnalytics"));
const schoolPage = (name) => lazy(() => import("./pages/School").then((m) => ({ default: m[name] })));
const SchoolMembers = schoolPage("SchoolMembers");
const SchoolBilling = schoolPage("SchoolBilling");
const BillingReturn = schoolPage("BillingReturn");
const DevCheckout = schoolPage("DevCheckout");
const Receipt = schoolPage("Receipt");
const SchoolHome = schoolPage("SchoolHome");
const resetPage = (name) => lazy(() => import("./pages/PasswordReset").then((m) => ({ default: m[name] })));
const ForgotPassword = resetPage("ForgotPassword");
const ResetPassword = resetPage("ResetPassword");
const legalPage = (name) => lazy(() => import("./pages/Legal").then((m) => ({ default: m[name] })));
const Terms = legalPage("Terms");
const Privacy = legalPage("Privacy");
const Contact = lazy(() => import("./pages/Contact"));

// Public pages: open to everyone, signed in or not, and while an account still has to accept the Terms.
const OPEN_PATHS = new Set(["/terms", "/privacy", "/contact"]);

function RequireAuth({ children, teacher = false, admin = false, schoolAdmin = false }) {
  const { user, isTeacher, isAdmin } = useAuth();
  const location = useLocation();
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  if (admin && !isAdmin) return <Navigate to="/" replace />;
  if (teacher && !isTeacher) return <Navigate to="/" replace />;
  if (schoolAdmin && user.role !== "school_admin") return <Navigate to="/" replace />;
  return children;
}

function RedirectToLogin() {
  const location = useLocation();
  return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
}

function ScrollToTop() {
  const { pathname, hash } = useLocation();
  useEffect(() => {
    if (!hash) {
      window.scrollTo(0, 0);
      return undefined;
    }
    // Links like /profile#school go to that section once the page has rendered it.
    let id = hash.slice(1);
    try {
      id = decodeURIComponent(id);
    } catch {
      /* not valid percent-encoding: use it as it is */
    }
    let tries = 0;
    const timer = setInterval(() => {
      const element = document.getElementById(id);
      if (element || ++tries > 20) {
        clearInterval(timer);
        element?.scrollIntoView({ block: "start" });
      }
    }, 100);
    return () => clearInterval(timer);
  }, [pathname, hash]);
  return null;
}

export default function App() {
  const { user, ready } = useAuth();
  const { lang, setLang } = useI18n();
  const location = useLocation();
  const maintenance = useMaintenance();

  // Follow the language saved on the account when someone logs in.
  useEffect(() => {
    if (user?.preferred_language && user.preferred_language !== lang) setLang(user.preferred_language);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id]);

  if (!ready) return <Spinner />;

  // Iga is being updated: "back soon" for everyone; the Iga team logs in at /team.
  if (maintenance && location.pathname !== "/team") return <Maintenance />;

  // A temporary password from a teacher must be replaced before anything else.
  if (user?.must_change_password && !user.offline) return <FirstLogin />;

  // The Terms of Use and Privacy Policy must be accepted (again, when they change) before the app opens.
  if (user?.consent_required && !user.offline && !OPEN_PATHS.has(location.pathname)) {
    return (
      <>
        <StepUpDialog />
        <ConsentGate />
      </>
    );
  }

  const page = (element, opts) => <RequireAuth {...opts}>{element}</RequireAuth>;

  return (
    <>
      <ScrollToTop />
      {user && <StepUpDialog />}
      <ErrorBoundary resetKey={location.pathname} reloadOnRetry>
        <Suspense fallback={<Spinner />}>
          <Routes>
            <Route path="/login" element={user ? <Navigate to="/" replace /> : <Login />} />
            <Route path="/team" element={user ? <Navigate to="/" replace /> : <Login team />} />
            <Route path="/register" element={user ? <Navigate to="/" replace /> : <Register />} />
            <Route path="/forgot-password" element={user ? <Navigate to="/" replace /> : <ForgotPassword />} />
            {/* Open even when signed in: the link in the email may be opened on a shared computer. */}
            <Route path="/reset-password" element={<ResetPassword />} />
            <Route path="/terms" element={<Terms />} />
            <Route path="/privacy" element={<Privacy />} />
            <Route path="/contact" element={<Contact />} />
            <Route path="/pricing" element={<Landing section="pricing" />} />
            <Route path="/faq" element={<Landing section="faq" />} />
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
              <Route path="/planner" element={page(<Planner />)} />
              <Route path="/my-notes" element={page(<MyNotes />)} />
              <Route path="/classes" element={page(<Classes />)} />
              <Route path="/classes/:id" element={page(<ClassDetail />)} />
              <Route path="/groups" element={page(<Groups />)} />
              <Route path="/groups/:id" element={page(<GroupDetail />)} />
              <Route path="/leaderboard" element={page(<Leaderboard />)} />
              <Route path="/profile" element={page(<Profile />)} />
              <Route path="/search" element={page(<Search />)} />
              <Route path="/playground" element={page(<Playground />)} />
              <Route path="/calculator" element={page(<CalculatorPage />)} />
              <Route path="/ask" element={page(<Ask />)} />
              <Route path="/children/:id" element={page(<ChildReport />)} />
              <Route path="/teach" element={page(<Teach />, { teacher: true })} />
              <Route path="/classes/:id/quizzes/:quizId/analytics" element={page(<QuizAnalytics />, { teacher: true })} />
              <Route path="/teach/quizzes/:quizId/analytics" element={page(<QuizAnalytics />, { teacher: true })} />
              <Route path="/marking" element={page(<Marking />, { teacher: true })} />
              <Route path="/teaching-packs" element={page(<TeachingPacks />, { teacher: true })} />
              <Route path="/teaching-packs/:id" element={page(<TeachingPack />, { teacher: true })} />
              <Route path="/admin" element={page(<Admin />, { admin: true })} />
              <Route path="/school" element={page(<SchoolHome />, { schoolAdmin: true })} />
              <Route path="/school/members" element={page(<SchoolMembers />, { schoolAdmin: true })} />
              <Route path="/school/billing" element={page(<SchoolBilling />, { schoolAdmin: true })} />
              <Route path="/school/billing/return" element={page(<BillingReturn />, { schoolAdmin: true })} />
              <Route path="/school/billing/dev-checkout" element={page(<DevCheckout />, { schoolAdmin: true })} />
              <Route path="/school/billing/receipt/:reference" element={page(<Receipt />, { schoolAdmin: true })} />
              <Route path="*" element={<NotFound />} />
            </Route>
          </Routes>
        </Suspense>
      </ErrorBoundary>
    </>
  );
}
