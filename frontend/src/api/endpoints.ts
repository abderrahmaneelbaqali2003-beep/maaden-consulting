import { apiClient } from "@/api/client";
import type {
  AnalyzeResponse,
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
export const validateRecommendation = (id: number, validator_name?: string, comment?: string) =>
  apiClient.post(`/api/recommendations/${id}/validate`, { validator_name, comment });
export const rejectRecommendation = (id: number, validator_name?: string, comment?: string) =>
  apiClient.post(`/api/recommendations/${id}/reject`, { validator_name, comment });

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
