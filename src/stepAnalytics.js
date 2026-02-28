const DAY_MS = 24 * 60 * 60 * 1000;

function normalizeDate(rawDate) {
  const date = new Date(rawDate);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return date.toISOString().slice(0, 10);
}

function normalizeSteps(rawSteps) {
  const steps = Number.parseInt(rawSteps, 10);
  if (!Number.isFinite(steps) || steps < 0) {
    return null;
  }
  return steps;
}

function parseCsv(text) {
  const [headerLine, ...rows] = text.trim().split(/\r?\n/);
  if (!headerLine) {
    return [];
  }
  const headers = headerLine.split(",").map((header) => header.trim().toLowerCase());
  const dateIndex = headers.findIndex((value) => ["date", "day", "time", "timestamp"].includes(value));
  const stepsIndex = headers.findIndex((value) => ["steps", "stepcount", "count"].includes(value));
  if (dateIndex === -1 || stepsIndex === -1) {
    return [];
  }

  return rows
    .map((row) => row.split(","))
    .map((parts) => ({
      date: normalizeDate(parts[dateIndex]?.trim()),
      steps: normalizeSteps(parts[stepsIndex]?.trim())
    }))
    .filter((entry) => entry.date && entry.steps !== null);
}

function parseJson(text) {
  const parsed = JSON.parse(text);
  const records = Array.isArray(parsed) ? parsed : parsed?.records;
  if (!Array.isArray(records)) {
    return [];
  }
  return records
    .map((record) => ({
      date: normalizeDate(record.date ?? record.day ?? record.time ?? record.timestamp),
      steps: normalizeSteps(record.steps ?? record.stepCount ?? record.count)
    }))
    .filter((entry) => entry.date && entry.steps !== null);
}

export function parseMiFitnessData(text, fileName = "") {
  if (!text?.trim()) {
    return [];
  }
  if (fileName.toLowerCase().endsWith(".json")) {
    return parseJson(text);
  }
  try {
    return parseJson(text);
  } catch {
    return parseCsv(text);
  }
}

function getPeriodKey(dateString, period) {
  const date = new Date(`${dateString}T00:00:00Z`);
  if (period === "day") {
    return dateString;
  }
  if (period === "month") {
    return dateString.slice(0, 7);
  }
  if (period === "year") {
    return dateString.slice(0, 4);
  }
  const day = date.getUTCDay() || 7;
  date.setUTCDate(date.getUTCDate() + 4 - day);
  const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
  const weekNumber = Math.ceil(((date - yearStart) / DAY_MS + 1) / 7);
  return `${date.getUTCFullYear()}-W${String(weekNumber).padStart(2, "0")}`;
}

export function aggregateSteps(records, period) {
  const totals = new Map();
  for (const record of records) {
    const key = getPeriodKey(record.date, period);
    totals.set(key, (totals.get(key) ?? 0) + record.steps);
  }
  return [...totals.entries()]
    .map(([label, steps]) => ({ label, steps }))
    .sort((a, b) => a.label.localeCompare(b.label));
}

function average(total, count) {
  return count === 0 ? 0 : Math.round(total / count);
}

function countPeriods(records, period) {
  const periods = new Set(records.map((record) => getPeriodKey(record.date, period)));
  return periods.size;
}

export function calculateAverages(records) {
  const totalSteps = records.reduce((sum, record) => sum + record.steps, 0);
  return {
    day: average(totalSteps, countPeriods(records, "day")),
    week: average(totalSteps, countPeriods(records, "week")),
    month: average(totalSteps, countPeriods(records, "month")),
    year: average(totalSteps, countPeriods(records, "year"))
  };
}
