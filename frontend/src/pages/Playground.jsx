import { useState } from "react";

import CodePlayground from "../components/CodePlayground";
import PythonPlayground from "../components/PythonPlayground";
import RemotePlayground from "../components/RemotePlayground";
import SqlPlayground from "../components/SqlPlayground";
import { Tabs } from "../components/ui";
import { useI18n } from "../i18n";

import cppEn from "../playground-starters/cpp.en.cpp?raw";
import cppFr from "../playground-starters/cpp.fr.cpp?raw";
import javaEn from "../playground-starters/java.en.java?raw";
import javaFr from "../playground-starters/java.fr.java?raw";
import pythonEn from "../playground-starters/python.en.py?raw";
import pythonFr from "../playground-starters/python.fr.py?raw";
import sqlEn from "../playground-starters/sql.en.sql?raw";
import sqlFr from "../playground-starters/sql.fr.sql?raw";
import webEn from "../playground-starters/web.en.html?raw";
import webFr from "../playground-starters/web.fr.html?raw";

// Starter programs in the reader's language, so they name the buttons and words they actually see.
// They are separate files so coderunner/test_server.py can compile and run the C++ and Java ones.
const STARTERS = {
  web: { en: webEn, fr: webFr },
  python: { en: pythonEn, fr: pythonFr },
  cpp: { en: cppEn, fr: cppFr },
  java: { en: javaEn, fr: javaFr },
  sql: { en: sqlEn, fr: sqlFr },
};
const starter = (kind, lang) => STARTERS[kind][lang] || STARTERS[kind].en;

export default function Playground() {
  const { t, lang } = useI18n();
  const [tab, setTab] = useState("web");
  return (
    <>
      <div className="page-header">
        <h1>{t("nav.playground")}</h1>
        <p>{t("python.pageIntro")}</p>
      </div>
      <Tabs
        value={tab}
        onChange={setTab}
        tabs={[
          { value: "web", label: "HTML · CSS · JS" },
          { value: "python", label: "Python" },
          { value: "cpp", label: "C++" },
          { value: "java", label: "Java" },
          { value: "sql", label: "SQL" },
        ]}
      />
      {tab === "web" && <CodePlayground initialCode={starter("web", lang)} height={420} />}
      {tab === "python" && <PythonPlayground initialCode={starter("python", lang)} height={380} />}
      {tab === "cpp" && (
        <RemotePlayground key={`cpp-${lang}`} language="cpp" initialCode={starter("cpp", lang)} height={380} />
      )}
      {tab === "java" && (
        <RemotePlayground key={`java-${lang}`} language="java" initialCode={starter("java", lang)} height={380} />
      )}
      {tab === "sql" && <SqlPlayground key={lang} initialCode={starter("sql", lang)} height={380} />}
    </>
  );
}
