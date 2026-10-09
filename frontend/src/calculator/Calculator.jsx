// A calculator in the style of the Windows 11 Calculator app: Standard, Scientific and
// Programmer modes chosen from a menu, with history and memory. Everything runs in the
// browser (no network), and history, memory and settings stay in this browser.
//
// Props: lang ("en" | "fr"); compact (always the narrow layout, and the keyboard only
// works while the calculator has focus, for when it sits inside another page).
import { useEffect, useId, useLayoutEffect, useReducer, useRef, useState } from "react";

import { Icon } from "../components/Icon";
import "./calculator.css";
import { keyFor } from "./engine/keyboard.js";
import * as M from "./engine/machine.js";
import { BASE_NAMES, WORD_NAMES } from "./engine/programmer.js";
import STRINGS from "./strings.js";

const STORAGE = "iga.calc.";

function load(name) {
  try {
    return JSON.parse(localStorage.getItem(STORAGE + name) || "null");
  } catch {
    return null;
  }
}

function store(name, value) {
  try {
    localStorage.setItem(STORAGE + name, JSON.stringify(value));
  } catch {
    // Private windows may refuse storage: the calculator still works, it just forgets.
  }
}

function initial() {
  return M.initMachine(M.fromSaved({ settings: load("settings"), history: load("history"), memory: load("memory") }));
}

function reducer(state, action) {
  switch (action.type) {
    case "press":
      return M.press(state, action.key);
    case "mode":
      return M.setMode(state, action.mode);
    case "base":
      return M.setBase(state, action.base);
    case "bits":
      return M.setBits(state, M.nextBits(state.bits));
    case "memoryItem":
      return M.memoryItem(state, action.op, action.index);
    case "recall":
      return M.recallHistory(state, action.index);
    case "clearHistory":
      return M.clearHistory(state);
    case "paste":
      return M.paste(state, action.text, action.lang);
    default:
      return state;
  }
}

// The menu, as in Windows. Modes that are not built yet are listed but switched off.
const MENU = [
  {
    section: "sectionCalculator",
    items: [
      { id: "standard", icon: "calculator" },
      { id: "scientific", icon: "sigma" },
      { id: "graphing", icon: "graph" },
      { id: "programmer", icon: "binary" },
      { id: "date", icon: "calendar" },
    ],
  },
  {
    section: "sectionConverter",
    items: [
      { id: "currency", icon: "coins" },
      { id: "volume", icon: "beaker" },
      { id: "length", icon: "ruler" },
      { id: "weight", icon: "weight" },
      { id: "temperature", icon: "thermometer" },
      { id: "energy", icon: "flame" },
      { id: "area", icon: "area" },
      { id: "speed", icon: "rocket" },
      { id: "time", icon: "clock" },
      { id: "power", icon: "zap" },
      { id: "data", icon: "database" },
      { id: "pressure", icon: "gauge" },
      { id: "angle", icon: "angle" },
    ],
  },
];

const LAYOUTS = {
  standard: {
    cols: 4,
    keys: ["percent", "ce", "c", "back", "inv", "sqr", "sqrt", "div", "7", "8", "9", "mul", "4", "5", "6", "sub", "1", "2", "3", "add", "neg", "0", "point", "equals"],
  },
  scientific: {
    cols: 5,
    keys: [
      "second", "hyp", "sin", "cos", "tan",
      "pi", "e", "ce", "c", "back",
      "sqr", "inv", "abs", "exp", "mod",
      "sqrt", "open", "close", "fact", "div",
      "pow", "7", "8", "9", "mul",
      "tenx", "4", "5", "6", "sub",
      "log", "1", "2", "3", "add",
      "ln", "neg", "0", "point", "equals",
    ],
  },
  programmer: {
    cols: 5,
    bits: ["and", "or", "xor", "not", "nand", "nor"],
    keys: [
      "A", "lsh", "rsh", "clear", "back",
      "B", "open", "close", "mod", "div",
      "C", "7", "8", "9", "mul",
      "D", "4", "5", "6", "sub",
      "E", "1", "2", "3", "add",
      "F", "neg", "0", "point", "equals",
    ],
  },
};

