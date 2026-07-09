// ── State coordinates for choropleth approximation ──
const STATE_COORDS = {
  AL:[32.8,-86.8],AK:[64.2,-152.5],AZ:[34.0,-111.1],AR:[35.2,-91.8],CA:[36.8,-119.4],
  CO:[39.1,-105.4],CT:[41.6,-72.7],DE:[39.0,-75.5],FL:[27.8,-81.8],GA:[32.2,-83.7],
  HI:[19.9,-155.6],ID:[44.1,-114.7],IL:[40.3,-89.0],IN:[40.3,-86.1],IA:[42.0,-93.2],
  KS:[38.5,-98.8],KY:[37.8,-84.3],LA:[31.2,-92.1],ME:[45.3,-69.4],MD:[39.0,-76.6],
  MA:[42.4,-71.4],MI:[44.3,-84.5],MN:[46.7,-94.7],MS:[32.7,-89.7],MO:[38.6,-92.6],
  MT:[46.9,-110.4],NE:[41.1,-98.3],NV:[38.8,-116.4],NH:[43.2,-71.6],NJ:[40.1,-74.5],
  NM:[34.5,-105.9],NY:[43.0,-75.0],NC:[35.8,-79.0],ND:[47.5,-101.0],OH:[40.4,-82.9],
  OK:[35.0,-97.1],OR:[43.8,-120.6],PA:[41.2,-77.2],RI:[41.6,-71.5],SC:[33.8,-81.2],
  SD:[43.9,-99.4],TN:[35.5,-86.6],TX:[31.1,-97.6],UT:[39.3,-111.1],VT:[44.6,-72.6],
  VA:[37.8,-78.2],WA:[47.7,-120.7],WV:[38.6,-80.6],WI:[43.8,-88.8],WY:[43.1,-107.6],
  DC:[38.9,-77.0],
};

// ── Metric config ──
const METRICS = {
  zhvi_current: { label: "Median Home Price", fmt: "$", dec: 0 },
  zori_rent: { label: "Median Rent", fmt: "$", dec: 0 },
  median_hh_income: { label: "Median Income", fmt: "$", dec: 0 },
  price_to_income: { label: "Price-to-Income", fmt: "x", dec: 1 },
  payment_pct_income: { label: "Payment % Income", fmt: "%", dec: 1 },
  monthly_payment: { label: "Est. Monthly Payment", fmt: "$", dec: 0 },
  price_chg_1yr_pct: { label: "1Y Price Change", fmt: "%", dec: 1 },
  price_chg_5yr_pct: { label: "5Y Price Change", fmt: "%", dec: 1 },
  r_months_supply: { label: "Months of Supply", fmt: "", dec: 1 },
  r_median_dom: { label: "Days on Market", fmt: "", dec: 0 },
  r_price_drops: { label: "% Price Cuts", fmt: "%", dec: 1 },
  r_sold_above_list: { label: "% Sold Above List", fmt: "%", dec: 1 },
  population: { label: "Population", fmt: ",", dec: 0 },
  pop_growth_ann_pct: { label: "Pop Growth", fmt: "%", dec: 1 },
  income_growth_ann_pct: { label: "Income Growth", fmt: "%", dec: 1 },
  migration_rate_per_1000: { label: "Net Migration", fmt: "", dec: 1 },
  bachelors_pct: { label: "Bachelor's %", fmt: "%", dec: 1 },
  poverty_rate: { label: "Poverty Rate", fmt: "%", dec: 1 },
  homeownership_rate: { label: "Homeownership", fmt: "%", dec: 1 },
  median_age: { label: "Median Age", fmt: "", dec: 1 },
  mean_commute_min: { label: "Avg Commute", fmt: " min", dec: 0 },
  fema_risk_score: { label: "Disaster Risk", fmt: "", dec: 1 },
  median_aqi: { label: "Air Quality Index", fmt: "", dec: 0 },
  electricity_cents_kwh: { label: "Electricity", fmt: " ¢/kWh", dec: 1 },
  rpp: { label: "Cost of Living", fmt: "", dec: 1 },
  pct_wfh: { label: "% Work from Home", fmt: "%", dec: 1 },
  price_to_rent: { label: "Price-to-Rent", fmt: "x", dec: 1 },
  gross_rental_yield: { label: "Rental Yield", fmt: "%", dec: 1 },
};

