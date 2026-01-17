// Tailwind dark mode via class
tailwind.config = { darkMode: 'class' };

// -------------------------
// API Fetch
// -------------------------
const API_BASE = "https://hospital-stain-tracker-data-pipeline-production.up.railway.app";

async function fetchMetrics(dateStr) {
  try {
    const response = await fetch(`${API_BASE}/metrics/compare?date=${dateStr}`);
    const data = await response.json();
    return data.rows.map(row => ({
      region: row.region,
      strain: row.strain_index,
      delta: row.delta || 0
    }));
  } catch (error) {
    console.error('API error:', error);
    return [];
  }
}

// Placeholder trend data (not tied to snapshot date, but could be)
const TREND_LABELS = ["Day 1", "Day 2", "Day 3", "Day 4", "Day 5", "Day 6", "Day 7"];
const TREND_VALUES = [62, 66, 64, 70, 73, 71, 75];

// -------------------------
// Theme handling
// -------------------------
const root = document.documentElement;
const themeToggle = document.getElementById('themeToggle');

function setTheme(mode) {
  if (mode === 'dark') root.classList.add('dark');
  else root.classList.remove('dark');
  localStorage.setItem('hst_theme', mode);
  refreshCharts(); // update chart grid/ticks colors
}

function initTheme() {
  const saved = localStorage.getItem('hst_theme');
  if (saved === 'dark' || saved === 'light') {
    setTheme(saved);
    return;
  }
  // System preference fallback
  const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  setTheme(prefersDark ? 'dark' : 'light');
}

themeToggle.addEventListener('click', () => {
  const isDark = root.classList.contains('dark');
  setTheme(isDark ? 'light' : 'dark');
});

// -------------------------
// Helpers
// -------------------------
function formatPercent(n) {
  return `${Math.round(n)}%`;
}

function strainBadge(strain) {
  if (strain > 80) return { label: "CRISIS", cls: "bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-200" };
  if (strain >= 70) return { label: "ELEVATED", cls: "bg-orange-100 text-orange-700 dark:bg-orange-900/35 dark:text-orange-200" };
  return { label: "STABLE", cls: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/35 dark:text-emerald-200" };
}

function strainPill(strain) {
  if (strain > 80) return "bg-rose-500/10 text-rose-700 dark:text-rose-200 border border-rose-500/20";
  if (strain >= 70) return "bg-orange-500/10 text-orange-700 dark:text-orange-200 border border-orange-500/20";
  return "bg-emerald-500/10 text-emerald-700 dark:text-emerald-200 border border-emerald-500/20";
}

function deltaCell(delta) {
  const sign = delta > 0 ? "+" : "";
  const cls = delta > 0
    ? "text-rose-600 dark:text-rose-300"
    : delta < 0
      ? "text-emerald-600 dark:text-emerald-300"
      : "text-slate-600 dark:text-slate-300";
  return { text: `${sign}${delta.toFixed(1)}`, cls };
}

function nowStamp() {
  const d = new Date();
  return d.toLocaleString(undefined, { year: 'numeric', month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit' });
}

// -------------------------
// UI render (KPIs + Table)
// -------------------------
const tableBody = document.getElementById('tableBody');
const kpiHighestState = document.getElementById('kpiHighestState');
const kpiHighestValue = document.getElementById('kpiHighestValue');
const kpiHighestBadge = document.getElementById('kpiHighestBadge');
const kpiAverage = document.getElementById('kpiAverage');
const avgProgress = document.getElementById('avgProgress');
const kpiCrisis = document.getElementById('kpiCrisis');
const lastRefreshed = document.getElementById('lastRefreshed');

async function renderDashboard(dateStr) {
  const rows = await fetchMetrics(dateStr);
  const sortedRows = rows.slice().sort((a, b) => b.strain - a.strain);

  // KPIs
  const highest = sortedRows[0] || { region: "—", strain: 0 };
  const avg = sortedRows.length ? sortedRows.reduce((s, r) => s + r.strain, 0) / sortedRows.length : 0;
  const crisisCount = sortedRows.filter(r => r.strain > 80).length;

  kpiHighestState.textContent = highest.region;
  kpiHighestValue.textContent = formatPercent(highest.strain);

  const hb = strainBadge(highest.strain);
  kpiHighestBadge.textContent = hb.label;
  kpiHighestBadge.className = `px-2.5 py-1 rounded-full text-xs font-semibold ${hb.cls}`;

  kpiAverage.textContent = avg.toFixed(1);
  avgProgress.style.width = `${Math.max(0, Math.min(100, avg))}%`;

  kpiCrisis.textContent = crisisCount.toString();

  // Table
  tableBody.innerHTML = "";
  sortedRows.forEach((r) => {
    const tr = document.createElement('tr');
    tr.className = "hover:bg-slate-50 dark:hover:bg-slate-800/40";

    const tdRegion = document.createElement('td');
    tdRegion.className = "px-5 py-3 font-medium";
    tdRegion.textContent = r.region;

    const tdStrain = document.createElement('td');
    tdStrain.className = "px-5 py-3 text-right";
    tdStrain.innerHTML = `
      <span class="inline-flex items-center justify-end gap-2">
        <span class="px-2.5 py-1 rounded-full text-xs font-semibold ${strainPill(r.strain)}">${formatPercent(r.strain)}</span>
      </span>
    `;

    const tdDelta = document.createElement('td');
    const d = deltaCell(r.delta);
    tdDelta.className = `px-5 py-3 text-right font-semibold ${d.cls}`;
    tdDelta.textContent = d.text;

    tr.appendChild(tdRegion);
    tr.appendChild(tdStrain);
    tr.appendChild(tdDelta);
    tableBody.appendChild(tr);
  });

  // Charts
  updateCharts(sortedRows);

  // Show the selected date instead of current time
  if (dateStr) {
    const date = new Date(dateStr);
    lastRefreshed.textContent = date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
  } else {
    lastRefreshed.textContent = "—";
  }
}

// -------------------------
// Charts
// -------------------------
let barChartInstance = null;
let lineChartInstance = null;

function chartThemeColors() {
  const isDark = root.classList.contains('dark');
  return {
    grid: isDark ? "rgba(148,163,184,0.14)" : "rgba(148,163,184,0.28)",
    ticks: isDark ? "rgba(226,232,240,0.85)" : "rgba(15,23,42,0.75)",
    border: isDark ? "rgba(148,163,184,0.22)" : "rgba(148,163,184,0.35)"
  };
}

function buildBarColors(strains) {
  // Color-coded strain levels
  return strains.map(s => {
    if (s > 80) return "rgba(244, 63, 94, 0.75)";   // rose
    if (s >= 70) return "rgba(249, 115, 22, 0.75)"; // orange
    return "rgba(16, 185, 129, 0.75)";              // emerald
  });
}

function updateCharts(rows) {
  const labels = rows.map(r => r.region);
  const values = rows.map(r => r.strain);

  const t = chartThemeColors();

  // Bar chart
  const barCtx = document.getElementById('barChart');
  const barData = {
    labels,
    datasets: [{
      label: "Strain Index",
      data: values,
      backgroundColor: buildBarColors(values),
      borderColor: t.border,
      borderWidth: 1,
      borderRadius: 10
    }]
  };

  const barOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (ctx) => ` ${ctx.parsed.y}%`
        }
      }
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: { color: t.ticks, maxRotation: 0, autoSkip: true }
      },
      y: {
        beginAtZero: true,
        max: 100,
        grid: { color: t.grid },
        ticks: { color: t.ticks, callback: (v) => `${v}%` }
      }
    }
  };

  if (barChartInstance) {
    barChartInstance.data = barData;
    barChartInstance.options = barOptions;
    barChartInstance.update();
  } else {
    barChartInstance = new Chart(barCtx, { type: 'bar', data: barData, options: barOptions });
  }

  // Line chart (placeholder)
  const lineCtx = document.getElementById('lineChart');
  const lineData = {
    labels: TREND_LABELS,
    datasets: [{
      label: "Avg Strain (placeholder)",
      data: TREND_VALUES,
      tension: 0.35,
      borderColor: "rgba(59, 130, 246, 0.9)",
      backgroundColor: "rgba(59, 130, 246, 0.18)",
      fill: true,
      pointRadius: 3,
      pointHoverRadius: 5
    }]
  };

  const lineOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (ctx) => ` ${ctx.parsed.y}%`
        }
      }
    },
    scales: {
      x: { grid: { display: false }, ticks: { color: t.ticks } },
      y: {
        beginAtZero: true,
        max: 100,
        grid: { color: t.grid },
        ticks: { color: t.ticks, callback: (v) => `${v}%` }
      }
    }
  };

  if (lineChartInstance) {
    lineChartInstance.data = lineData;
    lineChartInstance.options = lineOptions;
    lineChartInstance.update();
  } else {
    lineChartInstance = new Chart(lineCtx, { type: 'line', data: lineData, options: lineOptions });
  }
}

