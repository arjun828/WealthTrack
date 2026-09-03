/* WealthTrack frontend — vanilla JS, no build step. Talks to the FastAPI backend
 * via relative paths since it's served from the same origin. */

const REFRESH_INTERVAL_MS = 45000; // matches backend's 45s price cache TTL

const els = {
  summaryInvested: document.getElementById("summary-invested"),
  summaryCurrent: document.getElementById("summary-current"),
  summaryPnl: document.getElementById("summary-pnl"),
  summaryReturn: document.getElementById("summary-return"),
  form: document.getElementById("add-holding-form"),
  formError: document.getElementById("form-error"),
  tbody: document.getElementById("holdings-tbody"),
  tableEmpty: document.getElementById("holdings-empty"),
  refreshNote: document.getElementById("refresh-note"),
  allocationEmpty: document.getElementById("allocation-empty"),
  pnlEmpty: document.getElementById("pnl-empty"),
};

let allocationChart = null;
let pnlChart = null;
let refreshTimer = null;

// ---------- formatting helpers ----------

function formatMoney(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatPct(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

function formatTimestamp(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function signClass(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "";
  return value >= 0 ? "positive" : "negative";
}

// ---------- API calls ----------

async function fetchJSON(url, options) {
  const res = await fetch(url, options);
  let body = null;
  try {
    body = await res.json();
  } catch (_) {
    // no JSON body
  }
  if (!res.ok) {
    const message = (body && (body.detail || body.error)) || `Request failed (${res.status})`;
    const err = new Error(message);
    err.status = res.status;
    throw err;
  }
  return body;
}

async function loadDashboard({ showToastOnError = true } = {}) {
  try {
    const [holdings, summary] = await Promise.all([
      fetchJSON("/api/holdings"),
      fetchJSON("/api/portfolio/summary"),
    ]);
    renderSummary(summary);
    renderTable(holdings);
    renderCharts(holdings);
    els.refreshNote.textContent = `Updated ${new Date().toLocaleTimeString()}`;
    hideToast();
  } catch (err) {
    console.error("Failed to load dashboard:", err);
    if (showToastOnError) showToast("Couldn't reach the server — showing last known data.");
    els.refreshNote.textContent = "Refresh failed — will retry automatically.";
  }
}

// ---------- rendering ----------

function renderSummary(summary) {
  els.summaryInvested.textContent = formatMoney(summary.total_invested);
  els.summaryCurrent.textContent = formatMoney(summary.total_current_value);

  els.summaryPnl.textContent = formatMoney(summary.total_profit_loss);
  els.summaryPnl.className = `card-value ${signClass(summary.total_profit_loss)}`;

  els.summaryReturn.textContent = formatPct(summary.total_return_pct);
  els.summaryReturn.className = `card-value ${signClass(summary.total_return_pct)}`;
}

function renderTable(holdings) {
  els.tbody.innerHTML = "";

  if (!holdings || holdings.length === 0) {
    els.tableEmpty.hidden = false;
    return;
  }
  els.tableEmpty.hidden = true;

  for (const h of holdings) {
    const tr = document.createElement("tr");

    const currentPriceCell = h.price_error
      ? `<span class="price-error" title="${escapeHtml(h.price_error)}">unavailable</span>`
      : formatMoney(h.current_price);

    const lastUpdatedCell = h.price_error
      ? `<span class="stale">—</span>`
      : formatTimestamp(h.last_updated);

    tr.innerHTML = `
      <td class="symbol-cell">${escapeHtml(h.symbol)}</td>
      <td>${h.quantity}</td>
      <td>${formatMoney(h.purchase_price)}</td>
      <td>${currentPriceCell}</td>
      <td>${formatMoney(h.invested_amount)}</td>
      <td>${h.price_error ? "—" : formatMoney(h.current_value)}</td>
      <td class="${signClass(h.profit_loss)}">${h.price_error ? "—" : formatMoney(h.profit_loss)}</td>
      <td class="${signClass(h.return_pct)}">${h.price_error ? "—" : formatPct(h.return_pct)}</td>
      <td>${lastUpdatedCell}</td>
      <td><button class="remove-btn" data-id="${escapeHtml(h.id)}">Remove</button></td>
    `;
    els.tbody.appendChild(tr);
  }

  for (const btn of els.tbody.querySelectorAll(".remove-btn")) {
    btn.addEventListener("click", onRemoveClick);
  }
}

function renderCharts(holdings) {
  const priced = (holdings || []).filter((h) => !h.price_error);

  // Allocation chart (by current value)
  const allocLabels = priced.map((h) => h.symbol);
  const allocData = priced.map((h) => h.current_value);
  const hasAlloc = priced.length > 0 && allocData.some((v) => v > 0);

  els.allocationEmpty.hidden = hasAlloc;
  document.getElementById("allocation-chart").style.display = hasAlloc ? "" : "none";

  if (hasAlloc) {
    const colors = generateColors(allocLabels.length);
    if (allocationChart) {
      allocationChart.data.labels = allocLabels;
      allocationChart.data.datasets[0].data = allocData;
      allocationChart.data.datasets[0].backgroundColor = colors;
      allocationChart.update();
    } else {
      const ctx = document.getElementById("allocation-chart").getContext("2d");
      allocationChart = new Chart(ctx, {
        type: "doughnut",
        data: {
          labels: allocLabels,
          datasets: [{ data: allocData, backgroundColor: colors }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { position: "bottom" } },
        },
      });
    }
  }

  // P&L bar chart
  const pnlLabels = priced.map((h) => h.symbol);
  const pnlData = priced.map((h) => h.profit_loss);
  const hasPnl = priced.length > 0;

  els.pnlEmpty.hidden = hasPnl;
  document.getElementById("pnl-chart").style.display = hasPnl ? "" : "none";

  if (hasPnl) {
    const barColors = pnlData.map((v) => (v >= 0 ? "#12805c" : "#b3261e"));
    if (pnlChart) {
      pnlChart.data.labels = pnlLabels;
      pnlChart.data.datasets[0].data = pnlData;
      pnlChart.data.datasets[0].backgroundColor = barColors;
      pnlChart.update();
    } else {
      const ctx = document.getElementById("pnl-chart").getContext("2d");
      pnlChart = new Chart(ctx, {
        type: "bar",
        data: {
          labels: pnlLabels,
          datasets: [{ label: "P&L ($)", data: pnlData, backgroundColor: barColors }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: { y: { beginAtZero: true } },
        },
      });
    }
  }
}

function generateColors(n) {
  const palette = [
    "#3f5efb", "#12805c", "#f2994a", "#eb5757", "#9b51e0",
    "#2d9cdb", "#f2c94c", "#219653", "#bb6bd9", "#56ccf2",
  ];
  const out = [];
  for (let i = 0; i < n; i++) out.push(palette[i % palette.length]);
  return out;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

// ---------- form handling ----------

function showFormError(message) {
  els.formError.textContent = message;
  els.formError.hidden = false;
}

function hideFormError() {
  els.formError.hidden = true;
  els.formError.textContent = "";
}

async function onAddHoldingSubmit(evt) {
  evt.preventDefault();
  hideFormError();

  const formData = new FormData(els.form);
  const symbol = String(formData.get("symbol") || "").trim().toUpperCase();
  const quantity = parseFloat(formData.get("quantity"));
  const purchasePrice = parseFloat(formData.get("purchase_price"));
  const purchaseDate = String(formData.get("purchase_date") || "").trim();

  if (!symbol || Number.isNaN(quantity) || Number.isNaN(purchasePrice)) {
    showFormError("Please fill in symbol, quantity, and purchase price.");
    return;
  }

  const payload = { symbol, quantity, purchase_price: purchasePrice };
  if (purchaseDate) payload.purchase_date = purchaseDate;

  const submitBtn = els.form.querySelector("button[type=submit]");
  submitBtn.disabled = true;
  try {
    await fetchJSON("/api/holdings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    els.form.reset();
    await loadDashboard();
  } catch (err) {
    showFormError(err.message || "Failed to add holding.");
  } finally {
    submitBtn.disabled = false;
  }
}

async function onRemoveClick(evt) {
  const btn = evt.currentTarget;
  const id = btn.dataset.id;
  btn.disabled = true;
  btn.textContent = "Removing…";
  try {
    await fetchJSON(`/api/holdings/${encodeURIComponent(id)}`, { method: "DELETE" });
    await loadDashboard();
  } catch (err) {
    console.error("Failed to remove holding:", err);
    showToast(`Couldn't remove holding: ${err.message}`);
    btn.disabled = false;
    btn.textContent = "Remove";
  }
}

// ---------- toast for background errors ----------

let toastEl = null;
function showToast(message) {
  if (!toastEl) {
    toastEl = document.createElement("div");
    toastEl.className = "toast";
    document.body.appendChild(toastEl);
  }
  toastEl.textContent = message;
  toastEl.hidden = false;
}
function hideToast() {
  if (toastEl) toastEl.hidden = true;
}

// ---------- init ----------

function startAutoRefresh() {
  if (refreshTimer) clearInterval(refreshTimer);
  refreshTimer = setInterval(() => loadDashboard({ showToastOnError: false }), REFRESH_INTERVAL_MS);
}

els.form.addEventListener("submit", onAddHoldingSubmit);

loadDashboard();
startAutoRefresh();