// Lower = better (green) for these metrics
const REVERSE_METRICS = new Set([
  "zhvi_current",          // cheaper homes = better
  "zori_rent",             // cheaper rent = better
  "price_to_income",       // lower ratio = more affordable
  "payment_pct_income",    // lower % = more affordable
  "monthly_payment",       // lower payment = better
  "price_to_rent",         // lower = buying favored over renting
  "poverty_rate",          // lower poverty = better
  "fema_risk_score",       // lower risk = better
  "median_aqi",            // lower AQI = cleaner air
  "r_median_dom",          // fewer days = hotter market
  "mean_commute_min",      // shorter commute = better
  "electricity_cents_kwh", // cheaper energy = better
  "rpp",                   // lower cost of living = better
]);

const KEY_STATS = ["zhvi_current", "median_hh_income", "population"];

const CATEGORIES = {
  affordability: ["zori_rent", "price_to_income", "payment_pct_income", "monthly_payment", "price_to_rent", "gross_rental_yield"],
  market: ["price_chg_1yr_pct", "price_chg_5yr_pct", "r_months_supply", "r_median_dom", "r_price_drops", "r_sold_above_list"],
  economy: ["pop_growth_ann_pct", "income_growth_ann_pct", "migration_rate_per_1000", "bachelors_pct", "poverty_rate", "homeownership_rate", "median_age", "pct_wfh"],
  quality: ["fema_risk_score", "median_aqi", "mean_commute_min", "electricity_cents_kwh", "rpp"],
};

const COMPARE_SECTIONS = [
  { label: "Affordability", keys: ["zhvi_current", "zori_rent", "median_hh_income", "price_to_income", "payment_pct_income", "monthly_payment"] },
  { label: "Market", keys: ["price_chg_1yr_pct", "price_chg_5yr_pct", "r_months_supply", "r_median_dom", "r_price_drops", "r_sold_above_list"] },
  { label: "Economy", keys: ["population", "pop_growth_ann_pct", "income_growth_ann_pct", "migration_rate_per_1000", "bachelors_pct", "poverty_rate", "homeownership_rate", "pct_wfh"] },
  { label: "Quality of Life", keys: ["fema_risk_score", "median_aqi", "mean_commute_min", "electricity_cents_kwh", "rpp"] },
];

const COMPARE_KEYS = COMPARE_SECTIONS.flatMap(s => s.keys);

// ── Formatting ──
// Fields stored as 0-1 that should display as 0-100%
const SCALE_100 = new Set(["r_price_drops", "r_sold_above_list", "r_sale_to_list"]);

function fmtVal(val, key) {
  if (val == null || isNaN(val)) return "—";
  let v = val;
  if (SCALE_100.has(key)) v = val * 100;
  const m = METRICS[key];
  if (!m) return String(v);
  if (m.fmt === "$") return "$" + v.toLocaleString("en-US", { maximumFractionDigits: m.dec });
  if (m.fmt === "%") return v.toFixed(m.dec) + "%";
  if (m.fmt === "x") return v.toFixed(m.dec) + "x";
  if (m.fmt === ",") return v.toLocaleString("en-US");
  return v.toFixed(m.dec) + m.fmt;
}

