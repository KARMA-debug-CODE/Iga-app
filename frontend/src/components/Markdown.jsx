import "katex/dist/katex.min.css";

import ReactMarkdown from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";

import CodePlayground from "./CodePlayground";
import PythonPlayground from "./PythonPlayground";
import SimEmbed from "./SimEmbed";

function codeBlockInfo(node) {
  const code = node?.children?.[0];
  if (!code || code.tagName !== "code") return null;
  const className = code.properties?.className || [];
  const language = className.find((c) => String(c).startsWith("language-"))?.slice(9);
  const text = (code.children || []).map((c) => c.value || "").join("");
  return { language, text };
}

/**
 * Lesson Markdown with maths ($…$, $$…$$), tables, and two special blocks:
 *   ```sim
 *   projectile-lab
 *   ```
 *   ```playground html
 *   <h1>Hello</h1>
 *   ```
 *   ```python-run
 *   print("Muraho!")
 *   ```
 * Raw HTML in the Markdown is NOT rendered, so content can't inject scripts.
 */
export default function Markdown({ children, sims = {}, interactive = true }) {
  return (
    <div className="prose">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[[rehypeKatex, { throwOnError: false, strict: "ignore" }]]}
        components={{
          pre({ node, children: kids }) {
            const info = codeBlockInfo(node);
            if (interactive && info?.language === "sim") {
              const slug = info.text.trim();
              return <SimEmbed slug={slug} sim={sims[slug]} />;
            }
            if (interactive && info?.language === "playground") {
              return <CodePlayground initialCode={info.text.replace(/\n$/, "")} />;
            }
            if (interactive && info?.language === "python-run") {
              return <PythonPlayground initialCode={info.text.replace(/\n$/, "")} />;
            }
            return <pre>{kids}</pre>;
          },
          a({ href = "", children: kids }) {
            const external = /^https?:\/\//.test(href);
            return (
              <a href={href} {...(external ? { target: "_blank", rel: "noopener noreferrer" } : {})}>
                {kids}
              </a>
            );
          },
        }}
      >
        {children || ""}
      </ReactMarkdown>
    </div>
  );
}
