// Unit converters, like the Windows calculator: two linked value boxes, each with its unit,
// a swap button, "About equal to" in a few other units, and a keypad. Typing in either box
// (or with the keypad, into the box last chosen) converts into the other one.
import { useEffect, useId, useLayoutEffect, useRef, useState } from "react";

import { Icon } from "../components/Icon";
import "./converter.css";
import { formatDecimal, formatEntry, parseDecimalText } from "./engine/format.js";
import { decimalEntry } from "./engine/standard.js";
import { CATEGORIES, alsoUnits, convert, hasUnit } from "./engine/units.js";
import { load, store } from "./storage.js";

const ENTRY = decimalEntry(16);
const KEYS = ["ce", "back", "7", "8", "9", "4", "5", "6", "1", "2", "3", "neg", "0", "point"];
const ABOUT_DIGITS = 6; // significant digits under "About equal to": 1,660,030 in, not 1.66003e+6

function fill(text, vars) {
  return text.replace(/\{(\w+)\}/g, (_, name) => vars[name] ?? "");
}

function savedUnits() {
  const saved = load("units");
  return saved && typeof saved === "object" && !Array.isArray(saved) ? saved : {};
}

/** The two units last used in this category, or its usual pair. */
function initialUnits(category) {
  const pair = savedUnits()[category];
  if (pair && hasUnit(category, pair.from) && hasUnit(category, pair.to)) return { from: pair.from, to: pair.to };
  const [from, to] = CATEGORIES[category].pair;
  return { from, to };
}

