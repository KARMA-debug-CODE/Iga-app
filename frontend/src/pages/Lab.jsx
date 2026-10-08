import { Link, useParams } from "react-router-dom";

import { Icon } from "../components/Icon";
import SimEmbed from "../components/SimEmbed";
import { Loader } from "../components/ui";
import { useApi } from "../hooks";
import { useI18n } from "../i18n";

export default function Lab() {
  const { slug } = useParams();
  const { t, lang } = useI18n();
  const state = useApi(`/simulations/${slug}/`, { params: { lang } });
  return (
    <Loader state={state}>
      {(sim) => (
        <div style={{ maxWidth: 960 }}>
          <div className="breadcrumb">
            <Link to="/labs">{t("labs.title")}</Link> <span>›</span> <span>{sim.title}</span>
          </div>
          <h1>{sim.title}</h1>
          {sim.description && <p className="muted">{sim.description}</p>}
          <SimEmbed slug={sim.slug} sim={sim} />
          <div className="grid-2 section">
            {sim.learning_goals && (
              <div className="card">
                <h2 className="title-with-icon">
                  <Icon name="target" /> {t("labs.goals")}
                </h2>
                <p style={{ margin: 0 }}>{sim.learning_goals}</p>
              </div>
            )}
            {sim.lessons.length > 0 && (
              <div className="card">
                <h2 className="title-with-icon">
                  <Icon name="learn" /> {t("labs.related")}
                </h2>
                <ul className="list">
                  {sim.lessons.map((l) => (
                    <li key={l.slug}>
                      <Link to={`/lessons/${l.slug}`}>{l.title}</Link>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </Loader>
  );
}