function refreshCharts() {
  // Re-apply theme colors without changing data
  if (!barChartInstance && !lineChartInstance) return;
  const t = chartThemeColors();

  if (barChartInstance) {
    barChartInstance.options.scales.x.ticks.color = t.ticks;
    barChartInstance.options.scales.y.ticks.color = t.ticks;
    barChartInstance.options.scales.y.grid.color = t.grid;
    barChartInstance.data.datasets[0].borderColor = t.border;
    barChartInstance.update();
  }

  if (lineChartInstance) {
    lineChartInstance.options.scales.x.ticks.color = t.ticks;
    lineChartInstance.options.scales.y.ticks.color = t.ticks;
    lineChartInstance.options.scales.y.grid.color = t.grid;
    lineChartInstance.update();
  }
}

// -------------------------
// CSV Export
// -------------------------
function toCSV(rows) {
  const header = ["Region", "Strain Index", "Delta Strain"];
  const lines = [header.join(",")];
  rows.forEach(r => {
    const safeRegion = `"${String(r.region).replace(/"/g, '""')}"`;
    lines.push([safeRegion, r.strain, r.delta].join(","));
  });
  return lines.join("\n");
}

async function downloadCSV(dateStr) {
  const rows = await fetchMetrics(dateStr);
  const sortedRows = rows.slice().sort((a, b) => b.strain - a.strain);
  const csv = toCSV(sortedRows);
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);

  const a = document.createElement('a');
  a.href = url;
  a.download = `hospital_strain_${dateStr || "snapshot"}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();

  URL.revokeObjectURL(url);
}

// -------------------------
// Init
// -------------------------
const datePicker = document.getElementById('datePicker');
const downloadBtn = document.getElementById('downloadBtn');

function setDefaultDate() {
  datePicker.value = '2021-06-12';
}

datePicker.addEventListener('change', async () => await renderDashboard(datePicker.value));
downloadBtn.addEventListener('click', async () => await downloadCSV(datePicker.value));

(async () => {
  initTheme();
  setDefaultDate();
  await renderDashboard(datePicker.value);
})();
