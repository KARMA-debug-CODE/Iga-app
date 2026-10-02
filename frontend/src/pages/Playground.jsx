import { useState } from "react";

import CodePlayground from "../components/CodePlayground";
import PythonPlayground from "../components/PythonPlayground";
import { Tabs } from "../components/ui";
import { useI18n } from "../i18n";

const STARTER = `<!DOCTYPE html>
<html>
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
</html>`;

const PY_STARTER = `# Iga Python playground — press Run (or Ctrl+Enter)
name = input("What is your name? ")
print(f"Muraho, {name}!")

marks = [72, 85, 64, 90]
average = sum(marks) / len(marks)
print("Average mark:", round(average, 1))

for m in marks:
    print(m, "pass" if m >= 50 else "try again")
`;

export default function Playground() {
  const { t } = useI18n();
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
      {tab === "web" ? <CodePlayground initialCode={STARTER} height={420} /> : <PythonPlayground initialCode={PY_STARTER} height={380} />}
    </>
  );
}
