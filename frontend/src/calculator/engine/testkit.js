// Helpers for the engine tests: press a list of keys and read what the calculator shows.
import { displayText, errorOf, expressionText, initMachine, press, setMode } from "./machine.js";

/** Keys separated by spaces; a number like "12.5" is typed digit by digit. */
export function keys(text, state = initMachine()) {
  let s = state;
  for (const token of text.trim().split(/\s+/)) {
    if (/^[0-9.]+$/.test(token) && token !== ".") {
      for (const ch of token) s = press(s, ch === "." ? "point" : ch);
    } else s = press(s, token);
  }
  return s;
}

export function inMode(mode, settings = {}) {
  return setMode({ ...initMachine(), ...settings }, mode);
}

/** What the big display shows: the number, or the error code. */
export function shows(state, lang = "en") {
  return errorOf(state) ?? displayText(state, lang);
}

export function expr(state, lang = "en") {
  return expressionText(state, lang);
}
