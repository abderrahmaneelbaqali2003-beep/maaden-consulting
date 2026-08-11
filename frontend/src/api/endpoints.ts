import { apiClient } from "@/api/client";
import type {
  AnalyzeResponse,
  CalculationInput,
  CalculationResult,
  DashboardSummary,
  DataIssueEntry,
  Driver,
  ImportHistoryEntry,
  ImportResponse,
  Lens,
  LedModule,
  PaginatedResponse,
  RecommendationRequest,
  RecommendationResponse,
  ValidateResultRequest,
} from "@/types/api";

// --- Sante ---
export const getHealth = () => apiClient.get("/api/health").then((r) => r.data);

// --- Tableau de bord ---
export const getDashboardSummary = () =>
  apiClient.get<DashboardSummary>("/api/dashboard/summary").then((r) => r.data);

// --- Drivers ---
export interface CatalogListParams {
  search?: string;
  manufacturer?: string;
  page?: number;
  page_size?: number;
  [key: string]: string | number | undefined;
}

export const listDrivers = (params: CatalogListParams = {}) =>
  apiClient.get<PaginatedResponse<Driver>>("/api/drivers", { params }).then((r) => r.data);
export const getDriver = (id: number) => apiClient.get<Driver>(`/api/drivers/${id}`).then((r) => r.data);
export const deleteDriver = (id: number) => apiClient.delete(`/api/drivers/${id}`);

// --- Modules ---
export const listModules = (params: CatalogListParams = {}) =>
  apiClient.get<PaginatedResponse<LedModule>>("/api/modules", { params }).then((r) => r.data);
export const getModule = (id: number) => apiClient.get<LedModule>(`/api/modules/${id}`).then((r) => r.data);
export const deleteModule = (id: number) => apiClient.delete(`/api/modules/${id}`);

// --- Lenses ---
export const listLenses = (params: CatalogListParams = {}) =>
  apiClient.get<PaginatedResponse<Lens>>("/api/lenses", { params }).then((r) => r.data);
export const getLens = (id: number) => apiClient.get<Lens>(`/api/lenses/${id}`).then((r) => r.data);
export const deleteLens = (id: number) => apiClient.delete(`/api/lenses/${id}`);

// --- Recommandations ---
export const createRecommendation = (payload: RecommendationRequest) =>
  apiClient.post<RecommendationResponse>("/api/recommendations", payload).then((r) => r.data);
export const getRecommendation = (id: number) =>
  apiClient.get<RecommendationResponse>(`/api/recommendations/${id}`).then((r) => r.data);
export const getRecommendationHistory = (page = 1, page_size = 10) =>
  apiClient
    .get<PaginatedResponse<RecommendationResponse>>("/api/recommendations/history", {
      params: { page, page_size },
    })
    .then((r) => r.data);
export const validateRecommendationResult = (resultId: number, payload: ValidateResultRequest) =>
  apiClient.post(`/api/recommendation-results/${resultId}/validate`, payload).then((r) => r.data);
export const rejectRecommendationResult = (resultId: number, payload: ValidateResultRequest) =>
  apiClient.post(`/api/recommendation-results/${resultId}/reject`, payload).then((r) => r.data);

// --- Rapport PDF de consulting ---

function extractFilename(contentDisposition: string | undefined, fallback: string): string {
  const match = contentDisposition?.match(/filename="?([^";]+)"?/);
  return match ? match[1] : fallback;
}

/** Telecharge le rapport PDF d'une configuration validee et declenche le telechargement
 * navigateur. Ne fonctionne que si `validation_status === "validated"` (409 sinon). */
export const downloadRecommendationReport = async (resultId: number) => {
  const response = await apiClient.get(`/api/recommendation-results/${resultId}/report.pdf`, {
    responseType: "blob",
  });
  const filename = extractFilename(response.headers["content-disposition"], `MAADEN_Consulting_Report_${resultId}.pdf`);
  const blobUrl = URL.createObjectURL(new Blob([response.data], { type: "application/pdf" }));
  const link = document.createElement("a");
  link.href = blobUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(blobUrl);
};

// --- Calculateur technique ---
export const previewCalculations = (payload: CalculationInput) =>
  apiClient.post<CalculationResult>("/api/calculations/preview", payload).then((r) => r.data);

// --- Imports ---
export const analyzeImportFile = (file: File) => {
  const formData = new FormData();
  formData.append("file", file);
  return apiClient
    .post<AnalyzeResponse>("/api/imports/analyze", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    })
    .then((r) => r.data);
};

export const importFile = (entity: "drivers" | "modules" | "lenses", file: File) => {
  const formData = new FormData();
  formData.append("file", file);
  return apiClient
    .post<ImportResponse>(`/api/imports/${entity}`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    })
    .then((r) => r.data);
};

export const getImportHistory = (page = 1, page_size = 20) =>
  apiClient
    .get<PaginatedResponse<ImportHistoryEntry>>("/api/imports/history", { params: { page, page_size } })
    .then((r) => r.data);

export const getImportIssues = (importId: number) =>
  apiClient.get<DataIssueEntry[]>(`/api/imports/${importId}/issues`).then((r) => r.data);
