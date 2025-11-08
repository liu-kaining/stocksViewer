import ApiClient from "./api.js";

const state = {
  symbol: "",
  range: document.querySelector(".chip-group .chip.active")?.dataset.range ?? "1M",
  adjusted: false,
  provider: document.querySelector("input[name='provider-toggle']:checked")?.value || "alphavantage",
};

let charts = {
  price: null,
  volume: null,
  indicator: null,
};

const toastContainer = document.getElementById("toast-container");

function showToast(message, type = "info", duration = 3000) {
  const toast = document.createElement("div");
  toast.className = `toast ${type === "error" ? "error" : ""}`;
  toast.textContent = message;
  toastContainer.appendChild(toast);
  setTimeout(() => toast.remove(), duration);
}

function updateQuoteCard(data) {
  const container = document.getElementById("quote-content");
  if (!data) {
    container.innerHTML = "<p>暂无行情信息。</p>";
    return;
  }
  const heroProviderLabel = document.getElementById("hero-provider-label");
  const providerLabel = document.getElementById("provider-label");
  container.innerHTML = `
    <div class="quote-price">${data.price ?? "--"}</div>
    <div class="quote-change">涨跌：${data.change ?? "--"} （${data.change_percent ?? "--"}）</div>
    <div class="quote-volume">成交量：${data.volume ?? "--"}</div>
    <div class="quote-timestamp">更新时间：${data.timestamp ?? "--"}</div>
    <div class="quote-provider">当前数据源：${data.provider_label ?? "--"}</div>
  `;
}

function updateCompanyCard(overview) {
  const container = document.getElementById("company-content");
  if (!overview) {
    container.innerHTML = "<p>暂无公司概览，请先获取有效数据。</p>";
    return;
  }
  container.innerHTML = `
    <p><strong>行业：</strong> ${overview.industry ?? "--"}</p>
    <p><strong>市值：</strong> ${overview.market_cap ?? "--"}</p>
    <p><strong>市盈率：</strong> ${overview.pe_ratio ?? "--"}</p>
    <p class="company-desc">${overview.description ?? ""}</p>
  `;
}

function updateStatus(message) {
  const container = document.getElementById("status-content");
  container.innerHTML = `<p>${message}</p>`;
}

function setSearchLoading(isLoading) {
  const button = document.getElementById("search-btn");
  if (!button) return;
  if (!button.dataset.originalText) {
    button.dataset.originalText = button.textContent ?? "查询";
  }
  button.disabled = isLoading;
  button.textContent = isLoading ? "查询中…" : button.dataset.originalText;
}

function initCharts() {
  if (!window.echarts) return;
  const priceEl = document.getElementById("price-chart");
  const volumeEl = document.getElementById("volume-chart");
  const indicatorEl = document.getElementById("indicator-chart");
  if (!priceEl || !volumeEl || !indicatorEl) return;

  charts = {
    price: window.echarts.init(priceEl),
    volume: window.echarts.init(volumeEl),
    indicator: window.echarts.init(indicatorEl),
  };

  window.addEventListener("resize", () => {
    charts.price?.resize();
    charts.volume?.resize();
    charts.indicator?.resize();
  });
}

function formatSeries(history) {
  const series = history?.series ?? [];
  if (!series.length) return null;
  const timestamps = series.map((item) => item.timestamp);
  const candlesticks = series.map((item) => [item.open, item.close, item.low, item.high]);
  const closeValues = series.map((item) => item.adjusted_close ?? item.close ?? null);
  const volumes = series.map((item) => Number(item.volume ?? 0));
  return { timestamps, candlesticks, closeValues, volumes };
}

