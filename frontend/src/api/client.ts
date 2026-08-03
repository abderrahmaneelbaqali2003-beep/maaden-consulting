import axios from "axios";

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000",
  headers: { "Content-Type": "application/json" },
});

export function extractErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join(" ; ");
    }
    if (error.response?.status === undefined) {
      return "Impossible de contacter le serveur. Verifiez que le backend est demarre (voir README).";
    }
  }
  return "Une erreur inattendue s'est produite.";
}
