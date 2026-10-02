import { Link } from "react-router-dom";

import { Logo } from "../components/ui";
import { LanguagePicker } from "./Landing";

export default function AuthShell({ title, children }) {
  return (
    <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", padding: "24px var(--gutter)" }}>
      <div style={{ width: "100%", maxWidth: 440 }}>
        <Link to="/" className="brand" style={{ justifyContent: "center", marginBottom: 16 }}>
          <Logo size={42} />
          <span style={{ fontSize: "1.6rem" }}>Iga</span>
        </Link>
        <div className="card">
          <h1 style={{ fontSize: "1.5rem" }}>{title}</h1>
          {children}
        </div>
        <div style={{ marginTop: 16, display: "flex", justifyContent: "center" }}>
          <LanguagePicker />
        </div>
      </div>
    </div>
  );
}
