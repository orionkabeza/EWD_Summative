
const ZoneMap = (() => {
  const STOPS = ["#fff7bc", "#fec44f", "#fe9929", "#d95f0e", "#993404"];
  const NO_DATA = "#e5e7eb";
  let map, layer, legendBody;
  let rowsById = new Map();
  let geojsonReady = false;

  function mix(hexA, hexB, t) {
    const a = parseInt(hexA.slice(1), 16);
    const b = parseInt(hexB.slice(1), 16);
    const channel = (shift) => Math.round(((a >> shift) & 255) * (1 - t) + ((b >> shift) & 255) * t);
    return "rgb(" + channel(16) + "," + channel(8) + "," + channel(0) + ")";
  }

  function colourAt(t) {
    const clamped = Math.min(1, Math.max(0, t));
    const scaled = clamped * (STOPS.length - 1);
    const index = Math.min(STOPS.length - 2, Math.floor(scaled));
    return mix(STOPS[index], STOPS[index + 1], scaled - index);
  }

  function metric() { return document.getElementById("map-metric").value; }

  function range() {
    const values = [...rowsById.values()].map((row) => row[metric()]).filter((v) => v !== null && v !== undefined);
    return { min: values.length ? Math.min(...values) : 0, max: values.length ? Math.max(...values) : 0 };
  }

  function position(value, bounds) {
    if (metric() === "trips") return Math.sqrt(value / (bounds.max || 1));
    return bounds.max === bounds.min ? 0.5 : (value - bounds.min) / (bounds.max - bounds.min);
  }

  function styleFor(feature, bounds) {
    const row = rowsById.get(feature.properties.location_id);
    const value = row ? row[metric()] : null;
    const hasValue = value !== null && value !== undefined;
    return {
      fillColor: hasValue ? colourAt(position(value, bounds)) : NO_DATA,
      fillOpacity: hasValue ? 0.85 : 0.5,
      color: "#ffffff",
      weight: 1,
    };
  }

  function popupFor(feature) {
    const row = rowsById.get(feature.properties.location_id);
    const box = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = feature.properties.zone;
    const borough = document.createElement("div");
    borough.textContent = feature.properties.borough;
    const stats = document.createElement("div");
    stats.textContent = row
      ? row.trips.toLocaleString("en-US") + " pickups · avg fare $" + row.avg_fare.toFixed(2)
      : "No pickups in this selection";
    box.append(title, borough, stats);
    return box;
  }

  function updateLegend(bounds) {
    if (!legendBody) return;
    const isTrips = metric() === "trips";
    legendBody.textContent = "";
    const title = document.createElement("div");
    title.textContent = isTrips ? "Pickups per zone" : "Average fare";
    const bar = document.createElement("div");
    bar.className = "legend-bar";
    const scale = document.createElement("div");
    scale.className = "legend-scale";
    const low = document.createElement("span");
    const high = document.createElement("span");
    low.textContent = isTrips ? "0" : "$" + bounds.min.toFixed(0);
    high.textContent = isTrips ? bounds.max.toLocaleString("en-US") : "$" + bounds.max.toFixed(0);
    scale.append(low, high);
    legendBody.append(title, bar, scale);
  }

  function restyle() {
    if (!layer) return;
    const bounds = range();
    layer.setStyle((feature) => styleFor(feature, bounds));
    updateLegend(bounds);
  }

  function init(geojson) {
    const container = document.getElementById("map");
    if (typeof L === "undefined") {
      container.textContent = "The map library could not be loaded. Check your internet connection.";
      return;
    }
    map = L.map(container, { zoomSnap: 0.25 }).setView([40.72, -73.95], 10.5);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap contributors", maxZoom: 18,
    }).addTo(map);

    layer = L.geoJSON(geojson, {
      style: (feature) => styleFor(feature, range()),
      onEachFeature: (feature, shape) => {
        shape.on("mouseover", () => { shape.setStyle({ weight: 2.5, color: "#14213d" }); shape.bringToFront(); });
        shape.on("mouseout", () => layer.resetStyle(shape));
        shape.on("click", (event) => L.popup().setLatLng(event.latlng).setContent(popupFor(feature)).openOn(map));
      },
    }).addTo(map);

    const legend = L.control({ position: "bottomright" });
    legend.onAdd = () => {
      legendBody = L.DomUtil.create("div", "legend");
      return legendBody;
    };
    legend.addTo(map);

    document.getElementById("map-metric").addEventListener("change", restyle);
    geojsonReady = true;
    restyle();
  }

  function update(rows) {
    rowsById = new Map(rows.map((row) => [row.location_id, row]));
    if (geojsonReady) restyle();
  }

  return { init, update };
})();



