const METRIC_TIPS = {
  zhvi_current: "Zillow Home Value Index — median estimated home value for the metro area.",
  zori_rent: "Zillow Observed Rent Index — median monthly rent for the metro area.",
  median_hh_income: "Median household income from Census ACS.",
  price_to_income: "Home price divided by annual income. Lower = more affordable. Under 3x is historically normal.",
  payment_pct_income: "Estimated monthly mortgage payment as a % of monthly income. Under 28% is considered comfortable.",
  monthly_payment: "Estimated monthly mortgage payment (20% down, 30yr fixed at current rate).",
  price_to_rent: "Home price divided by annual rent. Under 15 favors buying, over 20 favors renting.",
  gross_rental_yield: "Annual rent as a % of home price. Higher = better for investors.",
  price_chg_1yr_pct: "Home price change over the past 12 months.",
  price_chg_5yr_pct: "Home price change over the past 5 years.",
  r_months_supply: "Months of inventory at current sales pace. Under 4 = seller's market, over 6 = buyer's market.",
  r_median_dom: "Median days on market before a home sells.",
  r_price_drops: "Percentage of active listings with a price reduction.",
  r_sold_above_list: "Percentage of homes that sold above their list price.",
  population: "Metro area population from Census ACS.",
  pop_growth_ann_pct: "Annual population growth rate.",
  income_growth_ann_pct: "Annual median household income growth rate.",
  migration_rate_per_1000: "Net migration per 1,000 residents (IRS tax return data).",
  bachelors_pct: "% of adults with a bachelor's degree or higher.",
  poverty_rate: "% of population below the poverty line.",
  homeownership_rate: "% of occupied housing units that are owner-occupied.",
  median_age: "Median age of the population.",
  pct_wfh: "% of workers who work from home.",
  fema_risk_score: "FEMA National Risk Index — composite natural disaster risk (0-100, higher = more risk).",
  median_aqi: "Median Air Quality Index. Lower is better. Under 50 = good air quality.",
  mean_commute_min: "Average one-way commute time in minutes.",
  electricity_cents_kwh: "Average residential electricity cost in cents per kWh.",
  rpp: "Regional Price Parity — cost of living relative to national average (100). Over 100 = more expensive.",
};

function statCard(key, val) {
  const m = METRICS[key];
  const infoBtn = METRIC_TIPS[key] ? `<button class="info-btn" onclick="this.parentElement.nextElementSibling.nextElementSibling.classList.toggle('show')">ⓘ</button>` : "";
  const infoText = METRIC_TIPS[key] ? `<div class="info-text">${METRIC_TIPS[key]}</div>` : "";
  return `<div class="stat-card"><div class="label">${m ? m.label : key}${infoBtn}</div><div class="value">${fmtVal(val, key)}</div>${infoText}</div>`;
}

// ── Color scale ──
function getColor(val, min, max, reverse) {
  if (val == null || isNaN(val)) return "#d1d5db";
  let t = (val - min) / (max - min || 1);
  // For normal metrics (higher=better): low=red, high=green
  // For reverse metrics (lower=better): low=green, high=red
  if (!reverse) t = 1 - t;
  // t=0 → green, t=1 → red
  const r = t < 0.5 ? Math.round(255 * t * 2) : 255;
  const g = t < 0.5 ? 255 : Math.round(255 * (1 - (t - 0.5) * 2));
  return `rgb(${r},${g},80)`;
}

// State name → abbreviation
const STATE_ABBR = {
  "Alabama":"AL","Alaska":"AK","Arizona":"AZ","Arkansas":"AR","California":"CA",
  "Colorado":"CO","Connecticut":"CT","Delaware":"DE","Florida":"FL","Georgia":"GA",
  "Hawaii":"HI","Idaho":"ID","Illinois":"IL","Indiana":"IN","Iowa":"IA","Kansas":"KS",
  "Kentucky":"KY","Louisiana":"LA","Maine":"ME","Maryland":"MD","Massachusetts":"MA",
  "Michigan":"MI","Minnesota":"MN","Mississippi":"MS","Missouri":"MO","Montana":"MT",
  "Nebraska":"NE","Nevada":"NV","New Hampshire":"NH","New Jersey":"NJ","New Mexico":"NM",
  "New York":"NY","North Carolina":"NC","North Dakota":"ND","Ohio":"OH","Oklahoma":"OK",
  "Oregon":"OR","Pennsylvania":"PA","Rhode Island":"RI","South Carolina":"SC",
  "South Dakota":"SD","Tennessee":"TN","Texas":"TX","Utah":"UT","Vermont":"VT",
  "Virginia":"VA","Washington":"WA","West Virginia":"WV","Wisconsin":"WI","Wyoming":"WY",
  "District of Columbia":"DC","Puerto Rico":"PR",
};

// ── Globals ──
let data = [];
let stateGeo = null;
let stateData = {};
let map;
let markers = L.layerGroup();
let stateLayer = null;
let currentView = "metros"; // "metros" or "states"

