const Charts = (() => {
  const COLOR = {
    navy: "#1f3a5f", yellow: "#f5b301", teal: "#2a9d8f", coral: "#e76f51",
    grid: "#e2e5ec", ink: "#5b6478",
  };
  const numberFormat = new Intl.NumberFormat("en-US");
  const fmtInt = (value) => numberFormat.format(Math.round(value));
  const fmtMoney = (value) => "$" + Number(value).toFixed(2);
  const fmtMoneyBig = (value) => "$" + numberFormat.format(Math.round(value));

  const instances = {};

  function setupDefaults() {
    if (typeof Chart === "undefined") return;
    Chart.defaults.font.family = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif';
    Chart.defaults.color = COLOR.ink;
    Chart.defaults.animation.duration = 350;
    Chart.defaults.plugins.legend.labels.usePointStyle = true;
  }

  function draw(canvasId, config) {
    if (typeof Chart === "undefined") return;
    if (instances[canvasId]) instances[canvasId].destroy();
    instances[canvasId] = new Chart(document.getElementById(canvasId), config);
  }

  function hourLabel(hour) {
    const suffix = hour < 12 ? "AM" : "PM";
    const twelve = hour % 12 === 0 ? 12 : hour % 12;
    return twelve + " " + suffix;
  }

  const baseOptions = { responsive: true, maintainAspectRatio: false };

  /* ------------------------------------------------------------ KPI cards */
  function renderKpis(summary) {
    const empty = !summary || !summary.trips;
    const items = [
      ["Trips", empty ? "—" : fmtInt(summary.trips)],
      ["Average fare", empty ? "—" : fmtMoney(summary.avg_fare)],
      ["Average distance", empty ? "—" : summary.avg_distance.toFixed(2) + " mi"],
      ["Average speed", empty ? "—" : summary.avg_speed_mph.toFixed(1) + " mph"],
      ["Average tip (card)", empty || summary.avg_tip_pct === null ? "—" : summary.avg_tip_pct.toFixed(1) + "%"],
      ["Fare revenue", empty ? "—" : fmtMoneyBig(summary.total_revenue)],
    ];
    const container = document.getElementById("kpis");
    container.textContent = "";
    items.forEach(([label, value]) => {
      const card = document.createElement("div");
      card.className = "kpi";
      const labelNode = document.createElement("p");
      labelNode.className = "kpi-label";
      labelNode.textContent = label;
      const valueNode = document.createElement("p");
      valueNode.className = "kpi-value";
      valueNode.textContent = value;
      card.append(labelNode, valueNode);
      container.appendChild(card);
    });
  }
function renderInsights({ summary, hourly, borough, payment }) {
    const container = document.getElementById("insights");
    container.textContent = "";
    const add = (heading, parts) => {
      const card = document.createElement("div");
      card.className = "insight";
      const h = document.createElement("h3");
      h.textContent = heading;
      const p = document.createElement("p");
      parts.forEach((part, index) => {
        if (index % 2 === 1) {
          const strong = document.createElement("strong");
          strong.textContent = part;
          p.appendChild(strong);
        } else {
          p.appendChild(document.createTextNode(part));
        }
      });
      card.append(h, p);
      container.appendChild(card);
    };

    if (!summary || !summary.trips) {
      add("No matching trips", ["Nothing matches these filters. Try widening the date, distance or fare range."]);
      return;
    }

   const peak = hourly.reduce((best, row) => (row.trips > best.trips ? row : best), hourly[0]);
    add("Peak demand", [
      "Taxi demand peaks at ", hourLabel(peak.hour),
      ", with ", fmtInt(peak.trips) + " trips (" + (100 * peak.trips / summary.trips).toFixed(1) + "% of all trips in this selection).",
    ]);

    
    const busyHours = hourly.filter((row) => row.avg_speed_mph !== null && row.trips >= summary.trips * 0.01);
    if (busyHours.length >= 2) {
      const slowest = busyHours.reduce((a, b) => (b.avg_speed_mph < a.avg_speed_mph ? b : a));
      const fastest = busyHours.reduce((a, b) => (b.avg_speed_mph > a.avg_speed_mph ? b : a));
      add("Traffic", [
        "Cabs crawl at ", slowest.avg_speed_mph.toFixed(1) + " mph around " + hourLabel(slowest.hour),
        " but reach ", fastest.avg_speed_mph.toFixed(1) + " mph around " + hourLabel(fastest.hour) + ".",
      ]);
    }

    if (borough.length) {
      const top = borough[0];
      add("Geography", [
        "", top.borough, " accounts for ",
        (100 * top.trips / summary.trips).toFixed(1) + "% of pickups,",
        " with an average fare of " + fmtMoney(top.avg_fare) + ".",
      ]);
    }

    const card = payment.find((row) => row.payment_type_id === 1);
    if (card && card.avg_tip_pct !== null) {
      add("Tipping", [
        "Card riders tip ", card.avg_tip_pct.toFixed(1) + "%",
        " on average. Cash tips never reach the meter, so they are left out.",
      ]);
    }
  }


  function renderHourly(rows) {
    const byHour = new Map(rows.map((row) => [row.hour, row]));
    const hours = Array.from({ length: 24 }, (_, hour) => hour);
    draw("chart-hourly", {
      data: {
        labels: hours.map(hourLabel),
        datasets: [
          {
            type: "bar", label: "Trips", yAxisID: "y", order: 2,
            data: hours.map((h) => (byHour.has(h) ? byHour.get(h).trips : 0)),
            backgroundColor: COLOR.navy, borderRadius: 4,
          },
          {
            type: "line", label: "Average speed (mph)", yAxisID: "y1", order: 1,
            data: hours.map((h) => (byHour.has(h) ? byHour.get(h).avg_speed_mph : null)),
            borderColor: COLOR.coral, backgroundColor: COLOR.coral,
            tension: 0.3, pointRadius: 3, spanGaps: true,
          },
        ],
      },
      options: {
        ...baseOptions,
        interaction: { mode: "index", intersect: false },
        scales: {
          y: { beginAtZero: true, title: { display: true, text: "Trips" }, grid: { color: COLOR.grid },
               ticks: { callback: (v) => fmtInt(v) } },
          y1: { position: "right", beginAtZero: true, title: { display: true, text: "mph" }, grid: { drawOnChartArea: false } },
          x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 12 } },
        },
        plugins: { tooltip: { callbacks: { label: (ctx) =>
          ctx.dataset.yAxisID === "y" ? "Trips: " + fmtInt(ctx.parsed.y) : "Speed: " + ctx.parsed.y.toFixed(1) + " mph" } } },
      },
    });
  }

  function renderDaily(rows) {
    draw("chart-daily", {
      type: "line",
      data: {
        labels: rows.map((row) => {
          const [, month, day] = row.date.split("-");
          return ["Jan", "Feb"][Number(month) - 1] + " " + Number(day);
        }),
        datasets: [{
          label: "Trips", data: rows.map((row) => row.trips),
          borderColor: COLOR.navy, backgroundColor: "rgba(245, 179, 1, 0.25)",
          fill: true, tension: 0.25, pointRadius: 2,
        }],
      },
      options: {
        ...baseOptions,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, grid: { color: COLOR.grid }, ticks: { callback: (v) => fmtInt(v) } },
          x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 10 } },
        },
      },
    });
  }

  function renderBorough(rows) {
    const total = rows.reduce((sum, row) => sum + row.trips, 0);
    draw("chart-borough", {
      type: "bar",
      data: {
        labels: rows.map((row) => row.borough),
        datasets: [{ label: "Pickups", data: rows.map((row) => row.trips), backgroundColor: COLOR.teal, borderRadius: 4 }],
      },
      options: {
        ...baseOptions, indexAxis: "y",
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: (ctx) =>
            fmtInt(ctx.parsed.x) + " pickups (" + (100 * ctx.parsed.x / total).toFixed(1) + "%)" } },
        },
        scales: {
          x: { beginAtZero: true, grid: { color: COLOR.grid }, ticks: { callback: (v) => fmtInt(v) } },
          y: { grid: { display: false } },
        },
      },
    });
  }

  function renderPayment(rows) {
    draw("chart-payment", {
      type: "bar",
      data: {
        labels: rows.map((row) => row.description),
        datasets: [{ label: "Trips", data: rows.map((row) => row.trips), backgroundColor: COLOR.yellow, borderRadius: 4 }],
      },
      options: {
        ...baseOptions,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: {
            label: (ctx) => fmtInt(ctx.parsed.y) + " trips",
            afterLabel: (ctx) => {
              const tip = rows[ctx.dataIndex].avg_tip_pct;
              return tip === null ? "Tips not recorded" : "Average tip: " + tip.toFixed(1) + "%";
            },
          } },
        },
        scales: {
          y: { beginAtZero: true, grid: { color: COLOR.grid }, ticks: { callback: (v) => fmtInt(v) } },
          x: { grid: { display: false } },
        },
      },
    });
  }

  function renderTopZones(rows, by) {
    const truncate = (text) => (text.length > 28 ? text.slice(0, 27) + "…" : text);
    draw("chart-zones", {
      type: "bar",
      data: {
        labels: rows.map((row) => row.zone),
        datasets: [{
          label: by === "dropoff" ? "Dropoffs" : "Pickups",
          data: rows.map((row) => row.trips),
          backgroundColor: by === "dropoff" ? COLOR.teal : COLOR.navy, borderRadius: 4,
        }],
      },
      options: {
        ...baseOptions, indexAxis: "y",
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: {
            label: (ctx) => fmtInt(ctx.parsed.x) + (by === "dropoff" ? " dropoffs" : " pickups"),
            afterLabel: (ctx) => rows[ctx.dataIndex].borough,
          } },
        },
        scales: {
          x: { beginAtZero: true, grid: { color: COLOR.grid }, ticks: { callback: (v) => fmtInt(v) } },
          y: { grid: { display: false }, ticks: { callback(value) { return truncate(this.getLabelForValue(value)); } } },
        },
      },
    });
  }

  function renderRoutes(rows) {
    const list = document.getElementById("top-routes");
    list.textContent = "";
    if (!rows.length) {
      const item = document.createElement("li");
      item.className = "route";
      item.textContent = "No routes match these filters.";
      list.appendChild(item);
      return;
    }
    const max = rows[0].trips;
    rows.forEach((row) => {
      const item = document.createElement("li");
      item.className = "route";
      const bar = document.createElement("span");
      bar.className = "route-bar";
      bar.style.width = (100 * row.trips / max).toFixed(1) + "%";
      const name = document.createElement("span");
      name.className = "route-name";
      name.textContent = row.pu_zone + " → " + row.do_zone;
      const stat = document.createElement("span");
      stat.className = "route-stat";
      stat.textContent = fmtInt(row.trips) + " trips · " + fmtMoney(row.avg_fare) + " avg fare";
      item.append(bar, name, stat);
      list.appendChild(item);
    });
  }

  setupDefaults();
  return {
    renderKpis, renderInsights, renderHourly, renderDaily,
    renderBorough, renderPayment, renderTopZones, renderRoutes, fmtInt, fmtMoney,
  };
})();








