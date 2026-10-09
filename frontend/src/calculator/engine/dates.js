// Date calculation, like the Windows calculator: the difference between two dates (in
// years, months, weeks and days, and in total days), and adding or subtracting years,
// months and days. Dates are plain {y, m, d} (month 1-12) with no time and no time zone,
// so the answer never depends on the clock or the time zone of the phone.

export const MIN_YEAR = 1;
export const MAX_YEAR = 9999;

export const isLeap = (y) => (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0;

export function daysInMonth(y, m) {
  return m === 2 ? (isLeap(y) ? 29 : 28) : [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1];
}

/** Day number of a date (1 January 1970 is 0), for any year of the Gregorian calendar. */
export function dayNumber({ y, m, d }) {
  // Howard Hinnant's days_from_civil: years start on 1 March, so 29 February is the last day.
  const yy = m <= 2 ? y - 1 : y;
  const era = Math.floor(yy / 400);
  const yoe = yy - era * 400;
  const doy = Math.floor((153 * (m + (m > 2 ? -3 : 9)) + 2) / 5) + d - 1;
  const doe = yoe * 365 + Math.floor(yoe / 4) - Math.floor(yoe / 100) + doy;
  return era * 146097 + doe - 719468;
}

/** The date of a day number (the inverse of dayNumber). */
export function fromDayNumber(n) {
  const z = n + 719468;
  const era = Math.floor(z / 146097);
  const doe = z - era * 146097;
  const yoe = Math.floor((doe - Math.floor(doe / 1460) + Math.floor(doe / 36524) - Math.floor(doe / 146096)) / 365);
  const doy = doe - (365 * yoe + Math.floor(yoe / 4) - Math.floor(yoe / 100));
  const mp = Math.floor((5 * doy + 2) / 153);
  const d = doy - Math.floor((153 * mp + 2) / 5) + 1;
  const m = mp + (mp < 10 ? 3 : -9);
  return { y: era * 400 + yoe + (m <= 2 ? 1 : 0), m, d };
}

export function isValidDate(date) {
  if (!date) return false;
  const { y, m, d } = date;
  return (
    [y, m, d].every(Number.isInteger) && y >= MIN_YEAR && y <= MAX_YEAR && m >= 1 && m <= 12 && d >= 1 && d <= daysInMonth(y, m)
  );
}

/** "2026-10-09" (what a date box gives) to {y, m, d}, or null. */
export function parseISO(text) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(text ?? "").trim());
  if (!match) return null;
  const date = { y: Number(match[1]), m: Number(match[2]), d: Number(match[3]) };
  return isValidDate(date) ? date : null;
}

export function toISO({ y, m, d }) {
  const pad = (n, size) => String(n).padStart(size, "0");
  return `${pad(y, 4)}-${pad(m, 2)}-${pad(d, 2)}`;
}

/** Today's date on this device. */
export function today(now = new Date()) {
  return { y: now.getFullYear(), m: now.getMonth() + 1, d: now.getDate() };
}

export function compareDates(a, b) {
  return dayNumber(a) - dayNumber(b);
}

/** Add months; a day that the new month does not have becomes its last day (31 Jan + 1 month = 28 or 29 Feb). */
export function addMonths({ y, m, d }, months) {
  const index = y * 12 + (m - 1) + months;
  const ny = Math.floor(index / 12);
  const nm = index - ny * 12 + 1;
  return { y: ny, m: nm, d: Math.min(d, daysInMonth(ny, nm)) };
}

/**
 * Add (sign 1) or subtract (sign -1) years, months and days. Years and months move together
 * first (29 Feb 2024 + 1 year = 28 Feb 2025), then the days. Returns null outside years 1-9999.
 */
export function addToDate(date, { years = 0, months = 0, days = 0 }, sign = 1) {
  const moved = addMonths(date, sign * (years * 12 + months));
  if (moved.y < MIN_YEAR || moved.y > MAX_YEAR) return null;
  const result = fromDayNumber(dayNumber(moved) + sign * days);
  return isValidDate(result) ? result : null;
}

/**
 * The difference between two dates, whichever comes first: whole years and months counted
 * on the calendar from the earlier date, then the days left as weeks and days.
 * 31 Jan to 28 Feb 2025 is 1 month; 31 Jan to 27 Feb is 3 weeks and 6 days.
 */
export function dateDifference(first, second) {
  let a = first;
  let b = second;
  if (compareDates(a, b) > 0) [a, b] = [b, a];
  let months = (b.y - a.y) * 12 + (b.m - a.m);
  if (compareDates(addMonths(a, months), b) > 0) months -= 1;
  const rest = dayNumber(b) - dayNumber(addMonths(a, months));
  return {
    years: Math.floor(months / 12),
    months: months % 12,
    weeks: Math.floor(rest / 7),
    days: rest % 7,
    totalDays: dayNumber(b) - dayNumber(a),
  };
}