// The 2nd key swaps these functions, as in Windows.
const SECOND = { sqr: "cube", sqrt: "cbrt", pow: "yroot", tenx: "twox", log: "logy", ln: "ex" };
const MEMORY_LABELS = { mc: "MC", mr: "MR", mplus: "M+", mminus: "M−", ms: "MS" };

const sup = (base, power) => (
  <>
    {base}
    <sup>{power}</sup>
  </>
);

const LABELS = {
  percent: "%",
  ce: "CE",
  c: "C",
  back: <Icon name="backspace" size={20} />,
  inv: "1/x",
  sqr: sup("x", "2"),
  cube: sup("x", "3"),
  sqrt: "√x",
  cbrt: "∛x",
  div: "÷",
  mul: "×",
  sub: "−",
  add: "+",
  equals: "=",
  neg: "+/−",
  hyp: "hyp",
  pi: "π",
  e: "e",
  pow: sup("x", "y"),
  yroot: (
    <>
      <sup>y</sup>√x
    </>
  ),
  tenx: sup("10", "x"),
  twox: sup("2", "x"),
  ex: sup("e", "x"),
  log: "log",
  logy: (
    <>
      log<sub>y</sub>x
    </>
  ),
  ln: "ln",
  fact: "n!",
  abs: "|x|",
  exp: "exp",
  mod: "mod",
  open: "(",
  close: ")",
  and: "AND",
  or: "OR",
  xor: "XOR",
  not: "NOT",
  nand: "NAND",
  nor: "NOR",
  lsh: "Lsh",
  rsh: "Rsh",
};

const isDigitKey = (id) => /^[0-9A-F]$/.test(id) || id === "point" || id === "neg";

/** Is the keyboard busy typing into a text field (the page's search box, for example)? */
function isTextField(el) {
  if (!el || el.nodeType !== 1) return false;
  if (el.isContentEditable || el.tagName === "TEXTAREA" || el.tagName === "SELECT") return true;
  return el.tagName === "INPUT" && !["radio", "checkbox", "button", "submit", "range"].includes(el.type);
}

/** Show which key was pressed on the keyboard, as Windows does. */
function flash(root, key) {
  const button = root?.querySelector(`[data-key="${key}"]`);
  if (!button) return;
  button.classList.add("calc-key-pressed");
  setTimeout(() => button.classList.remove("calc-key-pressed"), 120);
}

function fill(text, vars) {
  return text.replace(/\{(\w+)\}/g, (_, name) => vars[name] ?? "");
}

