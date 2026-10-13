(function () {
    let refreshToken = 0;
    let ZoneRanking = "pickup";

    const byId = (id) => document.getElementById(id);
    const cardof = (id) => byId(id).closest(".card");

    function showStatus(message){
        const banner = byId("status");
        banner.textContent = message;
        banner.hidden = !message;
    }
    function setLoading(element, isloading){
        if (element) element.classlist.togle("is-loading", isloading);

    }

    async function loadCard(token, targets, request, render) {
    targets.forEach((element) => setLoading(element, true));
    try {
      const result = await request;
      if (token !== refreshToken) return;
      render(result.data);
    } catch (error) {
      if (token !== refreshToken) return;
      
      showStatus(error.status === 504 ? error.message
        : "Could not load part of the dashboard: " + error.message +
          ". Is the backend running and the database loaded?");
    } finally {
      if (token === refreshToken) targets.forEach((element) => setLoading(element, false));
    }
  }

  function refresh() {
    const token = ++refreshToken;
    const filters = getFilters();
    showStatus("");

    
    const parts = {};
    const renderInsightsWhenReady = () => {
      if (parts.summary && parts.hourly && parts.borough && parts.payment) Charts.renderInsights(parts);
    };
    const keep = (name) => (data) => { parts[name] = data; renderInsightsWhenReady(); };
    const insights = byId("insights");
    setLoading(insights, true);

    const jobs = [
      loadCard(token, [byId("kpis")], API.analytics("summary", filters),
        (data) => { Charts.renderKpis(data); keep("summary")(data); }),
      loadCard(token, [cardOf("chart-hourly")], API.analytics("hourly", filters),
        (data) => { Charts.renderHourly(data); keep("hourly")(data); }),
      loadCard(token, [cardOf("chart-daily")], API.analytics("daily", filters), Charts.renderDaily),
      loadCard(token, [cardOf("chart-borough")], API.analytics("borough", filters),
        (data) => { Charts.renderBorough(data); keep("borough")(data); }),
      loadCard(token, [cardOf("chart-payment")], API.analytics("payment-types", filters),
        (data) => { Charts.renderPayment(data); keep("payment")(data); }),
      loadCard(token, [byId("map").closest(".card")], API.analytics("zone-counts", filters), ZoneMap.update),
      loadCard(token, [cardOf("chart-zones")],
        API.analytics("top-zones", { ...filters, k: 10, by: zoneRanking }),
        (data) => Charts.renderTopZones(data, zoneRanking)),
      loadCard(token, [cardOf("top-routes")], API.analytics("top-routes", { ...filters, k: 10 }), Charts.renderRoutes),
    ];
    
    Promise.allSettled(jobs).then(() => { if (token === refreshToken) setLoading(insights, false); });
  }

  function wireZoneToggle() {
    document.querySelectorAll(".seg").forEach((button) => {
      button.addEventListener("click", () => {
        zoneRanking = button.dataset.by;
        document.querySelectorAll(".seg").forEach((other) =>
          other.classList.toggle("active", other === button));
        const token = refreshToken;  // a newer refresh() will supersede this
        loadCard(token, [cardOf("chart-zones")],
          API.analytics("top-zones", { ...getFilters(), k: 10, by: zoneRanking }),
          (data) => Charts.renderTopZones(data, zoneRanking));
      });
    });
  }

  async function start() {
    try {
      const zones = await API.zones();
      const boroughs = [...new Set(zones.data.map((zone) => zone.borough))]
        .filter((name) => name !== "Unknown")
        .sort();
      Filters.init(boroughs);
    } catch (error) {
      Filters.init([]);
      showStatus("Could not load the zone list: " + error.message);
    }

    initTripsTable("trips-table");
    wireZoneToggle();
    document.addEventListener("filters:changed", refresh);

    
    API.zonesGeoJSON().then((geojson) => ZoneMap.init(geojson)).catch((error) =>
      showStatus("Could not load the map: " + error.message));

    refresh();
  }

  document.addEventListener("DOMContentLoaded", start);
})();
