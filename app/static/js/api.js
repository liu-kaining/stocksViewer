const ApiClient = {
  async get(path, params = {}) {
    const url = new URL(path, window.location.origin);
    Object.entries(params).forEach(([key, value]) => url.searchParams.append(key, value));
    const response = await fetch(url, { method: "GET", headers: { "Accept": "application/json" } });
    return response.json();
  },

  async post(path, body = {}) {
    const response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      body: JSON.stringify(body),
    });
    return response.json();
  },
};

export default ApiClient;

