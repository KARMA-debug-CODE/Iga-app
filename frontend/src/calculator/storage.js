// What the calculator keeps in this browser, under localStorage keys "iga.calc.<name>".
// Storage can be missing or refuse to save (private windows): the calculator then
// still works, it just forgets.
const PREFIX = "iga.calc.";

export function load(name) {
  try {
    return JSON.parse(localStorage.getItem(PREFIX + name) || "null");
  } catch {
    return null;
  }
}

export function store(name, value) {
  try {
    localStorage.setItem(PREFIX + name, JSON.stringify(value));
  } catch {
    // Nothing to do: see above.
  }
}