export default function ConverterMode({ category, t, lang, keysRef }) {
  const cat = CATEGORIES[category];
  const names = t.units[category];
  const uid = useId();
  const [units, setUnits] = useState(() => initialUnits(category));
  const [active, setActive] = useState("from");
  const [text, setText] = useState("0");

  useEffect(() => {
    store("units", { ...savedUnits(), [category]: units });
  }, [category, units]);

  const other = active === "from" ? "to" : "from";
  const name = (unit) => names[unit][0];
  const label = (unit) => (names[unit][1] ? `${names[unit][0]} (${names[unit][1]})` : names[unit][0]);
  const symbol = (unit) => names[unit][1] || names[unit][0].toLowerCase();

  // The number typed in the active box, converted into the other one.
  let value = null;
  let result = null;
  let problem = null;
  if (text.trim() !== "") {
    const entry = parseDecimalText(text, lang);
    if (entry === null) problem = "typeNumber";
    else {
      try {
        value = ENTRY.parse(entry);
        result = convert(category, units[active], units[other], value);
      } catch {
        value = null;
        problem = "tooBig";
      }
    }
  }
  const shown = { [active]: text, [other]: result ? formatDecimal(result, { lang }) : "" };

  const about = [];
  if (value !== null && result) {
    for (const unit of alsoUnits(category, units.from, units.to)) {
      try {
        const rounded = convert(category, units[active], unit, value).toSignificantDigits(ABOUT_DIGITS);
        about.push(`${formatDecimal(rounded, { lang })} ${symbol(unit)}`);
      } catch {
        // Too large in that unit: leave it out.
      }
    }
  }

  function activate(side) {
    if (side === active) return;
    setText(shown[side]);
    setActive(side);
  }

  function press(key) {
    if (key === "neg" && !cat.signed) return;
    const current = parseDecimalText(text, lang) ?? "0";
    let next = current;
    if (/^[0-9]$/.test(key)) next = ENTRY.appendDigit(current, key) ?? current;
    else if (key === "point") next = ENTRY.appendPoint(current) ?? current;
    else if (key === "back") next = ENTRY.backspace(current);
    else if (key === "ce") next = "0";
    else if (key === "neg") next = ENTRY.negateEntry(current) ?? current;
    setText(formatEntry(next, lang));
  }

  // Keys, paste and copy from Calculator.jsx (when no text box has the keyboard).
  const live = useRef(null);
  useLayoutEffect(() => {
    live.current = { press, text: result ? formatDecimal(result, { lang, grouping: false }) : "" };
  });
  useEffect(() => {
    keysRef.current = {
      keyFor(event) {
        if (event.ctrlKey || event.metaKey || event.altKey) return null;
        if (/^[0-9]$/.test(event.key)) return event.key;
        const keys = { ".": "point", ",": "point", Backspace: "back", Escape: "ce", Delete: "ce", F9: "neg" };
        return keys[event.key] ?? null;
      },
      press: (key) => live.current.press(key),
      paste(pasted) {
        const entry = parseDecimalText(pasted, lang);
        if (entry === null) return false;
        setText(formatEntry(entry, lang));
        return true;
      },
      copy: () => live.current.text,
    };
    return () => {
      keysRef.current = null;
    };
  }, [keysRef, lang]);

  function box(side) {
    const id = `${uid}-${side}`;
    const isActive = side === active;
    return (
      <div className="calc-conv-box">
        <input
          id={id}
          className={`calc-conv-value ${isActive ? "is-active" : ""}`}
          type="text"
          inputMode="decimal"
          autoComplete="off"
          spellCheck={false}
          value={shown[side]}
          style={{ "--calc-len": Math.max(shown[side].length, 8) }}
          aria-label={fill(t.conv.valueIn, { unit: name(units[side]) })}
          aria-invalid={isActive && problem ? true : undefined}
          aria-describedby={isActive && problem ? `${uid}-problem` : undefined}
          onFocus={() => activate(side)}
          onChange={(event) => {
            setActive(side);
            setText(event.target.value);
          }}
        />
        <span className="calc-conv-unit">
          <select
            value={units[side]}
            aria-label={side === "from" ? t.conv.from : t.conv.to}
            onChange={(event) => setUnits({ ...units, [side]: event.target.value })}
          >
            {cat.units.map((unit) => (
              <option key={unit} value={unit}>
                {label(unit)}
              </option>
            ))}
          </select>
          <Icon name="chevronDown" size={16} />
        </span>
      </div>
    );
  }

  return (
    <div className="calc-conv">
      <div className="calc-conv-values">
        {box("from")}
        <div className="calc-conv-swap-row">
          <button
            type="button"
            className="calc-icon-btn calc-conv-swap"
            aria-label={t.conv.swap}
            title={t.conv.swap}
            onClick={() => setUnits({ from: units.to, to: units.from })}
          >
            <Icon name="swap" size={20} />
          </button>
        </div>
        {box("to")}
        <p id={`${uid}-problem`} className="calc-conv-problem" aria-live="polite">
          {problem ? t.conv[problem] : ""}
        </p>
        {about.length > 0 && (
          <div className="calc-conv-about">
            <span>{t.conv.about}</span>
            <ul>
              {about.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </div>
        )}
        <p className="sr-only" aria-live="polite">
          {result ? fill(t.conv.equation, { from: shown.from, fromUnit: name(units.from), to: shown.to, toUnit: name(units.to) }) : ""}
        </p>
      </div>

      <div className="calc-keys calc-conv-keys" role="group" aria-label={t.keypad}>
        {KEYS.map((key) => {
          const disabled = key === "neg" && !cat.signed;
          const digit = /^[0-9]$/.test(key) || key === "point" || key === "neg";
          let content = key;
          if (key === "back") content = <Icon name="backspace" size={20} />;
          else if (key === "ce") content = "CE";
          else if (key === "neg") content = "+/−";
          else if (key === "point") content = lang === "fr" ? "," : ".";
          return (
            <button
              key={key}
              type="button"
              className={`calc-key ${digit ? "calc-key-digit" : "calc-key-fn"} ${key === "ce" ? "calc-conv-ce" : ""}`}
              data-key={key}
              aria-label={t.keys[key] ?? key}
              aria-disabled={disabled ? true : undefined}
              onClick={() => !disabled && press(key)}
            >
              {content}
            </button>
          );
        })}
      </div>
    </div>
  );
}
