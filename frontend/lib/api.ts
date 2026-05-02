/**
 * Typed API client for the FastAPI backend.
 * Automatically attaches the Supabase JWT from the browser session.
 */
import axios from "axios";
import { createClient } from "@/lib/supabase/client";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const apiClient = axios.create({ baseURL: BASE_URL });

// Attach JWT on every request
apiClient.interceptors.request.use(async (config) => {
  const supabase = createClient();
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// --- Policies ---
export const policiesApi = {
  list: (params?: Record<string, unknown>) =>
    apiClient.get("/api/v1/policies", { params }).then((r) => r.data),
  get: (id: string) =>
    apiClient.get(`/api/v1/policies/${id}`).then((r) => r.data),
  create: (data: unknown) =>
    apiClient.post("/api/v1/policies", data).then((r) => r.data),
  update: (id: string, data: unknown) =>
    apiClient.patch(`/api/v1/policies/${id}`, data).then((r) => r.data),
  delete: (id: string) => apiClient.delete(`/api/v1/policies/${id}`),
};

// --- Providers ---
export const providersApi = {
  list: () => apiClient.get("/api/v1/providers").then((r) => r.data),
  get: (id: string) =>
    apiClient.get(`/api/v1/providers/${id}`).then((r) => r.data),
  create: (data: unknown) =>
    apiClient.post("/api/v1/providers", data).then((r) => r.data),
  update: (id: string, data: unknown) =>
    apiClient.patch(`/api/v1/providers/${id}`, data).then((r) => r.data),
  delete: (id: string) => apiClient.delete(`/api/v1/providers/${id}`),
};

// --- Renewal Notices ---
export const noticesApi = {
  list: (params?: Record<string, unknown>) =>
    apiClient.get("/api/v1/notices", { params }).then((r) => r.data),
  get: (id: string) =>
    apiClient.get(`/api/v1/notices/${id}`).then((r) => r.data),
  downloadDocument: (id: string) =>
    apiClient
      .get(`/api/v1/notices/${id}/document`, { responseType: "blob" })
      .then((r) => r.data),
  uploadDocument: (id: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return apiClient
      .post(`/api/v1/notices/${id}/upload`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data);
  },
  regenerate: (id: string) =>
    apiClient.post(`/api/v1/notices/${id}/regenerate`).then((r) => r.data),
};

// --- Templates ---
export const templatesApi = {
  list: () => apiClient.get("/api/v1/templates").then((r) => r.data),
  get: (id: string) =>
    apiClient.get(`/api/v1/templates/${id}`).then((r) => r.data),
  update: (id: string, data: unknown) =>
    apiClient.patch(`/api/v1/templates/${id}`, data).then((r) => r.data),
  preview: (data: unknown) =>
    apiClient.post("/api/v1/templates/preview", data).then((r) => r.data),
};

// --- Logs ---
export const logsApi = {
  list: (params?: Record<string, unknown>) =>
    apiClient.get("/api/v1/logs", { params }).then((r) => r.data),
};
