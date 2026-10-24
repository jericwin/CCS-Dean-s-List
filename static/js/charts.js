/* Chart.js defaults and helpers in the Fox palette. */
(function () {
  "use strict";
  if (!window.Chart) return;

  const css = getComputedStyle(document.documentElement);
  const v = (name) => css.getPropertyValue(name).trim();
  const palette = {
    maroon: v("--maroon-700"), maroonLight: v("--maroon-200"), maroonMid: v("--maroon-500"),
    orange: v("--orange-500"), orangeLight: v("--orange-200"),
    grey: v("--grey-500"), greyLight: v("--grey-200"),
    success: v("--success-600"), danger: v("--danger-600"),
  };
  // Status → colour, matching the badge tones.
  const statusColors = {
    "Pending": palette.orange, "Approved": "#d9a066", "Rejected": "#d98a83",
    "For Dean Review": palette.maroon, "Dean Approved": palette.success, "Dean Rejected": palette.danger,
  };

  Chart.defaults.font.family = v("--font-sans") || "system-ui";
  Chart.defaults.font.size = 12;
  Chart.defaults.color = v("--grey-600");
  Chart.defaults.borderColor = v("--grey-150");
  Chart.defaults.plugins.legend.labels.usePointStyle = true;
  Chart.defaults.plugins.legend.labels.boxWidth = 8;
  Chart.defaults.plugins.tooltip.backgroundColor = v("--grey-900");
  Chart.defaults.plugins.tooltip.padding = 10;
  Chart.defaults.plugins.tooltip.cornerRadius = 8;
  Chart.defaults.maintainAspectRatio = false;

  const empty = (canvas, message) => {
    const box = canvas.parentElement;
    box.innerHTML = `<div class="empty" style="height:100%"><div class="list-icon"><i class="fas fa-chart-simple"></i></div><p>${Fox.escapeHtml(message)}</p></div>`;
  };
  const hasData = (values) => values && values.some((n) => Number(n) > 0);
  const intAxis = { beginAtZero: true, ticks: { precision: 0 }, grid: { color: v("--grey-150") }, border: { display: false } };
  const catAxis = { grid: { display: false }, border: { display: false } };

  window.FoxCharts = {
    palette,
    statusColors,
    bar(id, labels, values, { label = "Count", color = palette.orange, horizontal = false, emptyText = "No data for this selection yet." } = {}) {
      const el = document.getElementById(id);
      if (!el) return null;
      if (!hasData(values)) return empty(el, emptyText);
      return new Chart(el, {
        type: "bar",
        data: { labels, datasets: [{ label, data: values, backgroundColor: color, borderRadius: 6, maxBarThickness: 44 }] },
        options: {
          indexAxis: horizontal ? "y" : "x",
          plugins: { legend: { display: false } },
          scales: horizontal ? { x: intAxis, y: catAxis } : { x: catAxis, y: intAxis },
        },
      });
    },
    doughnut(id, labels, values, colors, { emptyText = "No applications for this selection yet." } = {}) {
      const el = document.getElementById(id);
      if (!el) return null;
      if (!hasData(values)) return empty(el, emptyText);
      return new Chart(el, {
        type: "doughnut",
        data: { labels, datasets: [{ data: values, backgroundColor: colors, borderWidth: 2, borderColor: "#fff", hoverOffset: 6 }] },
        options: { cutout: "68%", plugins: { legend: { position: "bottom" } } },
      });
    },
    lines(id, labels, series, { emptyText = "No activity in the last 12 months." } = {}) {
      const el = document.getElementById(id);
      if (!el) return null;
      if (!series.some((s) => hasData(s.data))) return empty(el, emptyText);
      return new Chart(el, {
        type: "line",
        data: {
          labels,
          datasets: series.map((s) => ({
            label: s.label, data: s.data, borderColor: s.color, backgroundColor: s.color,
            tension: 0.35, pointRadius: 3, pointHoverRadius: 5, borderWidth: 2, fill: false,
          })),
        },
        options: { interaction: { mode: "index", intersect: false }, plugins: { legend: { position: "bottom" } }, scales: { x: catAxis, y: intAxis } },
      });
    },
  };
})();