function updateCharts(history) {
  if (!charts || !window.echarts) return;
  const formatted = formatSeries(history);
  if (!formatted) {
    charts.price?.clear();
    charts.volume?.clear();
    charts.indicator?.clear();
    return;
  }

  const { timestamps, candlesticks, closeValues, volumes } = formatted;

  charts.price.setOption({
    textStyle: { fontFamily: "inherit" },
    tooltip: { trigger: "axis" },
    grid: { left: 40, right: 30, top: 20, bottom: 80 },
    xAxis: {
      type: "category",
      data: timestamps,
      axisLine: { lineStyle: { color: "#cfd4dc" } },
      axisLabel: { color: "#55627a" },
    },
    yAxis: {
      scale: true,
      axisLine: { lineStyle: { color: "#cfd4dc" } },
      axisLabel: { color: "#55627a" },
      splitLine: { lineStyle: { color: "#e5eaf1" } },
    },
    dataZoom: [
      { type: "inside", start: 60, end: 100 },
      { type: "slider", bottom: 20, height: 20, start: 60, end: 100 },
    ],
    series: [
      {
        name: "价格",
        type: "candlestick",
        data: candlesticks,
        itemStyle: {
          color: "#22c55e",
          color0: "#ef4444",
          borderColor: "#22c55e",
          borderColor0: "#ef4444",
        },
      },
    ],
  });

  charts.volume.setOption({
    textStyle: { fontFamily: "inherit" },
    tooltip: { trigger: "axis" },
    grid: { left: 40, right: 30, top: 10, bottom: 40 },
    xAxis: {
      type: "category",
      data: timestamps,
      axisLine: { lineStyle: { color: "#cfd4dc" } },
      axisLabel: { color: "#55627a" },
    },
    yAxis: {
      axisLine: { lineStyle: { color: "#cfd4dc" } },
      axisLabel: { color: "#55627a" },
      splitLine: { show: false },
    },
    dataZoom: [{ type: "inside", start: 60, end: 100 }],
    series: [
      {
        name: "成交量",
        type: "bar",
        data: volumes,
        itemStyle: { color: "#93c5fd" },
      },
    ],
  });

  charts.indicator.setOption({
    textStyle: { fontFamily: "inherit" },
    tooltip: { trigger: "axis" },
    grid: { left: 40, right: 30, top: 10, bottom: 40 },
    xAxis: {
      type: "category",
      data: timestamps,
      axisLine: { lineStyle: { color: "#cfd4dc" } },
      axisLabel: { color: "#55627a" },
    },
    yAxis: {
      axisLine: { lineStyle: { color: "#cfd4dc" } },
      axisLabel: { color: "#55627a" },
      splitLine: { lineStyle: { color: "#e5eaf1" } },
    },
    dataZoom: [{ type: "inside", start: 60, end: 100 }],
    series: [
      {
        name: "收盘价",
        type: "line",
        smooth: true,
        data: closeValues,
        areaStyle: { color: "rgba(37, 99, 235, 0.15)" },
        lineStyle: { color: "#2563eb", width: 2 },
      },
    ],
  });
}

async function loadQuote() {
  if (!state.symbol) return;
  updateStatus("正在加载实时行情…");
  try {
    const response = await ApiClient.get("/api/quote", { symbol: state.symbol });
    if (response.success) {
      updateQuoteCard(response.data);
      updateCompanyCard(response.data?.company_overview);
      updateStatus(`行情已加载（来源：${response.data?.source ?? "未知"}）。`);
    } else {
      showToast(response.error?.message ?? "行情加载失败", "error");
      updateStatus("行情加载失败。");
    }
  } catch (error) {
    console.error(error);
    showToast("请求异常，请查看控制台。", "error");
    updateStatus("网络异常，请稍后重试。");
  }
}

async function loadHistory() {
  if (!state.symbol) return;
  updateStatus("正在加载历史数据…");
  try {
    const response = await ApiClient.get("/api/history", {
      symbol: state.symbol,
      interval: "daily",
      range: state.range,
      adjusted: state.adjusted,
    });
    if (response.success) {
      if (response.data?.notice && response.data?.source === "live") {
        showToast(response.data.notice, "info", 5000);
      }
      updateStatus(`历史数据已加载（来源：${response.data?.source ?? "未知"}）。`);
      updateCharts(response.data);
    } else {
      showToast(response.error?.message ?? "历史数据加载失败", "error");
      updateStatus("历史数据加载失败。");
      updateCharts(null);
    }
  } catch (error) {
    console.error(error);
    showToast("请求异常，请查看控制台。", "error");
    updateStatus("网络异常，请稍后重试。");
    updateCharts(null);
  }
}

async function performSearch() {
  const input = document.getElementById("symbol-input");
  if (!input) return;
  state.symbol = input.value.trim().toUpperCase();
  if (!state.symbol) {
    showToast("请输入有效的股票代码。", "error");
    return;
  }
  setSearchLoading(true);
  try {
    await Promise.all([loadQuote(), loadHistory()]);
  } finally {
    setSearchLoading(false);
  }
}

function bindEvents() {
  document.getElementById("search-btn")?.addEventListener("click", () => {
    performSearch();
  });

  document.querySelectorAll(".chip-group .chip").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".chip-group .chip").forEach((btn) => btn.classList.remove("active"));
      button.classList.add("active");
      state.range = button.dataset.range;
      loadHistory();
    });
  });

  document.getElementById("refresh-data")?.addEventListener("click", () => {
    performSearch();
  });

  document.getElementById("indicator-form")?.addEventListener("submit", (event) => {
    event.preventDefault();
    showToast("指标应用功能开发中，敬请期待。");
  });

  document.querySelectorAll(".provider-toggle input").forEach((radio) => {
    radio.addEventListener("change", () => {
      const selected = document.querySelector(".provider-toggle input:checked");
      if (!selected) return;
      state.provider = selected.value;
      ApiClient.post("/api/settings", { data: { provider: state.provider } }).then((response) => {
        const label = state.provider === "alphavantage" ? "Alpha Vantage" : "Finnhub";
        heroProviderLabel && (heroProviderLabel.textContent = label);
        providerLabel && (providerLabel.textContent = label);
        showToast("数据源已切换，正在重新加载…", "info");
        performSearch();
      });
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initCharts();
  bindEvents();
  const defaultSymbol = document.getElementById("symbol-input")?.value?.trim();
  if (defaultSymbol) {
    state.symbol = defaultSymbol.toUpperCase();
    performSearch();
  }
});