// ── Init ──
async function init() {
  const [dataResp, geoResp] = await Promise.all([
    fetch("assets/data.json"),
    fetch("assets/us-states.json"),
  ]);
  data = await dataResp.json();
  stateGeo = await geoResp.json();

  // Use pre-computed coords, fallback to state center
  data.forEach(d => {
    if (!d._lat || !d._lon) {
      const base = STATE_COORDS[d.state_abbr] || [39.8, -98.6];
      d._lat = base[0];
      d._lon = base[1];
    }
  });

  // Pre-compute state medians
  const byState = {};
  data.forEach(d => {
    if (!byState[d.state_abbr]) byState[d.state_abbr] = [];
    byState[d.state_abbr].push(d);
  });
  Object.keys(byState).forEach(st => {
    const arr = byState[st];
    const med = {};
    Object.keys(METRICS).forEach(k => {
      const vals = arr.map(d => d[k]).filter(v => v != null && !isNaN(v));
      if (vals.length) {
        vals.sort((a, b) => a - b);
        med[k] = vals[Math.floor(vals.length / 2)];
      }
    });
    med._count = arr.length;
    stateData[st] = med;
  });

  initMap();
  populateControls();
  updateMap();
  setupEvents();
}

function initMap() {
  map = L.map("map", {
    center: [39.0, -96.0],
    zoom: 4,
    zoomControl: true,
    attributionControl: false,
  });
  L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
    maxZoom: 18,
  }).addTo(map);
  markers.addTo(map);
}