export default function Calculator({ lang = "en", compact = false }) {
  const t = STRINGS[lang] || STRINGS.en;
  const [state, dispatch] = useReducer(reducer, null, initial);
  const [menuOpen, setMenuOpen] = useState(false);
  const [tab, setTab] = useState("history");
  const [panelOpen, setPanelOpen] = useState(false);
  const rootRef = useRef(null);
  const menuButtonRef = useRef(null);
  const navRef = useRef(null);
  const panelRef = useRef(null);
  const panelOpenerRef = useRef(null);
  const exprRef = useRef(null);
  const live = useRef({ state, lang, menuOpen, panelOpen });
  const uid = useId();

  useLayoutEffect(() => {
    live.current = { state, lang, menuOpen, panelOpen };
  });

  const { mode } = state;
  const calc = state.calcs[mode];
  const kind = M.kindOf(mode);
  const history = state.history[kind];
  const memory = state.memory[kind];
  const error = M.errorOf(state);
  const display = error ? t.errors[error] : M.displayText(state, lang);
  const expression = M.expressionText(state, lang);
  const settings = M.savedSettings(state);
  const settingsKey = JSON.stringify(settings);

  // Keep history, memory and settings in this browser.
  useEffect(() => store("settings", JSON.parse(settingsKey)), [settingsKey]);
  useEffect(() => store("history", M.savedHistory({ history: state.history })), [state.history]);
  useEffect(() => store("memory", M.savedMemory({ memory: state.memory })), [state.memory]);

  // Long expressions scroll so the end (what was just typed) stays visible.
  useLayoutEffect(() => {
    const el = exprRef.current;
    if (el) el.scrollLeft = el.scrollWidth;
  }, [expression]);

  function press(key) {
    dispatch({ type: "press", key });
  }

  /** Give the keyboard back to the calculator, so typing and Enter work straight away. */
  function focusCalculator() {
    rootRef.current?.focus({ preventScroll: true });
  }

  function closeMenu(focusButton = false) {
    setMenuOpen(false);
    if (focusButton) menuButtonRef.current?.focus();
    else focusCalculator();
  }

  function closePanel() {
    setPanelOpen(false);
    if (panelOpenerRef.current) panelOpenerRef.current.focus();
    else focusCalculator();
  }

  function openPanel(which, event) {
    // Opened from the keyboard (detail 0): focus goes back to the button on close. After a tap or a
    // click it goes back to the calculator, so Enter means "=" and does not open the panel again.
    panelOpenerRef.current = event.detail === 0 ? event.currentTarget : null;
    setTab(which);
    setPanelOpen(true);
  }

  // Focus moves into the menu or the panel when it opens.
  useEffect(() => {
    if (menuOpen) navRef.current?.querySelector('[aria-current="true"]')?.focus();
  }, [menuOpen]);
  useEffect(() => {
    if (panelOpen) panelRef.current?.querySelector('[aria-selected="true"]')?.focus();
  }, [panelOpen]);

  // Keyboard, copy and paste, like the Windows calculator.
  useEffect(() => {
    const root = rootRef.current;
    const target = compact ? root : window;
    const ours = (event) => !isTextField(event.target) && (!compact || root.contains(document.activeElement));
    const hasSelection = () => Boolean(window.getSelection?.()?.toString());

    function onKeyDown(event) {
      if (event.defaultPrevented || !ours(event)) return;
      const { state: s, lang: l, menuOpen: menu, panelOpen: panel } = live.current;
      if (event.key === "Escape" && menu) {
        event.preventDefault();
        setMenuOpen(false);
        menuButtonRef.current?.focus();
        return;
      }
      if (event.key === "Escape" && panel && getComputedStyle(panelRef.current).position === "absolute") {
        event.preventDefault();
        setPanelOpen(false);
        (panelOpenerRef.current || root).focus({ preventScroll: true });
        return;
      }
      if (menu) return;
      // Enter and Space on a focused button press that button, not "=" (a chosen base radio still gives "=").
      if ((event.key === "Enter" || event.key === " ") && event.target.closest?.("button, a, [role=tab]")) return;
      if ((event.ctrlKey || event.metaKey) && !event.altKey && event.key.toLowerCase() === "c" && !hasSelection()) {
        // The copy event below fills the clipboard; this covers browsers that send no copy event.
        const text = M.copyText(s, l);
        if (text) navigator.clipboard?.writeText(text).catch(() => {});
        return;
      }
      const key = keyFor(event, s.mode, s.base);
      if (!key) return;
      event.preventDefault();
      flash(root, key);
      dispatch({ type: "press", key });
    }

    function onCopy(event) {
      if (!ours(event) || hasSelection()) return;
      const text = M.copyText(live.current.state, live.current.lang);
      if (!text || !event.clipboardData) return;
      event.clipboardData.setData("text/plain", text);
      event.preventDefault();
    }

    function onPaste(event) {
      if (!ours(event)) return;
      const text = event.clipboardData?.getData("text/plain");
      if (!text) return;
      event.preventDefault();
      dispatch({ type: "paste", text, lang: live.current.lang });
    }

    target.addEventListener("keydown", onKeyDown);
    document.addEventListener("copy", onCopy);
    document.addEventListener("paste", onPaste);
    return () => {
      target.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("copy", onCopy);
      document.removeEventListener("paste", onPaste);
    };
  }, [compact]);

  /** Clicking a key keeps the keyboard on the calculator (so Enter still means "="). */
  function onMouseDown(event) {
    if (!event.target.closest("button")) return;
    event.preventDefault();
    const root = rootRef.current;
    if (!root.contains(document.activeElement)) root.focus({ preventScroll: true });
  }

  function keyId(id) {
    if (id === "clear") return calc.entry !== null && !calc.error ? "ce" : "c";
    if (mode !== "scientific") return id;
    if (["sin", "cos", "tan"].includes(id)) return `${state.second ? "a" : ""}${id}${state.hyp ? "h" : ""}`;
    return state.second && SECOND[id] ? SECOND[id] : id;
  }

  function label(id) {
    if (id === "point") return lang === "fr" ? "," : ".";
    if (id === "second") return lang === "fr" ? sup("2", "nde") : sup("2", "nd");
    const trig = /^(a?)(sin|cos|tan)(h?)$/.exec(id);
    if (trig) return trig[1] ? sup(trig[2] + trig[3], "−1") : trig[2] + trig[3];
    return LABELS[id] ?? id;
  }

  function renderKey(slot) {
    const id = keyId(slot);
    const enabled = M.isEnabled(state, id);
    const toggle = id === "second" || id === "hyp";
    const on = toggle && state[id];
    const parens = id === "open" ? M.openParens(state) : 0;
    let aria = t.keys[id];
    if (parens) aria = `${aria}, ${fill(t.openBrackets, { n: parens })}`;
    const classes = [
      "calc-key",
      isDigitKey(id) ? "calc-key-digit" : "calc-key-fn",
      id === "equals" ? "calc-key-equals" : "",
      on ? "calc-key-on" : "",
      /^[A-F]$/.test(id) ? "calc-key-hex" : "",
    ];
    return (
      <button
        key={slot}
        type="button"
        className={classes.filter(Boolean).join(" ")}
        data-key={id}
        aria-label={aria}
        aria-pressed={toggle ? on : undefined}
        aria-disabled={enabled ? undefined : true}
        onClick={() => enabled && press(id)}
      >
        {label(id)}
        {parens > 0 && <sub className="calc-paren-count">{parens}</sub>}
      </button>
    );
  }

  const layout = LAYOUTS[mode];
  const tabs = [
    { id: "history", label: t.history },
    { id: "memory", label: t.memory },
  ];

  function onTabKey(event) {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    event.preventDefault();
    const next = tab === "history" ? "memory" : "history";
    setTab(next);
    panelRef.current?.querySelector(`#${CSS.escape(`${uid}-tab-${next}`)}`)?.focus();
  }

  const displayLength = (display || "").length;

  return (
    <section
      ref={rootRef}
      className={`calc calc-mode-${mode} ${compact ? "calc-compact" : ""} ${menuOpen ? "calc-menu-open" : ""}`}
      aria-label={t.title}
      tabIndex={-1}
      onMouseDown={onMouseDown}
    >
      <div className="calc-shell">
        <div className="calc-main">
          <div className="calc-bar">
            <button
              ref={menuButtonRef}
              type="button"
              className="calc-icon-btn"
              aria-label={menuOpen ? t.closeMenu : t.openMenu}
              aria-expanded={menuOpen}
              aria-controls={`${uid}-nav`}
              onClick={(event) => (menuOpen ? closeMenu(event.detail === 0) : setMenuOpen(true))}
            >
              <Icon name="menu" size={20} />
            </button>
            <h2 className="calc-title">{t.modes[mode]}</h2>
            <button type="button" className="calc-icon-btn calc-narrow-only" aria-label={t.showHistory} onClick={(e) => openPanel("history", e)}>
              <Icon name="history" size={20} />
            </button>
          </div>

          {menuOpen && (
            <>
              <div className="calc-scrim" onClick={() => closeMenu()} aria-hidden="true" />
              <nav
                ref={navRef}
                id={`${uid}-nav`}
                className="calc-nav"
                aria-label={t.menu}
                onBlur={(event) => {
                  // Tabbing out of the menu closes it.
                  const next = event.relatedTarget;
                  if (next && !navRef.current.contains(next) && next !== menuButtonRef.current) setMenuOpen(false);
                }}
              >
                {MENU.map((group) => (
                  <div key={group.section} className="calc-nav-group">
                    <h3 className="calc-nav-heading">{t[group.section]}</h3>
                    <ul>
                      {group.items.map((item) => {
                        const ready = M.MODES.includes(item.id);
                        return (
                          <li key={item.id}>
                            <button
                              type="button"
                              className="calc-nav-item"
                              aria-current={item.id === mode ? "true" : undefined}
                              disabled={!ready}
                              onClick={() => {
                                dispatch({ type: "mode", mode: item.id });
                                closeMenu();
                              }}
                            >
                              <Icon name={item.icon} size={18} />
                              <span>{t.modes[item.id]}</span>
                              {!ready && <span className="calc-soon">{t.soon}</span>}
                            </button>
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                ))}
              </nav>
            </>
          )}

          <div className="calc-display">
            <div className="calc-expr" ref={exprRef}>
              {expression && <span className="sr-only">{t.expressionIs} </span>}
              {expression}
            </div>
            <div
              className={`calc-value ${error ? "is-error" : ""}`}
              role="status"
              aria-live="polite"
              aria-atomic="true"
              style={{ "--calc-len": Math.max(displayLength, 8) }}
            >
              <span className="sr-only">{t.displayIs} </span>
              {display}
            </div>
          </div>

          {mode === "programmer" && (
            <fieldset className="calc-bases">
              <legend className="sr-only">{t.baseGroup}</legend>
              {M.baseValues(state, lang).map(({ base, text }) => (
                <label key={base} className={`calc-base ${state.base === base ? "is-selected" : ""}`}>
                  <input
                    type="radio"
                    className="calc-base-input"
                    name={`${uid}-base`}
                    checked={state.base === base}
                    onChange={() => dispatch({ type: "base", base })}
                    aria-label={`${t.bases[base]} (${BASE_NAMES[base]}) ${text}`}
                  />
                  <span className="calc-base-name" aria-hidden="true">
                    {BASE_NAMES[base]}
                  </span>
                  <span className="calc-base-value" aria-hidden="true">
                    {text}
                  </span>
                </label>
              ))}
            </fieldset>
          )}

          {mode === "scientific" && (
            <div className="calc-toolbar">
              <button
                type="button"
                className="calc-flat"
                data-key="angle"
                aria-label={fill(t.angleKey, { unit: t.angles[state.angle] })}
                onClick={() => press("angle")}
              >
                {state.angle.toUpperCase()}
              </button>
              <button type="button" className="calc-flat" data-key="fe" aria-pressed={state.fe} aria-label={t.fe} onClick={() => press("fe")}>
                F-E
              </button>
            </div>
          )}

          <div className="calc-toolbar">
            {mode === "programmer" && (
              // The word size shares the memory row, as in Windows.
              <button
                type="button"
                className="calc-flat calc-word"
                aria-label={fill(t.wordKey, { name: WORD_NAMES[state.bits], bits: state.bits })}
                onClick={() => dispatch({ type: "bits" })}
              >
                {WORD_NAMES[state.bits]}
              </button>
            )}
            <div className="calc-memrow" role="group" aria-label={t.memory}>
              {M.MEMORY_KEYS.map((id) => {
                const enabled = M.isEnabled(state, id);
                return (
                  <button
                    key={id}
                    type="button"
                    className="calc-flat"
                    data-key={id}
                    aria-label={t.keys[id]}
                    aria-disabled={enabled ? undefined : true}
                    onClick={() => enabled && press(id)}
                  >
                    {MEMORY_LABELS[id]}
                  </button>
                );
              })}
              <button
                type="button"
                className="calc-flat calc-narrow-only"
                aria-label={t.showMemory}
                onClick={(e) => openPanel("memory", e)}
              >
                M<Icon name="chevronDown" size={14} />
              </button>
            </div>
          </div>

          {layout.bits && (
            <div className="calc-keys calc-keys-bits" role="group" aria-label={t.bitwise}>
              {layout.bits.map(renderKey)}
            </div>
          )}
          <div className="calc-keys" role="group" aria-label={t.keypad} style={{ "--calc-cols": layout.cols }}>
            {layout.keys.map(renderKey)}
          </div>
        </div>

        {panelOpen && <div className="calc-scrim calc-scrim-panel" onClick={closePanel} aria-hidden="true" />}
        <aside
          ref={panelRef}
          className={`calc-side ${panelOpen ? "is-open" : ""}`}
          aria-label={`${t.history}, ${t.memory}`}
          onBlur={(event) => {
            // On phones, tabbing out of the panel closes it (as with the menu).
            const next = event.relatedTarget;
            if (panelOpen && next && !panelRef.current.contains(next)) setPanelOpen(false);
          }}
        >
          <div className="calc-side-head">
            <div className="calc-tabs" role="tablist" onKeyDown={onTabKey}>
              {tabs.map((item) => (
                <button
                  key={item.id}
                  id={`${uid}-tab-${item.id}`}
                  type="button"
                  role="tab"
                  className="calc-tab"
                  aria-selected={tab === item.id}
                  aria-controls={`${uid}-panel`}
                  tabIndex={tab === item.id ? 0 : -1}
                  onClick={() => setTab(item.id)}
                >
                  {item.label}
                </button>
              ))}
            </div>
            <button type="button" className="calc-icon-btn calc-narrow-only" aria-label={t.closePanel} onClick={closePanel}>
              <Icon name="close" size={20} />
            </button>
          </div>

          <div className="calc-side-body" id={`${uid}-panel`} role="tabpanel" aria-labelledby={`${uid}-tab-${tab}`}>
            {tab === "history" &&
              (history.length ? (
                <ul className="calc-list">
                  {history.map((item, index) => (
                    // History entries are only ever added at the front, so the index is stable enough here.
                    <li key={`${history.length - index}`}>
                      <button
                        type="button"
                        className="calc-item"
                        onClick={() => {
                          dispatch({ type: "recall", index });
                          if (panelOpen) closePanel();
                        }}
                      >
                        <span className="calc-item-expr">{M.expressionText(state, lang, item.parts)}</span>
                        <span className="calc-item-value">{M.formatValue(state, item.value, lang)}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="calc-empty">{t.noHistory}</p>
              ))}
            {tab === "memory" &&
              (memory.length ? (
                <ul className="calc-list">
                  {memory.map((value, index) => {
                    const text = M.formatValue(state, value, lang);
                    return (
                      <li key={`${memory.length - index}`} className="calc-memory-item">
                        <button
                          type="button"
                          className="calc-item"
                          aria-label={fill(t.useItem, { value: text })}
                          onClick={() => {
                            dispatch({ type: "memoryItem", op: "recall", index });
                            if (panelOpen) closePanel();
                          }}
                        >
                          <span className="calc-item-value">{text}</span>
                        </button>
                        <div className="calc-item-actions">
                          {[
                            ["clear", "MC", t.itemClear],
                            ["add", "M+", t.itemAdd],
                            ["sub", "M−", t.itemSub],
                          ].map(([op, short, aria]) => (
                            <button
                              key={op}
                              type="button"
                              className="calc-flat calc-item-btn"
                              aria-label={aria}
                              aria-disabled={op !== "clear" && error ? true : undefined}
                              onClick={() => dispatch({ type: "memoryItem", op, index })}
                            >
                              {short}
                            </button>
                          ))}
                        </div>
                      </li>
                    );
                  })}
                </ul>
              ) : (
                <p className="calc-empty">{t.noMemory}</p>
              ))}
          </div>

          {(tab === "history" ? history.length : memory.length) > 0 && (
            <div className="calc-side-foot">
              <button
                type="button"
                className="calc-icon-btn"
                aria-label={tab === "history" ? t.clearHistory : t.clearMemory}
                title={tab === "history" ? t.clearHistory : t.clearMemory}
                onClick={() => (tab === "history" ? dispatch({ type: "clearHistory" }) : press("mc"))}
              >
                <Icon name="trash" size={18} />
              </button>
            </div>
          )}
        </aside>
      </div>
    </section>
  );
}

