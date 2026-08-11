import axios from "axios";

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000",
  headers: { "Content-Type": "application/json" },
});

function formatDetail(detail: unknown): string | null {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const joined = detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join(" ; ");
    return joined || null;
  }
  return null;
}

export function extractErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = formatDetail(error.response?.data?.detail);
    if (detail) return detail;
    if (error.response?.status === undefined) {
      return "Impossible de contacter le serveur. Verifiez que le backend est demarre (voir README).";
    }
  }
  return "Une erreur inattendue s'est produite.";
}

/**
 * Avec `responseType: "blob"`, une reponse d'erreur JSON du backend (409, 404, 500...) arrive
 * cote Axios sous forme de `Blob` plutot que d'objet deja parse : `extractErrorMessage` ne peut
 * alors pas lire `error.response.data.detail` directement. Ce helper relit le blob en texte,
 * tente un JSON.parse, et retombe sur le texte brut ou un message generique si besoin.
 */
export async function extractBlobErrorMessage(error: unknown, fallback: string): Promise<string> {
  if (axios.isAxiosError(error) && error.response?.data instanceof Blob) {
    const text = await error.response.data.text();
    try {
      const json = JSON.parse(text);
      const detail = formatDetail(json?.detail);
      if (detail) return detail;
    } catch {
      // Reponse non-JSON (ex: erreur reseau/proxy) : on retombe sur le texte brut si exploitable.
      if (text.trim()) return text.trim();
    }
    return fallback;
  }
  if (axios.isAxiosError(error) && error.response?.status === undefined) {
    return "Impossible de contacter le serveur. Verifiez que le backend est demarre (voir README).";
  }
  return fallback;
}