function populateControls() {
  // Last updated
  const dataDate = data[0]?._data_date;
  document.getElementById("lastUpdated").textContent = dataDate
    ? new Date(dataDate + "T00:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
    : "Unknown";

  // Metro compare selects
  const names = data.map(d => d.RegionName).sort();
  ["compareA", "compareB"].forEach((id, i) => {
    const sel = document.getElementById(id);
    names.forEach((n, j) => {
      const opt = document.createElement("option");
      opt.value = n; opt.textContent = n;
      if (j === i) opt.selected = true;
      sel.appendChild(opt);
    });
  });

  // State compare selects
  const states = [...new Set(data.map(d => d.state_abbr))].filter(Boolean).sort();
  ["compareStateA", "compareStateB"].forEach((id, i) => {
    const sel = document.getElementById(id);
    const defaults = ["IL", "TX"];
    states.forEach((s, j) => {
      const opt = document.createElement("option");
      opt.value = s; opt.textContent = s;
      if (s === defaults[i]) opt.selected = true;
      sel.appendChild(opt);
    });
  });
}

function updateLegend(metric, min, max, reverse) {
  const m = METRICS[metric];
  document.getElementById("legendTitle").textContent = m ? m.label : metric;

  // Gradient: always green(good) on left, red(bad) on right
  document.getElementById("legendGradient").style.background = "linear-gradient(to right, rgb(80,255,80), rgb(255,255,80), rgb(255,80,80))";

  // Labels: for reverse metrics (lower=better), good(left)=low, bad(right)=high
  // For normal metrics (higher=better), good(left)=high, bad(right)=low
  const minLabel = reverse ? fmtVal(min, metric) : fmtVal(max, metric);
  const maxLabel = reverse ? fmtVal(max, metric) : fmtVal(min, metric);
  document.getElementById("legendMin").textContent = minLabel;
  document.getElementById("legendMax").textContent = maxLabel;
}

function updateMap() {
  const metric = document.getElementById("mapMetric").value;
  const reverse = REVERSE_METRICS.has(metric);

  // Clear both layers
  markers.clearLayers();
  if (stateLayer) { map.removeLayer(stateLayer); stateLayer = null; }

  if (currentView === "states") {
    // State choropleth
    const vals = Object.values(stateData).map(d => d[metric]).filter(v => v != null);
    const min = Math.min(...vals);
    const max = Math.max(...vals);

    updateLegend(metric, min, max, reverse);

    stateLayer = L.geoJSON(stateGeo, {
      style: feature => {
        const abbr = STATE_ABBR[feature.properties.name];
        const sd = stateData[abbr];
        const val = sd ? sd[metric] : null;
        return {
          fillColor: getColor(val, min, max, reverse),
          fillOpacity: 0.7,
          color: "white",
          weight: 1.5,
          opacity: 0.8,
        };
      },
      onEachFeature: (feature, layer) => {
        const abbr = STATE_ABBR[feature.properties.name];
        const sd = stateData[abbr];
        const val = sd ? sd[metric] : null;
        const count = sd ? sd._count : 0;
        layer.bindTooltip(
          `<b>${feature.properties.name}</b><br>${METRICS[metric]?.label || metric}: ${fmtVal(val, metric)}<br>${count} metro${count !== 1 ? "s" : ""}`,
          { className: "dark-tooltip", sticky: true }
        );
      },
    }).addTo(map);
  } else {
    // Metro bubbles
    const vals = data.map(d => d[metric]).filter(v => v != null && !isNaN(v));
    const min = Math.min(...vals);
    const max = Math.max(...vals);

    updateLegend(metric, min, max, reverse);

    data.forEach(d => {
      const val = d[metric];
      const color = getColor(val, min, max, reverse);
      const pop = d.population || 50000;
      const radius = Math.max(4, Math.min(18, Math.sqrt(pop / 50000) * 6));

      const marker = L.circleMarker([d._lat, d._lon], {
        radius, fillColor: color, fillOpacity: 0.75,
        color: "rgba(255,255,255,0.5)", weight: 1,
      });

      marker.bindTooltip(
        `<b>${d.RegionName}</b><br>${METRICS[metric]?.label || metric}: ${fmtVal(val, metric)}<br>Pop: ${(d.population || 0).toLocaleString()}`,
        { className: "dark-tooltip" }
      );

      marker.on("click", () => showDetail(d));
      markers.addLayer(marker);
    });
  }
}

function showDetail(d) {
  const card = document.getElementById("detailCard");
  card.classList.remove("hidden");
  document.getElementById("cardTitle").textContent = d.RegionName;
  document.getElementById("cardStats").innerHTML = KEY_STATS.map(k => statCard(k, d[k])).join("");
  showTab("affordability", d);
  card._metro = d;
}

function showTab(cat, d) {
  const content = document.getElementById("cardTabContent");
  const keys = CATEGORIES[cat] || [];
  const cards = keys.filter(k => METRICS[k]).map(k => statCard(k, d[k])).join("");

  // Source date for this category
  const src = d._source_dates || {};
  const catSources = {
    affordability: src.zillow ? `Prices: ${src.zillow} · Census: ${src.census || "—"}` : "",
    market: src.zillow ? `Zillow/Redfin: ${src.zillow}` : "",
    economy: src.census ? `Census ACS: ${src.census} · Migration: ${src.migration || "—"}` : "",
    quality: [src.fema ? `FEMA: ${src.fema}` : "", src.aqi ? `AQI: ${src.aqi}` : ""].filter(Boolean).join(" · "),
  };
  const sourceNote = catSources[cat] ? `<div style="font-size:0.6rem;color:#94a3b8;margin-top:8px;text-align:center">Data as of: ${catSources[cat]}</div>` : "";

  content.innerHTML = cards + sourceNote;
  document.querySelectorAll(".ctab").forEach(t => {
    t.classList.toggle("active", t.dataset.tab === cat);
  });
}

function buildCompareTable(dataA, dataB, nameA, nameB) {
  let html = `<table><thead><tr><th>Metric</th><th>${nameA}</th><th>${nameB}</th></tr></thead><tbody>`;
  COMPARE_SECTIONS.forEach(section => {
    html += `<tr><td colspan="3" style="font-weight:700;color:#4f46e5;padding:10px 5px 4px;font-size:0.65rem;letter-spacing:0.08em;text-transform:uppercase;border-bottom:none">${section.label}</td></tr>`;
    section.keys.forEach(k => {
      if (!METRICS[k]) return;
      html += `<tr><td>${METRICS[k].label}</td><td>${fmtVal(dataA[k], k)}</td><td>${fmtVal(dataB[k], k)}</td></tr>`;
    });
  });
  html += "</tbody></table>";
  return html;
}

function updateCompare() {
  const a = data.find(d => d.RegionName === document.getElementById("compareA").value);
  const b = data.find(d => d.RegionName === document.getElementById("compareB").value);
  if (!a || !b) return;
  document.getElementById("compareBody").innerHTML = buildCompareTable(a, b, a.RegionName.split(",")[0], b.RegionName.split(",")[0]);
}

function updateStateCompare() {
  const sa = document.getElementById("compareStateA").value;
  const sb = document.getElementById("compareStateB").value;
  const sdA = stateData[sa];
  const sdB = stateData[sb];
  if (!sdA || !sdB) return;
  document.getElementById("compareStateBody").innerHTML = buildCompareTable(sdA, sdB, sa, sb);
}

function setupEvents() {
  document.getElementById("mapMetric").addEventListener("change", updateMap);

  // View toggle
  document.getElementById("viewMetros").addEventListener("click", () => {
    currentView = "metros";
    document.getElementById("viewMetros").classList.add("active");
    document.getElementById("viewStates").classList.remove("active");
    updateMap();
  });

  document.getElementById("viewStates").addEventListener("click", () => {
    currentView = "states";
    document.getElementById("viewStates").classList.add("active");
    document.getElementById("viewMetros").classList.remove("active");
    updateMap();
  });

  // Compare — metro
  document.getElementById("compareA").addEventListener("change", updateCompare);
  document.getElementById("compareB").addEventListener("change", updateCompare);

  // Compare — state
  document.getElementById("compareStateA").addEventListener("change", updateStateCompare);
  document.getElementById("compareStateB").addEventListener("change", updateStateCompare);

  // Compare tab toggle
  document.getElementById("cmpTabMetro").addEventListener("click", () => {
    document.getElementById("cmpTabMetro").classList.add("active");
    document.getElementById("cmpTabState").classList.remove("active");
    document.getElementById("cmpMetroView").style.display = "";
    document.getElementById("cmpStateView").style.display = "none";
  });

  document.getElementById("cmpTabState").addEventListener("click", () => {
    document.getElementById("cmpTabState").classList.add("active");
    document.getElementById("cmpTabMetro").classList.remove("active");
    document.getElementById("cmpStateView").style.display = "";
    document.getElementById("cmpMetroView").style.display = "none";
    updateStateCompare();
  });

  // Card close
  document.getElementById("cardClose").addEventListener("click", () => {
    document.getElementById("detailCard").classList.add("hidden");
  });

  // Compare toggle
  document.getElementById("compareToggle").addEventListener("click", () => {
    document.getElementById("comparePanel").classList.remove("hidden");
    updateCompare();
  });

  document.getElementById("compareClose").addEventListener("click", () => {
    document.getElementById("comparePanel").classList.add("hidden");
  });

  // Tabs
  document.querySelectorAll(".ctab").forEach(tab => {
    tab.addEventListener("click", () => {
      const card = document.getElementById("detailCard");
      if (card._metro) showTab(tab.dataset.tab, card._metro);
    });
  });

  // Search
  const searchInput = document.getElementById("metroSearch");
  const searchResults = document.getElementById("searchResults");

  searchInput.addEventListener("input", () => {
    const q = searchInput.value.toLowerCase().trim();
    if (q.length < 2) { searchResults.classList.remove("active"); return; }

    const matches = data.filter(d => d.RegionName.toLowerCase().includes(q)).slice(0, 8);
    if (matches.length === 0) { searchResults.classList.remove("active"); return; }

    searchResults.innerHTML = matches.map(d =>
      `<div class="item" data-name="${d.RegionName}">${d.RegionName}</div>`
    ).join("");
    searchResults.classList.add("active");

    searchResults.querySelectorAll(".item").forEach(item => {
      item.addEventListener("click", () => {
        const metro = data.find(d => d.RegionName === item.dataset.name);
        if (metro) {
          showDetail(metro);
          map.setView([metro._lat, metro._lon], 8);
        }
        searchResults.classList.remove("active");
        searchInput.value = item.dataset.name;
      });
    });
  });

  searchInput.addEventListener("blur", () => {
    setTimeout(() => searchResults.classList.remove("active"), 200);
  });
}

// ── Dark tooltip style ──
const style = document.createElement("style");
style.textContent = `.dark-tooltip { background: white !important; color: #1e293b !important; border: 1px solid #e2e8f0 !important; border-radius: 6px !important; font-family: Inter, sans-serif !important; font-size: 0.8rem !important; padding: 8px 12px !important; box-shadow: 0 4px 16px rgba(0,0,0,0.1) !important; } .dark-tooltip::before { border-top-color: #e2e8f0 !important; }`;
document.head.appendChild(style);

// ── Go ──
init();
