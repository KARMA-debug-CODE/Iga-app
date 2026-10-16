// CSV files the app makes for people to open in Excel, LibreOffice or Google Sheets.
//
// A cell that starts with = + - @ (or a tab or carriage return, or their full-width forms) is read by
// spreadsheets as a formula, which can run commands or send the sheet's data to another site
// ("CSV injection"). Names and other text people typed are written with a leading apostrophe instead,
// which spreadsheets show as plain text.
const FORMULA_START = /^[=+\-@\t\r＝＋－＠]/;

export function csvCell(value) {
  let text = String(value ?? "");
  if (FORMULA_START.test(text)) text = `'${text}`;
  return `"${text.replace(/"/g, '""')}"`;
}

export function toCsv(rows) {
  return rows.map((row) => row.map(csvCell).join(",")).join("\r\n");
}

// Save rows as a CSV file (UTF-8 with a byte order mark, so Excel shows accents correctly).
export function downloadCsv(filename, rows) {
  const url = URL.createObjectURL(new Blob(["\ufeff" + toCsv(rows)], { type: "text/csv;charset=utf-8" }));
  const a = Object.assign(document.createElement("a"), { href: url, download: filename });
  a.click();
  URL.revokeObjectURL(url);
}
