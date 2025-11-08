import ApiClient from "./api.js";

const toastContainer = document.getElementById("toast-container");

function showToast(message, type = "info", duration = 3000) {
  const toast = document.createElement("div");
  toast.className = `toast ${type === "error" ? "error" : ""}`;
  toast.textContent = message;
  toastContainer.appendChild(toast);
  setTimeout(() => toast.remove(), duration);
}

function readFormValues() {
  return {
    data: {
      provider: document.getElementById("data-provider").value,
    },
    alphavantage: {
      api_key: document.getElementById("alphavantage-api-key").value.trim(),
      default_range: document.getElementById("alphavantage-default-range").value,
      default_interval: document.getElementById("alphavantage-default-interval").value,
      auto_refresh_sec: Number(document.getElementById("alphavantage-auto-refresh").value),
    },
    finnhub: {
      api_key: document.getElementById("finnhub-api-key").value.trim(),
    },
    cache: {
      history_ttl_days: Number(document.getElementById("cache-history-ttl").value),
      quote_ttl_sec: Number(document.getElementById("cache-quote-ttl").value),
      indicator_ttl_sec: Number(document.getElementById("cache-indicator-ttl").value),
    },
    ai: {
      deepseek: {
        enabled: document.getElementById("deepseek-enabled").checked,
        api_key: document.getElementById("deepseek-api-key").value.trim(),
        endpoint: document.getElementById("deepseek-endpoint").value.trim(),
        model: document.getElementById("deepseek-model").value.trim(),
      },
      qwen: {
        enabled: document.getElementById("qwen-enabled").checked,
        api_key: document.getElementById("qwen-api-key").value.trim(),
        endpoint: document.getElementById("qwen-endpoint").value.trim(),
        model: document.getElementById("qwen-model").value.trim(),
      },
      insight_prompt: document.getElementById("ai-insight-prompt").value,
    },
    ui: {
      theme: document.getElementById("ui-theme").value,
      show_ai_panel: document.getElementById("ui-show-ai").checked,
    },
  };
}

async function saveSettings() {
  try {
    const payload = readFormValues();
    const response = await ApiClient.post("/api/settings", payload);
    if (response.success) {
      showToast("设置已保存。");
    } else {
      throw new Error(response.error?.message ?? "未知错误");
    }
  } catch (error) {
    console.error(error);
    showToast(`保存失败：${error.message}`, "error");
  }
}

async function testProvider(provider) {
  try {
    const response = await ApiClient.post("/api/settings/test", { provider });
    if (response.success && response.data?.success) {
      showToast(`${provider} 连通性测试成功。`);
    } else {
      const message = response.data?.message ?? response.error?.message ?? "未知错误";
      showToast(`${provider} 测试失败：${message}`, "error");
    }
  } catch (error) {
    console.error(error);
    showToast(`测试 ${provider} 失败：${error.message}`, "error");
  }
}

async function clearHistory() {
  try {
    const response = await ApiClient.post("/api/cache/clear_history");
    if (response.success) {
      showToast("历史缓存已清空。");
    } else {
      throw new Error(response.error?.message ?? "未知错误");
    }
  } catch (error) {
    console.error(error);
    showToast(`清空失败：${error.message}`, "error");
  }
}

function bindSecretToggles() {
  document.querySelectorAll(".secret-toggle").forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetId = btn.dataset.target;
      if (!targetId) return;
      const input = document.getElementById(targetId);
      if (!input) return;
      const isHidden = input.type === "password";
      input.type = isHidden ? "text" : "password";
      btn.classList.toggle("active", isHidden);
    });
  });
}

function bindEvents() {
  document.getElementById("save-settings")?.addEventListener("click", saveSettings);
  document.getElementById("reset-settings")?.addEventListener("click", async () => {
    const response = await ApiClient.get("/api/settings");
    if (response.success) {
      window.location.reload();
    }
  });
  document.querySelectorAll(".test-btn").forEach((btn) => {
    btn.addEventListener("click", () => testProvider(btn.dataset.provider));
  });
  document.getElementById("clear-history")?.addEventListener("click", () => {
    if (confirm("确定要清空历史缓存吗？")) {
      clearHistory();
    }
  });

  bindSecretToggles();
}

document.addEventListener("DOMContentLoaded", bindEvents);

