import CodePlayground from "../components/CodePlayground";
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

export default function Playground() {
  const { t } = useI18n();
  return (
    <>
      <div className="page-header">
        <h1>💻 {t("nav.playground")}</h1>
        <p>HTML · CSS · JavaScript</p>
      </div>
      <CodePlayground initialCode={STARTER} height={420} />
    </>
  );
}
