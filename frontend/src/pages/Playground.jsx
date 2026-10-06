import { useState } from "react";

import CodePlayground from "../components/CodePlayground";
import PythonPlayground from "../components/PythonPlayground";
import SqlPlayground from "../components/SqlPlayground";
import { Tabs } from "../components/ui";
import { useI18n } from "../i18n";

// Starter code in the reader's language, so it names the buttons they actually see.
const STARTERS = {
  en: `<!DOCTYPE html>
<html lang="en">
<head>
<style>
  body { font-family: system-ui, sans-serif; padding: 20px; }
  h1 { color: #00A1DE; }
  button { background: #20603D; color: white; border: 0; padding: 10px 16px; border-radius: 8px; }
</style>
</head>
<body>
  <h1>Hello, Rwanda! 🇷🇼</h1>
  <p>Edit this code and press Run.</p>
  <button onclick="count++; this.textContent = 'Clicked ' + count + ' times'">Click me</button>
  <script>
    let count = 0;
  </script>
</body>
</html>`,
  fr: `<!DOCTYPE html>
<html lang="fr">
<head>
<style>
  body { font-family: system-ui, sans-serif; padding: 20px; }
  h1 { color: #00A1DE; }
  button { background: #20603D; color: white; border: 0; padding: 10px 16px; border-radius: 8px; }
</style>
</head>
<body>
  <h1>Bonjour, Rwanda ! 🇷🇼</h1>
  <p>Modifiez ce code et appuyez sur Exécuter.</p>
  <button onclick="count++; this.textContent = 'Cliqué ' + count + ' fois'">Cliquez-moi</button>
  <script>
    let count = 0;
  </script>
</body>
</html>`,
};

const PY_STARTERS = {
  en: `# Iga Python playground — press Run (or Ctrl+Enter)
name = input("What is your name? ")
print(f"Muraho, {name}!")

marks = [72, 85, 64, 90]
average = sum(marks) / len(marks)
print("Average mark:", round(average, 1))

for m in marks:
    print(m, "pass" if m >= 50 else "try again")
`,
  fr: `# Atelier Python d'Iga — appuyez sur Exécuter (ou Ctrl+Entrée)
nom = input("Comment vous appelez-vous ? ")
print(f"Muraho, {nom} !")

notes = [72, 85, 64, 90]
moyenne = sum(notes) / len(notes)
print("Note moyenne :", round(moyenne, 1))

for n in notes:
    print(n, "réussi" if n >= 50 else "à retravailler")
`,
};

const SQL_STARTERS = {
  en: `-- Iga SQL playground: press Run (or Ctrl+Enter)
CREATE TABLE students (id INTEGER PRIMARY KEY, name TEXT, grade TEXT, district TEXT);
CREATE TABLE marks (student_id INTEGER, subject TEXT, mark INTEGER);

INSERT INTO students VALUES
  (1, 'Aline', 'S2', 'Gasabo'),
  (2, 'Eric', 'S2', 'Huye'),
  (3, 'Grace', 'S3', 'Musanze'),
  (4, 'Jean', 'S3', 'Gasabo');

INSERT INTO marks VALUES
  (1, 'Mathematics', 78), (1, 'Physics', 64),
  (2, 'Mathematics', 55), (2, 'Physics', 71),
  (3, 'Mathematics', 90), (4, 'Physics', 48);

-- Who lives in Gasabo?
SELECT name, grade FROM students WHERE district = 'Gasabo';

-- Each student's average mark, best first
SELECT s.name, ROUND(AVG(m.mark), 1) AS average
FROM students s JOIN marks m ON m.student_id = s.id
GROUP BY s.id
ORDER BY average DESC;
`,
  fr: `-- Atelier SQL d'Iga : appuyez sur Exécuter (ou Ctrl+Entrée)
CREATE TABLE eleves (id INTEGER PRIMARY KEY, nom TEXT, classe TEXT, district TEXT);
CREATE TABLE notes (eleve_id INTEGER, matiere TEXT, note INTEGER);

INSERT INTO eleves VALUES
  (1, 'Aline', 'S2', 'Gasabo'),
  (2, 'Eric', 'S2', 'Huye'),
  (3, 'Grace', 'S3', 'Musanze'),
  (4, 'Jean', 'S3', 'Gasabo');

INSERT INTO notes VALUES
  (1, 'Mathématiques', 78), (1, 'Physique', 64),
  (2, 'Mathématiques', 55), (2, 'Physique', 71),
  (3, 'Mathématiques', 90), (4, 'Physique', 48);

-- Qui habite à Gasabo ?
SELECT nom, classe FROM eleves WHERE district = 'Gasabo';

-- La moyenne de chaque élève, de la meilleure à la moins bonne
SELECT e.nom, ROUND(AVG(n.note), 1) AS moyenne
FROM eleves e JOIN notes n ON n.eleve_id = e.id
GROUP BY e.id
ORDER BY moyenne DESC;
`,
};

export default function Playground() {
  const { t, lang } = useI18n();
  const [tab, setTab] = useState("web");
  return (
    <>
      <div className="page-header">
        <h1>💻 {t("nav.playground")}</h1>
        <p>{t("python.pageIntro")}</p>
      </div>
      <Tabs
        value={tab}
        onChange={setTab}
        tabs={[
          { value: "web", label: "🌐 HTML · CSS · JS" },
          { value: "python", label: "🐍 Python" },
          { value: "sql", label: "🗃️ SQL" },
        ]}
      />
      {tab === "web" && <CodePlayground initialCode={STARTERS[lang] || STARTERS.en} height={420} />}
      {tab === "python" && <PythonPlayground initialCode={PY_STARTERS[lang] || PY_STARTERS.en} height={380} />}
      {tab === "sql" && <SqlPlayground key={lang} initialCode={SQL_STARTERS[lang] || SQL_STARTERS.en} height={380} />}
    </>
  );
}
