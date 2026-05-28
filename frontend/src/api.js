const API_BASE = "http://127.0.0.1:8000";

export function getErrorMessage(error) {
  const fallback = "Ocorreu um erro. Tente novamente.";

  const formatValidationItem = (item) => {
    if (!item || typeof item !== "object") return "";
    const message = item.msg || item.message || "";
    const field = Array.isArray(item.loc) ? item.loc.filter((part) => part !== "body").join(".") : "";
    if (message && field) return `${field}: ${message}`;
    return message;
  };

  const normalize = (value) => {
    if (!value) return "";
    if (typeof value === "string") return value;
    if (Array.isArray(value)) {
      const validationMessages = value.map(formatValidationItem).filter(Boolean);
      if (validationMessages.length) {
        const hasMissingField = validationMessages.some((message) =>
          message.toLowerCase().includes("field required")
        );
        return hasMissingField ? "Preencha todos os campos obrigatórios." : validationMessages.join(" ");
      }
      return "";
    }
    if (typeof value === "object") {
      return normalize(value.detail) || normalize(value.message) || "";
    }
    return "";
  };

  return normalize(error) || normalize(error?.detail) || normalize(error?.message) || fallback;
}

export async function api(path, options = {}, token) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {})
  };

  if (token) {
    headers["X-Auth-Token"] = token;
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(getErrorMessage(data));
    error.detail = data.detail;
    error.response = data;
    throw error;
  }
  return data;
}
