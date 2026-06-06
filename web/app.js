// API base URL — empty string = same origin (local ./run_app.sh or Render full deploy)
// For Vercel frontend + Render API: set to "https://your-app.onrender.com"
const API = "";

const INT_FIELDS = [
  "SEX", "EDUCATION", "MARRIAGE", "RISK_RATING",
  "PAY_0", "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6",
];

const FLOAT_FIELDS = [
  "LIMIT_BAL", "AGE",
  "BILL_AMT1", "BILL_AMT2", "BILL_AMT3", "BILL_AMT4", "BILL_AMT5", "BILL_AMT6",
  "PAY_AMT1", "PAY_AMT2", "PAY_AMT3", "PAY_AMT4", "PAY_AMT5", "PAY_AMT6",
];

const PAY_COLS = ["PAY_0", "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6"];

const LOW_RISK_SAMPLE = {
  LIMIT_BAL: 200000,
  SEX: 2,
  EDUCATION: 2,
  MARRIAGE: 1,
  AGE: 42,
  PAY_0: -1,
  PAY_2: -1,
  PAY_3: -1,
  PAY_4: -1,
  PAY_5: -1,
  PAY_6: -1,
  BILL_AMT1: 5000,
  BILL_AMT2: 4200,
  BILL_AMT3: 3800,
  BILL_AMT4: 3500,
  BILL_AMT5: 3200,
  BILL_AMT6: 3000,
  PAY_AMT1: 5000,
  PAY_AMT2: 4200,
  PAY_AMT3: 3800,
  PAY_AMT4: 3500,
  PAY_AMT5: 3200,
  PAY_AMT6: 3000,
  RISK_RATING: 1,
  CITY: "City_1",
};

const HIGH_RISK_SAMPLE = {
  LIMIT_BAL: 50000,
  SEX: 2,
  EDUCATION: 2,
  MARRIAGE: 2,
  AGE: 30,
  PAY_0: 2,
  PAY_2: 2,
  PAY_3: 2,
  PAY_4: 2,
  PAY_5: 2,
  PAY_6: 2,
  BILL_AMT1: 50000,
  BILL_AMT2: 48000,
  BILL_AMT3: 45000,
  BILL_AMT4: 42000,
  BILL_AMT5: 40000,
  BILL_AMT6: 38000,
  PAY_AMT1: 0,
  PAY_AMT2: 0,
  PAY_AMT3: 0,
  PAY_AMT4: 0,
  PAY_AMT5: 0,
  PAY_AMT6: 0,
  RISK_RATING: 3,
  CITY: "City_23",
};

let lastPayload = null;
let lastResult = null;

function formToPayload(form) {
  const data = new FormData(form);
  const payload = { CITY: data.get("CITY") };
  for (const k of INT_FIELDS) payload[k] = parseInt(data.get(k), 10);
  for (const k of FLOAT_FIELDS) payload[k] = parseFloat(data.get(k));
  return payload;
}

function setFormValues(form, values) {
  for (const [k, v] of Object.entries(values)) {
    const el = form.elements[k];
    if (el) el.value = v;
  }
}

function updateGauge(prob, level) {
  const arc = document.getElementById("gauge-arc");
  const pct = document.getElementById("prob-pct");
  const maxOffset = 251;
  arc.style.strokeDashoffset = String(maxOffset * (1 - prob));
  const colors = { low: "#4ade80", medium: "#fbbf24", high: "#f87171" };
  arc.style.stroke = colors[level] || "var(--accent)";
  pct.textContent = `${(prob * 100).toFixed(1)}%`;
}

function renderPaySummary(summary) {
  const el = document.getElementById("pay-summary");
  if (!summary) {
    el.classList.add("hidden");
    return;
  }
  el.classList.remove("hidden");
  const trendClass = summary.trend === "improving" ? "good" : summary.trend === "worsening" ? "bad" : "";
  el.innerHTML = `
    <div class="pay-stat"><span>Late months</span><strong>${summary.months_late}/6</strong></div>
    <div class="pay-stat"><span>Worst delay</span><strong>${summary.worst_delay}</strong></div>
    <div class="pay-stat ${trendClass}"><span>Trend</span><strong>${summary.trend}</strong></div>
  `;
}

function showResult(data) {
  document.getElementById("result-empty").classList.add("hidden");
  document.getElementById("error-box").classList.add("hidden");
  document.getElementById("result-content").classList.remove("hidden");

  const pill = document.getElementById("risk-pill");
  pill.textContent = data.risk_label;
  pill.className = `risk-pill ${data.risk_level}`;

  updateGauge(data.default_probability, data.risk_level);

  document.getElementById("model-used").textContent =
    `${data.model_name} · threshold ${(data.threshold ?? 0.5).toFixed(2)}`;

  renderPaySummary(data.payment_summary);

  const list = document.getElementById("drivers-list");
  list.innerHTML = "";
  for (const d of data.top_drivers || []) {
    const li = document.createElement("li");
    li.innerHTML = `<span>${d.feature}</span><span>${d.score}</span>`;
    list.appendChild(li);
  }

  const recs = document.getElementById("recommendations-list");
  recs.innerHTML = "";
  for (const tip of data.recommendations || []) {
    const li = document.createElement("li");
    li.textContent = tip;
    recs.appendChild(li);
  }

  document.getElementById("whatif-btn").disabled = false;
  document.getElementById("whatif-results").classList.add("hidden");
  lastResult = data;
}

