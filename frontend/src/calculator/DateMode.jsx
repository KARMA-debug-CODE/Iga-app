// Date calculation, like the Windows calculator: the difference between two dates, or a
// date plus or minus some years, months and days. The maths is in engine/dates.js.
import { Fragment, useId, useState } from "react";

import "./datecalc.css";
import { addToDate, dateDifference, parseISO, toISO, today } from "./engine/dates.js";

const LOCALES = { en: "en-GB", fr: "fr-FR" };
const MAX_AMOUNT = 999;

/** "Friday, 9 October 2026" / "vendredi 9 octobre 2026", for any year from 1 to 9999. */
function longDate({ y, m, d }, lang) {
  const date = new Date(0);
  date.setUTCFullYear(y, m - 1, d);
  return new Intl.DateTimeFormat(LOCALES[lang] || LOCALES.en, {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(date);
}

/** "1 year", "2 weeks"; French uses the singular for 0 and 1 ("0 jour"). */
function count(n, [one, many], lang) {
  const singular = lang === "fr" ? n < 2 : n === 1;
  return `${new Intl.NumberFormat(LOCALES[lang] || LOCALES.en).format(n)} ${singular ? one : many}`;
}

/** A whole number from 0 to 999 typed in an amount box (anything else counts as 0). */
function amount(text) {
  const n = Number.parseInt(text, 10);
  return Number.isFinite(n) ? Math.min(Math.max(n, 0), MAX_AMOUNT) : 0;
}

export default function DateMode({ t, lang }) {
  const T = t.date;
  const uid = useId();
  const [kind, setKind] = useState("difference");
  const [from, setFrom] = useState(() => toISO(today()));
  const [to, setTo] = useState(() => toISO(today()));
  const [sign, setSign] = useState(1);
  const [amounts, setAmounts] = useState({ years: "0", months: "0", days: "0" });

  const start = parseISO(from);
  let main = "";
  let detail = "";
  let problem = false;
  if (kind === "difference") {
    const end = parseISO(to);
    if (!start || !end) {
      main = T.invalid;
      problem = true;
    } else {
      const diff = dateDifference(start, end);
      const parts = [
        [diff.years, T.words.year],
        [diff.months, T.words.month],
        [diff.weeks, T.words.week],
        [diff.days, T.words.day],
      ]
        .filter(([n]) => n > 0)
        .map(([n, words]) => count(n, words, lang));
      // Each part stays on one line ("3 days" never splits), so a long answer wraps between parts.
      main =
        diff.totalDays === 0
          ? T.same
          : parts.map((part, i) => (
              <Fragment key={part}>
                {i > 0 && ", "}
                <span className="calc-date-part">{part}</span>
              </Fragment>
            ));
      // The total in days, unless the line above already says only days.
      if (diff.totalDays > 0 && (diff.years || diff.months || diff.weeks)) detail = count(diff.totalDays, T.words.day, lang);
    }
  } else if (!start) {
    main = T.invalid;
    problem = true;
  } else {
    const result = addToDate(start, { years: amount(amounts.years), months: amount(amounts.months), days: amount(amounts.days) }, sign);
    main = result ? longDate(result, lang) : T.outOfRange;
    problem = !result;
  }

  const dateField = (id, labelText, value, setValue) => (
    <div className="calc-field">
      <label className="calc-field-label" htmlFor={id}>
        {labelText}
      </label>
      <input
        id={id}
        className="calc-input"
        type="date"
        min="0001-01-01"
        max="9999-12-31"
        required
        value={value}
        onChange={(event) => setValue(event.target.value)}
      />
    </div>
  );

  return (
    <div className="calc-date">
      <div className="calc-field">
        <label className="calc-field-label" htmlFor={`${uid}-kind`}>
          {T.kind}
        </label>
        <select id={`${uid}-kind`} className="calc-input" value={kind} onChange={(event) => setKind(event.target.value)}>
          <option value="difference">{T.difference}</option>
          <option value="add">{T.add}</option>
        </select>
      </div>

      {dateField(`${uid}-from`, T.from, from, setFrom)}

      {kind === "difference" ? (
        dateField(`${uid}-to`, T.to, to, setTo)
      ) : (
        <>
          <fieldset className="calc-date-sign">
            <legend className="sr-only">{T.operation}</legend>
            {[
              [1, T.addOption],
              [-1, T.subtractOption],
            ].map(([value, text]) => (
              <label key={value} className="calc-radio">
                <input type="radio" name={`${uid}-sign`} checked={sign === value} onChange={() => setSign(value)} />
                {text}
              </label>
            ))}
          </fieldset>
          <div className="calc-date-amounts">
            {["years", "months", "days"].map((unit) => (
              <div key={unit} className="calc-field">
                <label className="calc-field-label" htmlFor={`${uid}-${unit}`}>
                  {T[unit]}
                </label>
                <input
                  id={`${uid}-${unit}`}
                  className="calc-input"
                  type="number"
                  inputMode="numeric"
                  min="0"
                  max={MAX_AMOUNT}
                  step="1"
                  value={amounts[unit]}
                  onChange={(event) => setAmounts({ ...amounts, [unit]: event.target.value })}
                />
              </div>
            ))}
          </div>
        </>
      )}

      <section className="calc-date-result" aria-labelledby={`${uid}-result`} aria-live="polite">
        <h3 id={`${uid}-result`} className="calc-field-label">
          {kind === "difference" ? T.result : T.date}
        </h3>
        <p className={`calc-date-main ${problem ? "is-problem" : ""}`}>{main}</p>
        {detail && <p className="calc-date-detail">{detail}</p>}
      </section>
    </div>
  );
}
