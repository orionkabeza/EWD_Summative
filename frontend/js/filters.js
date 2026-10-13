const Filters = (() => {
 
  const FIELDS = {
    start: "f-start",
    end: "f-end",
    hour_min: "f-hour-min",
    hour_max: "f-hour-max",
    min_distance: "f-min-distance",
    max_distance: "f-max-distance",
    min_fare: "f-min-fare",
    max_fare: "f-max-fare",
    pu_borough: "f-borough",
    payment_type_id: "f-payment",
  };

  function read() {
    const filters = {};
    Object.entries(FIELDS).forEach(([param, id]) => {
      const value = document.getElementById(id).value.trim();
      if (value !== "") filters[param] = value;
    });
    return filters;
  }

  
  function validate(filters) {
    const num = (key) => (filters[key] === undefined ? null : Number(filters[key]));
    if (filters.start && filters.end && filters.start > filters.end) {
      return "The start date must not be after the end date.";
    }
    if (num("hour_min") !== null && num("hour_max") !== null && num("hour_min") > num("hour_max")) {
      return "The start hour must not be after the end hour.";
    }
    if (num("min_distance") !== null && num("max_distance") !== null && num("min_distance") > num("max_distance")) {
      return "Minimum distance must not be larger than maximum distance.";
    }
    if (num("min_fare") !== null && num("max_fare") !== null && num("min_fare") > num("max_fare")) {
      return "Minimum fare must not be larger than maximum fare.";
    }
    return "";
  }

  function announce(filters) {
    document.dispatchEvent(new CustomEvent("filters:changed", { detail: filters }));
  }

  function fillHourOptions() {
    ["f-hour-min", "f-hour-max"].forEach((id) => {
      const select = document.getElementById(id);
      for (let hour = 0; hour < 24; hour += 1) {
        const option = document.createElement("option");
        option.value = String(hour);
        option.textContent = String(hour).padStart(2, "0") + ":00";
        select.appendChild(option);
      }
    });
  }

  function fillBoroughs(boroughs) {
    const select = document.getElementById("f-borough");
    boroughs.forEach((name) => {
      const option = document.createElement("option");
      option.value = name;
      option.textContent = name;
      select.appendChild(option);
    });
  }

  function init(boroughs) {
    fillHourOptions();
    fillBoroughs(boroughs);
    const message = document.getElementById("filter-message");

    document.getElementById("filters").addEventListener("submit", (event) => {
      event.preventDefault();
      const filters = read();
      const problem = validate(filters);
      message.textContent = problem;
      if (!problem) announce(filters);
    });

    document.getElementById("reset-btn").addEventListener("click", () => {
      document.getElementById("filters").reset();
      message.textContent = "";
      announce({});
    });
  }

  return { init, read };
})();

function getFilters() { return Filters.read(); }
