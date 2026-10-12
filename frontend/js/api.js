const API = (() => {
    const base = window.API_BASE || "";

    function queryString(params) {
        const search = new URLSearchParams();
        Object.entries(params || {}).forEach(([Key, value]) => {
            if (value !==undefined && value !== null && value !== "") search.append(Key, value);
        });
        const text = search.toString();
        return text ? "?" + text : "";
    }

    async function get(path, params) {
        const response = await fetch(base + path +queryString(params));
        if (!response.ok) {
            let message = response.statusText;
            try {
                message = (await response.json()).error || message;
            } catch (ignored) { /*body was not JSON */ }
            const error = new Error(message);
            error.status = response.status;
            throw error;
        }
        return response.json();

}


return {
    get,
    trips: (params) => get("/api/trips", params),
    trip: (id) => get("/api/trips/" + encodeURIComponent(id)),
    zones: () => get("/api/zones"),
    zonesGeoJSON: () => get("/api/zones/geojson"),
    analytics: (name, params) => get("/api/analytics/" + name, params),
};
})();
