import Markdown from "../components/Markdown";

/** A short label followed by an answer option, the option drawn as Markdown so its maths shows. */
export default function AnswerLine({ label, text, className = "" }) {
  return (
    <div className={`pack-answer-line ${className}`.trim()}>
      <span>{label}</span>
      <Markdown interactive={false}>{text}</Markdown>
    </div>
  );
}
