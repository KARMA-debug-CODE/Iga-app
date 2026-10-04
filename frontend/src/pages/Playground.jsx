import { useState } from "react";

import CodePlayground from "../components/CodePlayground";
import PythonPlayground from "../components/PythonPlayground";
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
        ]}
      />
      {tab === "web" ? (
        <CodePlayground initialCode={STARTERS[lang] || STARTERS.en} height={420} />
      ) : (
        <PythonPlayground initialCode={PY_STARTERS[lang] || PY_STARTERS.en} height={380} />
      )}
    </>
  );
}
