import "katex/dist/katex.min.css";

import ReactMarkdown from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";

import remarkNoBreakSpaces from "../noBreakSpaces";
import CodePlayground from "./CodePlayground";
import PythonPlayground from "./PythonPlayground";
import SimEmbed from "./SimEmbed";

// A path on this site: "/x", but not "//host" or "/\host", which browsers read as another site.
const SAME_SITE = /^\/(?![/\\])/;
// Another site or app: a scheme ("https:", "mailto:"), "//host" or "/\host".
const OTHER_SITE = /^(?:[a-z][a-z0-9+.-]*:|\/[/\\])/i;

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
 * Raw HTML in the Markdown is NOT rendered (it shows as text), so content can't inject scripts, and
 * react-markdown drops unsafe link targets (javascript:, data:, vbscript: ...). With interactive={false},
 * for text people write, pictures from other sites become links.
 */
export default function Markdown({ children, sims = {}, interactive = true }) {
  return (
    <div className="prose">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath, remarkNoBreakSpaces]}
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
            // Links out open in a new tab that can't reach or redirect this page.
            const external = OTHER_SITE.test(href);
            return (
              <a href={href} {...(external ? { target: "_blank", rel: "noopener noreferrer" } : {})}>
                {kids}
              </a>
            );
          },
          img({ src = "", alt = "" }) {
            // People's text (shared notes, Santa's answers, questions) shows no pictures from other sites:
            // loading one would tell that site who is reading, and could put anything in front of a class.
            // It becomes a link the reader may choose to open. Lessons, reviewed before they are published,
            // may show pictures.
            if (!interactive && !SAME_SITE.test(src)) {
              return src ? (
                <a href={src} target="_blank" rel="noopener noreferrer">
                  {alt || src}
                </a>
              ) : (
                alt
              );
            }
            return <img src={src} alt={alt} loading="lazy" referrerPolicy="no-referrer" />;
          },
        }}
      >
        {children || ""}
      </ReactMarkdown>
    </div>
  );
}
