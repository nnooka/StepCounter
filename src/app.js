import { aggregateSteps, calculateAverages, parseMiFitnessData } from "./stepAnalytics.js";

const demoData = [
  { date: "2023-01-01", steps: 6411 },
  { date: "2023-01-02", steps: 8534 },
  { date: "2023-02-10", steps: 9210 },
  { date: "2023-04-04", steps: 7341 },
  { date: "2024-01-06", steps: 11442 },
  { date: "2024-07-15", steps: 9855 },
  { date: "2024-12-25", steps: 12004 },
  { date: "2025-01-09", steps: 10017 },
  { date: "2025-03-11", steps: 11325 },
  { date: "2025-05-30", steps: 8420 }
];

const input = document.getElementById("file-input");
const periodSelect = document.getElementById("period");
const status = document.getElementById("status");
const chart = document.getElementById("chart");
const ctx = chart.getContext("2d");
const useDemoButton = document.getElementById("use-demo");
const averageTargets = {
  day: document.getElementById("avg-day"),
  week: document.getElementById("avg-week"),
  month: document.getElementById("avg-month"),
  year: document.getElementById("avg-year")
};

let activeRecords = [];

function renderAverages(records) {
  const averages = calculateAverages(records);
  for (const [period, target] of Object.entries(averageTargets)) {
    target.textContent = averages[period].toLocaleString();
  }
}

function renderChart() {
  const data = aggregateSteps(activeRecords, periodSelect.value).slice(-20);
  const width = chart.width;
  const height = chart.height;
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#f5f7ff";
  ctx.fillRect(0, 0, width, height);
  if (!data.length) {
    return;
  }

  const maxSteps = Math.max(...data.map((item) => item.steps));
  const barWidth = Math.max(12, Math.floor((width - 40) / data.length) - 6);

  data.forEach((item, index) => {
    const left = 24 + index * (barWidth + 6);
    const barHeight = Math.floor((item.steps / maxSteps) * (height - 60));
    const top = height - barHeight - 28;
    ctx.fillStyle = "#3f67ff";
    ctx.fillRect(left, top, barWidth, barHeight);
  });
}

function render(records, source) {
  activeRecords = records;
  renderAverages(records);
  renderChart();
  status.textContent = `Loaded ${records.length} records from ${source}.`;
}

async function onFileUpload(event) {
  const file = event.target.files?.[0];
  if (!file) {
    return;
  }
  const text = await file.text();
  const records = parseMiFitnessData(text, file.name);
  render(records, file.name);
}

input.addEventListener("change", onFileUpload);
periodSelect.addEventListener("change", renderChart);
useDemoButton.addEventListener("click", () => render(demoData, "demo data"));

render(demoData, "demo data");
