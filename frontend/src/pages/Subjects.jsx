import { useSearchParams } from "react-router-dom";

import { useAuth } from "../auth";
import { GradeChips, Loader } from "../components/ui";
import { useApi } from "../hooks";
import { useI18n } from "../i18n";
import { SubjectCard } from "./Dashboard";

export default function Subjects() {
  const { user } = useAuth();
  const { t, lang } = useI18n();
  const [params, setParams] = useSearchParams();
  const grade = params.get("grade") || user.grade || "S1";
  const state = useApi("/subjects/", { params: { grade, lang } });

  return (
    <>
      <div className="page-header">
        <h1>{t("learn.subjects")}</h1>
        <p>{t("app.tagline")}</p>
      </div>
      <GradeChips value={grade} onChange={(g) => setParams({ grade: g })} />
      <div style={{ marginTop: 16 }}>
        <Loader state={state}>
          {(list) => (
            <div className="grid">
              {list.map((s) => (
                <SubjectCard key={s.code} subject={s} grade={grade} />
              ))}
            </div>
          )}
        </Loader>
      </div>
    </>
  );
}