function showError(msg) {
  document.getElementById("result-content").classList.add("hidden");
  const box = document.getElementById("error-box");
  box.textContent = msg;
  box.classList.remove("hidden");
}

function buildWhatIfScenarios(payload) {
  const scenarios = [];

  if (payload.PAY_0 > 0) {
    scenarios.push({
      label: "If latest payment becomes current (PAY_0 → 0)",
      changes: { PAY_0: 0 },
    });
    scenarios.push({
      label: "If client pays ahead of schedule (PAY_0 → -1)",
      changes: { PAY_0: -1 },
    });
  } else if (payload.PAY_0 === 0) {
    scenarios.push({
      label: "If client pays ahead of schedule (PAY_0 → -1)",
      changes: { PAY_0: -1 },
    });
  }

  const allLate = PAY_COLS.every((c) => payload[c] > 0);
  if (allLate) {
    scenarios.push({
      label: "If all 6 months become on-time (PAY_* → -1)",
      changes: Object.fromEntries(PAY_COLS.map((c) => [c, -1])),
    });
  }

  if (payload.RISK_RATING > 1) {
    scenarios.push({
      label: "If internal risk rating improves (→ 1)",
      changes: { RISK_RATING: 1 },
    });
  }

  const bills = [1, 2, 3, 4, 5, 6].map((i) => payload[`BILL_AMT${i}`]);
  const maxBill = Math.max(...bills);
  if (maxBill > payload.LIMIT_BAL * 0.5) {
    const reduced = Object.fromEntries(
      [1, 2, 3, 4, 5, 6].map((i) => [`BILL_AMT${i}`, Math.round(payload[`BILL_AMT${i}`] * 0.6)])
    );
    scenarios.push({
      label: "If bill amounts drop 40% (pay-down scenario)",
      changes: reduced,
    });
  }

  return scenarios.slice(0, 4);
}

function renderWhatIf(data) {
  const box = document.getElementById("whatif-results");
  box.classList.remove("hidden");
  box.innerHTML = "";

  const base = data.baseline.default_probability;
  for (const s of data.scenarios) {
    const delta = s.delta_vs_baseline;
    const sign = delta >= 0 ? "+" : "";
    const deltaClass = delta < 0 ? "good" : delta > 0 ? "bad" : "";
    const card = document.createElement("div");
    card.className = "whatif-card";
    card.innerHTML = `
      <p class="whatif-label">${s.label}</p>
      <div class="whatif-metrics">
        <span>${(s.default_probability * 100).toFixed(1)}%</span>
        <span class="whatif-delta ${deltaClass}">${sign}${(delta * 100).toFixed(1)} pp</span>
        <span class="risk-pill ${s.risk_level} whatif-pill">${s.risk_label}</span>
      </div>
    `;
    box.appendChild(card);
  }

  if (data.scenarios.length === 0) {
    box.innerHTML = "<p class='hint'>No scenarios apply — profile is already low-risk on key levers.</p>";
  }
}

async function loadMetadata() {
  const badge = document.getElementById("model-badge");
  try {
    const res = await fetch(`${API}/api/metadata`);
    if (!res.ok) throw new Error("API unavailable");
    const meta = await res.json();
    badge.textContent = `${meta.model_name} · AUC ${meta.test_auc_roc}`;
    badge.classList.add("ready");

    document.getElementById("insight-model").textContent = meta.model_name || "—";
    document.getElementById("insight-auc").textContent = meta.test_auc_roc ?? "—";
    document.getElementById("insight-f1").textContent = meta.test_f1 ?? "—";
    document.getElementById("insight-threshold").textContent =
      meta.risk_threshold != null ? meta.risk_threshold.toFixed(2) : "0.50";

    const sel = document.getElementById("city-select");
    sel.innerHTML = "";
    for (const c of meta.cities || []) {
      const opt = document.createElement("option");
      opt.value = c;
      opt.textContent = c;
      sel.appendChild(opt);
    }

    const feats = document.getElementById("global-features");
    feats.innerHTML = "";
    for (const f of meta.top_features || []) {
      const li = document.createElement("li");
      const pct = (f.importance * 100).toFixed(1);
      li.innerHTML = `<span>${f.name}</span><span class="bar-wrap"><span class="bar" style="width:${pct}%"></span></span>`;
      feats.appendChild(li);
    }
  } catch {
    badge.textContent = "Model offline — export & run server";
  }
}

document.getElementById("predict-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = document.getElementById("submit-btn");
  btn.disabled = true;
  btn.textContent = "Scoring…";

  try {
    lastPayload = formToPayload(e.target);
    const res = await fetch(`${API}/api/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(lastPayload),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Prediction failed");
    showResult(data);
  } catch (err) {
    showError(err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Assess default risk";
  }
});

document.getElementById("whatif-btn").addEventListener("click", async () => {
  if (!lastPayload) return;
  const btn = document.getElementById("whatif-btn");
  btn.disabled = true;
  btn.textContent = "Running scenarios…";

  try {
    const scenarios = buildWhatIfScenarios(lastPayload);
    const res = await fetch(`${API}/api/whatif`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ profile: lastPayload, scenarios }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "What-if failed");
    renderWhatIf(data);
  } catch (err) {
    showError(err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Run what-if analysis";
  }
});

document.getElementById("sample-low-btn").addEventListener("click", () => {
  setFormValues(document.getElementById("predict-form"), LOW_RISK_SAMPLE);
});

document.getElementById("sample-high-btn").addEventListener("click", () => {
  setFormValues(document.getElementById("predict-form"), HIGH_RISK_SAMPLE);
});

loadMetadata();
