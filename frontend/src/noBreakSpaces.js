// French typography puts a space before : ; ? ! and » and after «. Lessons are written with ordinary spaces,
// so on a phone a line could start with "; il reste 5 ms". This remark plugin turns those spaces into
// no-break spaces in the text of a lesson (code and maths are other node types, so they stay as written).

const BEFORE = / +([:;?!»])/g;
const AFTER = /« +/g;

export function keepPunctuationAttached(text) {
  return text.replace(BEFORE, " $1").replace(AFTER, "« ");
}

function walk(node) {
  if (node.type === "text") node.value = keepPunctuationAttached(node.value);
  else node.children?.forEach(walk);
}

export default function remarkNoBreakSpaces() {
  return walk;
}
