import { Suspense, useEffect, useId, useRef, useState } from "react";

import { api } from "../api";
import { useI18n } from "../i18n";
import { BUILTIN_SIMS } from "../sims/registry";
import ErrorBoundary from "./ErrorBoundary";
import { Spinner } from "./ui";

function useSimulation(slug, initial, lang) {
  const [sim, setSim] = useState(initial || null);
  const [error, setError] = useState(null);
  useEffect(() => {
    if (initial || !slug) return;
    api(`/simulations/${slug}/`, { params: { lang } }).then(setSim).catch(setError);
  }, [slug, initial, lang]);
  return { sim: sim || initial, error };
}

let ggbScript = null;
function loadGeoGebra() {
  if (window.GGBApplet) return Promise.resolve();
  if (!ggbScript) {
    ggbScript = new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = "https://www.geogebra.org/apps/deployggb.js";
      script.onload = resolve;
      script.onerror = () => {
        ggbScript = null;
        reject(new Error("Could not load GeoGebra. Check your internet connection."));
      };
      document.head.appendChild(script);
    });
  }
  return ggbScript;
}

function GeoGebraApp({ app }) {
  const { lang } = useI18n();
  const holder = useRef(null);
  const id = `ggb-${useId().replace(/:/g, "")}`;
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    loadGeoGebra()
      .then(() => {
        if (cancelled || !holder.current) return;
        const width = holder.current.clientWidth || 600;
        const applet = new window.GGBApplet(
          {
            appName: app,
            language: lang, // GeoGebra speaks English and French
            width,
            height: Math.max(380, Math.round(width * 0.65)),
            showToolBar: true,
            showAlgebraInput: true,
            showMenuBar: false,
            enableShiftDragZoom: true,
            showResetIcon: true,
            scaleContainerClass: "ggb-holder",
          },
          true,
        );
        applet.inject(id);
      })
      .catch((e) => !cancelled && setError(e));
    return () => {
      cancelled = true;
    };
  }, [app, id, lang]);

  return (
    <div ref={holder} className="ggb-holder" style={{ width: "100%" }}>
      {error ? <div className="alert alert-error">{error.message}</div> : <div id={id} />}
    </div>
  );
}

/**
 * Embeds any simulation. Heavy third-party sims only load after the student taps
 * "Launch", which saves mobile data. Built-in labs render immediately and work offline.
 */
export default function SimEmbed({ slug, sim: initial, autoLaunch = false }) {
  const { t, lang } = useI18n();
  const { sim, error } = useSimulation(slug, initial, lang);
  const [launched, setLaunched] = useState(autoLaunch);
  const recorded = useRef(false);

  const isBuiltin = sim?.provider === "builtin";

  useEffect(() => {
    if (!sim || recorded.current || !(launched || isBuiltin)) return;
    recorded.current = true;
    api(`/simulations/${sim.slug}/view/`, { method: "POST" }).catch(() => {});
  }, [sim, launched, isBuiltin]);

  if (error) return <div className="alert alert-error">Simulation “{slug}” not found.</div>;
  if (!sim) return <Spinner />;

  if (isBuiltin) {
    const Component = BUILTIN_SIMS[sim.provider_id];
    if (!Component) return <div className="alert">Unknown built-in lab: {sim.provider_id}</div>;
    return (
      <div className="sim-frame">
        <ErrorBoundary compact>
          <Suspense fallback={<Spinner />}>
            <Component />
          </Suspense>
        </ErrorBoundary>
        <div className="sim-caption">
          🔬 {sim.title} · {t("labs.offline")}
        </div>
      </div>
    );
  }

  const embedUrl = sim.embed_url;
  const attribution = sim.provider === "phet" ? t("labs.attributionPhet") : sim.provider === "geogebra" ? t("labs.attributionGeogebra") : sim.provider_label;

  return (
    <div className="sim-frame">
      {!launched ? (
        <div className="sim-placeholder">
          <div style={{ fontSize: "2.4rem" }} aria-hidden>
            {sim.provider === "geogebra" ? "📈" : "🧪"}
          </div>
          <strong>{sim.title}</strong>
          <span className="small muted">{t("labs.dataNote")}</span>
          <button className="btn" onClick={() => setLaunched(true)}>
            ▶ {t("labs.launch")}
          </button>
        </div>
      ) : sim.provider === "geogebra" && !embedUrl ? (
        <GeoGebraApp app={sim.provider_id} />
      ) : (
        <iframe
          src={embedUrl}
          title={sim.title}
          allowFullScreen
          loading="lazy"
          sandbox="allow-scripts allow-same-origin allow-popups allow-fullscreen"
        />
      )}
      <div className="sim-caption">{attribution}</div>
    </div>
  );
}
