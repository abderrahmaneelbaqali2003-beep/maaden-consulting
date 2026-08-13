import { apiClient } from "@/api/client";
import type {
  AiInterpretResponse,
  AnalyzeResponse,
  CalculationInput,
  CalculationResult,
  CpsAnalysisResponse,
  CpsDocumentOut,
  DashboardSummary,
  DataIssueEntry,
  Driver,
  ExtractedRequirementOut,
  ImportHistoryEntry,
  ImportResponse,
  Lens,
  LedModule,
  ManualRequirementCreateRequest,
  PaginatedResponse,
  Project,
  ProjectCreateRequest,
  ProjectScenarioOut,
  ProjectUpdateRequest,
  RecommendationRequest,
  RecommendationResponse,
  RequirementUpdateRequest,
  ScenarioSelectRequest,
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

// --- Assistant IA (autonome, aucun Projet requis) : texte libre -> exigences
// structurees (backend uniquement, jamais d'appel Groq direct depuis le frontend). Le
// resultat est ensuite transmis a `createRecommendation` (meme moteur que "Nouveau
// calcul") pour obtenir les configurations compatibles. */
export const interpretText = (text: string) =>
  apiClient.post<AiInterpretResponse>("/api/ai/interpret", { text }).then((r) => r.data);
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

// --- Projets (CPS -> exigences -> etude -> scenarios) ---

export const createProject = (payload: ProjectCreateRequest) =>
  apiClient.post<Project>("/api/projects", payload).then((r) => r.data);
export const listProjects = (page = 1, page_size = 20) =>
  apiClient.get<PaginatedResponse<Project>>("/api/projects", { params: { page, page_size } }).then((r) => r.data);
export const getProject = (projectId: number) =>
  apiClient.get<Project>(`/api/projects/${projectId}`).then((r) => r.data);
export const updateProject = (projectId: number, payload: ProjectUpdateRequest) =>
  apiClient.patch<Project>(`/api/projects/${projectId}`, payload).then((r) => r.data);

export const uploadCpsDocument = (projectId: number, file: File) => {
  const formData = new FormData();
  formData.append("file", file);
  return apiClient
    .post<CpsDocumentOut>(`/api/projects/${projectId}/documents/cps`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    })
    .then((r) => r.data);
};

export const listCpsDocuments = (projectId: number) =>
  apiClient.get<CpsDocumentOut[]>(`/api/projects/${projectId}/documents/cps`).then((r) => r.data);

/** Action unique "Importer et analyser le CPS" : upload + extraction + pre-analyse
 * automatique en un seul appel (jusqu'a 3 configurations provisoires si possible). */
export const analyzeCpsDocument = (projectId: number, file: File, launchedBy?: string) => {
  const formData = new FormData();
  formData.append("file", file);
  return apiClient
    .post<CpsAnalysisResponse>(`/api/projects/${projectId}/cps/analyze`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
      params: launchedBy ? { launched_by: launchedBy } : undefined,
    })
    .then((r) => r.data);
};

/** Relance la pre-analyse sans nouvel upload (ex: apres completion manuelle rapide). */
export const rerunPreliminaryStudy = (projectId: number) =>
  apiClient.post<CpsAnalysisResponse>(`/api/projects/${projectId}/cps/preliminary-study`).then((r) => r.data);

export const extractRequirements = (projectId: number, cpsDocumentId: number) =>
  apiClient
    .post<ExtractedRequirementOut[]>(`/api/projects/${projectId}/requirements/extract`, null, {
      params: { cps_document_id: cpsDocumentId },
    })
    .then((r) => r.data);

export const listRequirements = (projectId: number) =>
  apiClient.get<ExtractedRequirementOut[]>(`/api/projects/${projectId}/requirements`).then((r) => r.data);

export const addManualRequirement = (projectId: number, payload: ManualRequirementCreateRequest) =>
  apiClient.post<ExtractedRequirementOut>(`/api/projects/${projectId}/requirements`, payload).then((r) => r.data);

export const updateRequirement = (projectId: number, requirementId: number, payload: RequirementUpdateRequest) =>
  apiClient
    .patch<ExtractedRequirementOut>(`/api/projects/${projectId}/requirements/${requirementId}`, payload)
    .then((r) => r.data);

export const confirmRequirements = (projectId: number) =>
  apiClient.post<Project>(`/api/projects/${projectId}/requirements/confirm`).then((r) => r.data);

export const runStudy = (projectId: number, launchedBy?: string) =>
  apiClient
    .post<ProjectScenarioOut[]>(`/api/projects/${projectId}/study/run`, { launched_by: launchedBy ?? null })
    .then((r) => r.data);

export const listScenarios = (projectId: number) =>
  apiClient.get<ProjectScenarioOut[]>(`/api/projects/${projectId}/scenarios`).then((r) => r.data);

export const getProjectComparison = (projectId: number) =>
  apiClient.get<ProjectScenarioOut[]>(`/api/projects/${projectId}/comparison`).then((r) => r.data);

export const selectScenario = (projectId: number, scenarioId: number, payload: ScenarioSelectRequest) =>
  apiClient
    .post<ProjectScenarioOut>(`/api/projects/${projectId}/scenarios/${scenarioId}/select`, payload)
    .then((r) => r.data);

export const downloadProjectReport = async (projectId: number) => {
  const response = await apiClient.get(`/api/projects/${projectId}/report.pdf`, { responseType: "blob" });
  const filename = extractFilename(response.headers["content-disposition"], `MAADEN_Consulting_Report_${projectId}.pdf`);
  const blobUrl = URL.createObjectURL(new Blob([response.data], { type: "application/pdf" }));
  const link = document.createElement("a");
  link.href = blobUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(blobUrl);
};
