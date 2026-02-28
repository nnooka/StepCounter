/**
 * StepCounter Dashboard – Chart.js visualisations
 * Fetches data from /api/* endpoints and renders charts.
 */

'use strict';

// ---- Colour palette ----
const PALETTE = [
  '#4361ee', // blue
  '#2dc653', // green
  '#f4a261', // orange
  '#9b5de5', // purple
  '#4cc9f0', // cyan
  '#f15bb5', // pink
];

const MONTH_NAMES = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
];

// ---- Shared chart options helpers ----
function formatYAxisValue(val) {
  if (val >= 1000000) return (val / 1000000).toFixed(1) + 'M';
  if (val >= 1000) return (val / 1000).toFixed(0) + 'k';
  return val;
}

function baseChartOptions(yLabel = 'Steps') {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'top' },
      tooltip: {
        callbacks: {
          label: ctx => ` ${ctx.dataset.label || ''}: ${Number(ctx.raw).toLocaleString()} ${yLabel}`,
        },
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: { callback: formatYAxisValue },
        grid: { color: 'rgba(0,0,0,0.05)' },
      },
      x: { grid: { display: false } },
    },
  };
}

// ---- Fetch helpers ----
async function fetchJSON(url) {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

// ---- Stats cards ----
async function updateStats() {
  const [allData, yearlyData] = await Promise.all([
    fetchJSON('/api/data'),
    fetchJSON('/api/yearly'),
  ]);

  const totalSteps = allData.reduce((s, r) => s + r.steps, 0);
  const bestDay    = allData.reduce((m, r) => r.steps > m ? r.steps : m, 0);
  const avgSteps   = allData.length ? Math.round(totalSteps / allData.length) : 0;

  // Current year (latest year in data)
  const years = [...new Set(allData.map(r => r.date.slice(0, 4)))].sort();
  const latestYear = years[years.length - 1];
  const yearTotal  = yearlyData.find(r => String(r.year) === latestYear);
  const yearSteps  = yearTotal ? yearTotal.total_steps : 0;

  const fmt = n => Number(n).toLocaleString();
  document.getElementById('statTotal').textContent = fmt(totalSteps);
  document.getElementById('statBest').textContent  = fmt(bestDay);
  document.getElementById('statYear').textContent  = fmt(yearSteps);
  document.getElementById('statAvg').textContent   = fmt(avgSteps);
}

// ---- Yearly bar chart ----
let yearlyChartInst = null;
async function initYearlyChart() {
  const data = await fetchJSON('/api/yearly');
  const labels = data.map(r => String(r.year));
  const values = data.map(r => r.total_steps);

  const ctx = document.getElementById('yearlyChart').getContext('2d');
  if (yearlyChartInst) yearlyChartInst.destroy();
  yearlyChartInst = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Total Steps',
        data: values,
        backgroundColor: labels.map((_, i) => PALETTE[i % PALETTE.length]),
        borderRadius: 6,
        borderSkipped: false,
      }],
    },
    options: {
      ...baseChartOptions(),
      plugins: {
        ...baseChartOptions().plugins,
        legend: { display: false },
      },
    },
  });
}

// ---- Year comparison line chart ----
let comparisonChartInst = null;
async function initComparisonChart() {
  const yearlyData = await fetchJSON('/api/yearly');
  const years = yearlyData.map(r => r.year);

  // Fetch monthly data for every year in parallel
  const monthlyByYear = await Promise.all(
    years.map(y => fetchJSON(`/api/monthly?year=${y}`))
  );

  const datasets = years.map((year, i) => ({
    label: String(year),
    data: monthlyByYear[i].map(r => r.total_steps),
    borderColor: PALETTE[i % PALETTE.length],
    backgroundColor: PALETTE[i % PALETTE.length] + '22',
    borderWidth: 2.5,
    pointRadius: 4,
    tension: 0.35,
    fill: false,
  }));

  const ctx = document.getElementById('comparisonChart').getContext('2d');
  if (comparisonChartInst) comparisonChartInst.destroy();
  comparisonChartInst = new Chart(ctx, {
    type: 'line',
    data: { labels: MONTH_NAMES, datasets },
    options: baseChartOptions(),
  });
}

// ---- Monthly breakdown bar chart ----
let monthlyChartInst = null;
async function initMonthlyChart(year) {
  const data = await fetchJSON(`/api/monthly?year=${year}`);
  const values = data.map(r => r.total_steps);

  const ctx = document.getElementById('monthlyChart').getContext('2d');
  if (monthlyChartInst) monthlyChartInst.destroy();
  monthlyChartInst = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: MONTH_NAMES,
      datasets: [{
        label: `Steps in ${year}`,
        data: values,
        backgroundColor: PALETTE[2] + 'cc',
        borderColor: PALETTE[2],
        borderWidth: 1.5,
        borderRadius: 5,
        borderSkipped: false,
      }],
    },
    options: {
      ...baseChartOptions(),
      plugins: {
        ...baseChartOptions().plugins,
        legend: { display: false },
      },
    },
  });
}

// ---- Recent data table ----
async function populateTable() {
  const data = await fetchJSON('/api/data');
  const recent = data.slice(-30).reverse();
  const tbody = document.getElementById('tableBody');
  if (!recent.length) {
    tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted py-3">No data</td></tr>';
    return;
  }
  tbody.innerHTML = recent.map(r => `
    <tr>
      <td>${r.date}</td>
      <td class="text-end fw-semibold">${Number(r.steps).toLocaleString()}</td>
      <td class="text-end">${Number(r.distance).toFixed(2)}</td>
      <td class="text-end">${Number(r.calories).toFixed(0)}</td>
    </tr>
  `).join('');
}

// ---- Year selector for monthly chart ----
function attachYearSelector() {
  const sel = document.getElementById('yearSelect');
  if (!sel) return;
  // Default to last (most recent) option
  sel.selectedIndex = sel.options.length - 1;
  initMonthlyChart(sel.value);
  sel.addEventListener('change', () => initMonthlyChart(sel.value));
}

// ---- Bootstrap ----
document.addEventListener('DOMContentLoaded', async () => {
  try {
    await Promise.all([
      updateStats(),
      initYearlyChart(),
      initComparisonChart(),
      populateTable(),
    ]);
    attachYearSelector();
  } catch (err) {
    console.error('Dashboard error:', err);
  }
});
