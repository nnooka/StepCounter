import test from "node:test";
import assert from "node:assert/strict";
import { aggregateSteps, calculateAverages, parseMiFitnessData } from "../src/stepAnalytics.js";

test("parseMiFitnessData handles csv data", () => {
  const csv = "date,steps\n2025-01-01,1000\n2025-01-02,2000";
  assert.deepEqual(parseMiFitnessData(csv, "mi.csv"), [
    { date: "2025-01-01", steps: 1000 },
    { date: "2025-01-02", steps: 2000 }
  ]);
});

test("aggregateSteps groups by month and year", () => {
  const records = [
    { date: "2025-01-01", steps: 1000 },
    { date: "2025-01-12", steps: 1500 },
    { date: "2026-01-01", steps: 3000 }
  ];
  assert.deepEqual(aggregateSteps(records, "month"), [
    { label: "2025-01", steps: 2500 },
    { label: "2026-01", steps: 3000 }
  ]);
  assert.deepEqual(aggregateSteps(records, "year"), [
    { label: "2025", steps: 2500 },
    { label: "2026", steps: 3000 }
  ]);
});

test("calculateAverages returns period averages", () => {
  const records = [
    { date: "2025-01-01", steps: 1000 },
    { date: "2025-01-02", steps: 3000 },
    { date: "2025-01-08", steps: 2000 }
  ];
  assert.deepEqual(calculateAverages(records), {
    day: 2000,
    week: 3000,
    month: 6000,
    year: 6000
  });
});
