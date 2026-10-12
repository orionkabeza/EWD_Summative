const TripsTable = (() => {
  const COLUMNS = [
    { key: "pickup_ts", label: "Pickup time", sortable: true, format: (v) => v.replace("T", " ") },
    { key: "pu_zone", label: "From" },
    { key: "do_zone", label: "To" },
    { key: "trip_distance", label: "Distance (mi)", sortable: true, numeric: true, format: (v) => v.toFixed(2) },
    { key: "trip_duration_min", label: "Duration (min)", numeric: true, format: (v) => v.toFixed(1) },
    { key: "fare_amount", label: "Fare", sortable: true, numeric: true, format: (v) => "$" + v.toFixed(2) },
    { key: "tip_pct", label: "Tip", numeric: true, format: (v) => (v === null ? "n/a" : v.toFixed(1) + "%") },
    { key: "payment_type", label: "Payment" },
    ];

  const DETAIL_LABELS = [
    ["trip_id", "Trip ID"], ["vendor", "Vendor"], ["pickup_ts", "Pickup"], ["dropoff_ts", "Dropoff"],
    ["pu_zone", "Pickup zone"], ["pu_borough", "Pickup borough"],
    ["do_zone", "Dropoff zone"], ["do_borough", "Dropoff borough"],
    ["passenger_count", "Passengers"], ["trip_distance", "Distance (mi)"],
    ["trip_duration_min", "Duration (min)"], ["avg_speed_mph", "Average speed (mph)"],
    ["rate_code", "Rate code"], ["payment_type", "Payment type"],
    ["fare_amount", "Fare ($)"], ["extra", "Extra ($)"], ["mta_tax", "MTA tax ($)"],
    ["tip_amount", "Tip ($)"], ["tip_pct", "Tip (%)"], ["tolls_amount", "Tolls ($)"],
    ["improvement_surcharge", "Improvement surcharge ($)"], ["congestion_surcharge", "Congestion surcharge ($)"],
    ["total_amount", "Total ($)"], ["fare_per_mile", "Fare per mile ($)"],
    ["store_and_fwd_flag", "Store and forward"],
  ];

  const state = { filters: {}, sort: "pickup_ts", order: "desc", page: 1, pageSize: 25, total: 0, requestId: 0 };
  let root, body, status, pager, dialog;

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
}

 function build(containerId) {
   root = document.getElementById(containerId);
   root.textContent = "";

   const scroller = element("div", "trips-table-scroll");
   const table = element("table", "trips-table");
   table.setAttribute("aria-label", "Taxi trips");
   const headRow = element("tr");
   COLUMNS.forEach((column) => {
     const th = element("th", column.numeric ? "num" : "");
     th.scope = "col";
     if (column.sortable) {
       const button = element("button", "sort-btn", column.label);
       button.type = "button";
       button.dataset.key = column.key;
       button.addEventListener("click", () => toggleSort(column.key));
       th.appendChild(button);
     } else {
       th.textContent = column.label;
     }
     th.dataset.key = column.key;
     headRow.appendChild(th);
   });
    const thead = element("thead");
    thead.appendChild(headRow);
    body = element("tbody");
    table.append(thead, body);
    scroller.appendChild(table);

    status = element("p", "trips-status");
    status.setAttribute("role", "status");
    pager = element("div", "trips-pager");
    dialog = element("dialog", "trip-detail");

    root.append(scroller, status, pager, dialog);
  }

  function toggleSort(key) {
    if (state.sort === key) {
      state.order = state.order === "asc" ? "desc" : "asc";
    } else {
      state.sort = key;
      state.order = "desc";
    }
    state.page = 1;
    load();
  }

  function updateSortIndicators() {
    root.querySelectorAll("th").forEach((th) => {
      const active = th.dataset.key === state.sort;
      th.setAttribute("aria-sort", active ? (state.order === "asc" ? "ascending" : "descending") : "none");
      const button = th.querySelector(".sort-btn");
      if (button) {
        const base = COLUMNS.find((c) => c.key === th.dataset.key).label;
        button.textContent = base + (active ? (state.order === "asc" ? " ▲" : " ▼") : "");
      }
    });
  }

  function renderRows(rows) {
    body.textContent = "";
    rows.forEach((row) => {
      const tr = element("tr", "clickable");
      tr.tabIndex = 0;
      tr.addEventListener("click", () => showDetail(row.trip_id));
      tr.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") { event.preventDefault(); showDetail(row.trip_id); }
      });
      COLUMNS.forEach((column) => {
        const value = row[column.key];
        const text = value === null || value === undefined
          ? "n/a"
          : (column.format ? column.format(value) : String(value));
        tr.appendChild(element("td", column.numeric ? "num" : "", text));
      });
      body.appendChild(tr);
    });
  }

  function renderPager() {
    pager.textContent = "";
    const pages = Math.max(1, Math.ceil(state.total / state.pageSize));
    const prev = element("button", "pager-btn", "← Previous");
    const next = element("button", "pager-btn", "Next →");
    prev.type = next.type = "button";
    prev.disabled = state.page <= 1;
    next.disabled = state.page >= pages;
    prev.addEventListener("click", () => { state.page -= 1; load(); });
    next.addEventListener("click", () => { state.page += 1; load(); });
    pager.append(prev, element("span", "pager-info", `Page ${state.page.toLocaleString()} of ${pages.toLocaleString()}`), next);
  }


  async function load() {
    const requestId = ++state.requestId;
    status.textContent = "Loading trips…";
    try {
      const result = await API.trips({
        ...state.filters, sort: state.sort, order: state.order, page: state.page, page_size: state.pageSize,
      });
      if (requestId !== state.requestId) return; // a newer request superseded this one
      state.total = result.total;
      renderRows(result.data);
      renderPager();
      updateSortIndicators();
      status.textContent = result.total === 0
        ? "No trips match these filters."
        : `${result.total.toLocaleString()} trips match. Select a row for details.`;
    } catch (error) {
      if (requestId !== state.requestId) return;
      status.textContent = "Could not load trips: " + error.message;
    }
  }


  async function showDetail(tripId) {
    dialog.textContent = "";
    dialog.appendChild(element("p", "", "Loading…"));
    dialog.showModal();
    try {
      const trip = (await API.trip(tripId)).data;
      dialog.textContent = "";
      dialog.appendChild(element("h3", "", "Trip " + trip.trip_id));
      const list = element("dl", "trip-detail-list");
      DETAIL_LABELS.forEach(([key, label]) => {
        const value = trip[key];
        list.append(element("dt", "", label), element("dd", "", value === null || value === undefined ? "n/a" : String(value)));
      });
      const close = element("button", "pager-btn", "Close");
      close.type = "button";
      close.addEventListener("click", () => dialog.close());
      dialog.append(list, close);
    } catch (error) {
      dialog.textContent = "";
      dialog.appendChild(element("p", "", "Could not load trip: " + error.message));
      const close = element("button", "pager-btn", "Close");
      close.type = "button";
      close.addEventListener("click", () => dialog.close());
      dialog.appendChild(close);
    }
  }


  function init(containerId) {
    build(containerId);
    updateSortIndicators();
    document.addEventListener("filters:changed", () => {
      reload(typeof getFilters === "function" ? getFilters() : {});
    });
    load();
  }


  function reload(filters) {
    state.filters = filters || {};
    state.page = 1;
    load();
  }

  return { init, reload };
})();


function initTripsTable(containerId) { TripsTable.init(containerId); }
function reloadTripsTable(filters) { TripsTable.reload(filters); }
