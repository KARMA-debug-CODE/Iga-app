import { Suspense, useEffect, useId, useRef, useState } from "react";

import { api } from "../api";
import { translateNow, useI18n } from "../i18n";
import { safeUrl } from "../safeUrl";
import { BUILTIN_SIMS } from "../sims/registry";
import ErrorBoundary from "./ErrorBoundary";
import { Icon } from "./Icon";
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

// The frame may run scripts with its own origin's storage (PhET and GeoGebra need both), so it only
// shows an https page on another site: with this site's origin, allow-same-origin would undo the sandbox.
export function frameUrl(value) {
  const url = safeUrl(value, { httpsOnly: true });
  return url && new URL(url, window.location.origin).origin !== window.location.origin ? url : undefined;
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
        reject(new Error(translateNow("sim.geogebraLoadError")));
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

  if (error) return <div className="alert alert-error">{t("sim.notFound", { slug })}</div>;
  if (!sim) return <Spinner />;

  if (isBuiltin) {
    const Component = BUILTIN_SIMS[sim.provider_id];
    if (!Component) return <div className="alert">{t("sim.unknownBuiltin", { id: sim.provider_id })}</div>;
    return (
      <div className="sim-frame">
        <ErrorBoundary compact>
          <Suspense fallback={<Spinner />}>
            <Component />
          </Suspense>
        </ErrorBoundary>
        <div className="sim-caption">
          <span className="with-icon">
            <Icon name="labs" size={14} /> {sim.title} · {t("labs.offline")}
          </span>
        </div>
      </div>
    );
  }

  const embedUrl = frameUrl(sim.embed_url);
  const attribution = sim.provider === "phet" ? t("labs.attributionPhet") : sim.provider === "geogebra" ? t("labs.attributionGeogebra") : sim.provider_label;

  return (
    <div className="sim-frame">
      {!launched ? (
        <div className="sim-placeholder">
          <Icon name={sim.provider === "geogebra" ? "trend" : "flask"} size={40} strokeWidth={1.6} style={{ color: "var(--primary)" }} />
          <strong>{sim.title}</strong>
          <span className="small muted">{t("labs.dataNote")}</span>
          <button className="btn" onClick={() => setLaunched(true)}>
            <Icon name="play" size={16} /> {t("labs.launch")}
          </button>
        </div>
      ) : sim.provider === "geogebra" && !sim.embed_url ? (
        <GeoGebraApp app={sim.provider_id} />
      ) : !embedUrl ? (
        <div className="alert alert-error">{t("sim.notFound", { slug: sim.slug })}</div>
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
