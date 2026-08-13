export type RecommendationStatus =
  | "compatible"
  | "compatible_with_warning"
  | "data_incomplete"
  | "manual_validation_required"
  | "not_compatible"
  | "impossible";

export interface Manufacturer {
  id: number;
  name: string;
  country?: string | null;
  website_url?: string | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// --- Catalogue ---

export interface Driver {
  id: number;
  external_ref: string;
  manufacturer: Manufacturer;
  reference: string;
  product_family?: string | null;
  product_name?: string | null;
  output_voltage_min_v: number;
  output_voltage_max_v: number;
  output_current_min_ma?: number | null;
  output_current_max_ma?: number | null;
  output_power_max_w: number;
  dali_2: boolean;
  d4i: boolean;
  dimming_0_10v: boolean;
  dimming_1_10v: boolean;
  ambient_temperature_max_c?: number | null;
  ip_rating?: string | null;
  is_active: boolean;
  needs_manual_validation: boolean;
  data_quality_score?: number | null;
  data_quality_level?: string | null;
}

export interface LedModule {
  id: number;
  external_ref: string;
  manufacturer: Manufacturer;
  reference: string;
  product_family?: string | null;
  led_package?: string | null;
  luminous_flux_nominal_lm: number;
  cct_nominal_k: number;
  power_nominal_w?: number | null;
  input_voltage_nominal_v?: number | null;
  current_nominal_ma?: number | null;
  is_active: boolean;
  needs_manual_validation: boolean;
  data_quality_score?: number | null;
  data_quality_level?: string | null;
}

export interface Lens {
  id: number;
  external_ref: string;
  manufacturer: Manufacturer;
  reference: string;
  product_family?: string | null;
  compatible_led_package?: string | null;
  optical_cells_quantity?: number | null;
  iesna_distribution_type?: string | null;
  ies_file_available: boolean;
  ldt_file_available: boolean;
  is_active: boolean;
  needs_manual_validation: boolean;
  data_quality_score?: number | null;
  data_quality_level?: string | null;
}

// --- Recommandation ---

export interface RecommendationRequest {
  project_id?: number | null;
  required_flux_lm: number;
  max_power_w: number;
  required_cct_k: number;
  voltage_nominal_v: number;
  current_nominal_ma: number;
  protocol?: string | null;
  led_package?: string | null;
  road_type?: string | null;
  pole_height_m?: number | null;
  pole_spacing_m?: number | null;
  ambient_temperature_c?: number | null;
  road_width_m?: number | null;
  road_length_m?: number | null;
  layout_type?: string | null;
  operating_hours_per_year?: number | null;
  energy_price_per_kwh?: number | null;
}

export interface ComponentRef {
  id: number;
  manufacturer: string;
  reference: string;
}

export interface ScoresOut {
  electrical: number;
  photometric: number;
  mechanical: number;
  thermal: number;
  data_quality: number;
}

// --- V2 : synthese documentaire (RAG) ---

export type DocumentaryConfidence = "high" | "medium" | "low" | "insufficient_evidence";

export interface EvidenceOut {
  category: string;
  document: string;
  section: string | null;
  page: number | null;
  relevance_score: number;
  summary: string;
}

export interface DocumentaryAnalysisOut {
  confidence: DocumentaryConfidence;
  evidence_count: number;
  evidence: EvidenceOut[];
  missing_evidence: string[];
}

// --- Calculateur technique ---

export type CalculationStatus = "calculated" | "estimate" | "not_calculable" | "to_validate";

export interface CalculationValue {
  key: string;
  label: string;
  value: number | null;
  unit: string | null;
  status: CalculationStatus;
  formula: string | null;
  inputs: Record<string, string | number | null>;
  is_estimate: boolean;
  warning: string | null;
}

export interface DimmingProfileEntry {
  duration_hours: number;
  level_percent: number;
}

export type LayoutType = "unilateral" | "opposite" | "staggered" | "central";

export interface CalculationInput {
  road_width_m?: number | null;
  road_length_m?: number | null;
  pole_height_m?: number | null;
  pole_spacing_m?: number | null;
  layout_type?: LayoutType | null;

  required_flux_lm?: number | null;
  utilization_factor?: number | null;
  maintenance_factor?: number | null;
  illuminance_min_lux?: number | null;
  illuminance_avg_lux?: number | null;

  module_voltage_v?: number | null;
  module_current_ma?: number | null;
  module_power_nominal_w?: number | null;

  driver_power_max_w?: number | null;
  driver_max_temperature_c?: number | null;
  lens_max_temperature_c?: number | null;

  ambient_temperature_c?: number | null;

  operating_hours_per_year?: number | null;
  energy_price_per_kwh?: number | null;
  reference_energy_kwh?: number | null;
  dimming_profile?: DimmingProfileEntry[] | null;
}

export interface ElectricalCalculationResult {
  module_power_w: CalculationValue;
  module_power_consistency_percent: CalculationValue;
  driver_required_power_w: CalculationValue;
  driver_loading_percent: CalculationValue;
  driver_power_margin_percent: CalculationValue;
  luminous_efficacy_lm_w: CalculationValue;
}

export interface GeometryCalculationResult {
  spacing_height_ratio: CalculationValue;
  road_segment_area_m2: CalculationValue;
  estimated_luminaire_count: CalculationValue;
}

export interface ThermalCalculationResult {
  driver_thermal_margin_c: CalculationValue;
  lens_thermal_margin_c: CalculationValue;
  tightest_thermal_margin_c: CalculationValue;
}

export interface EnergyCalculationResult {
  total_installed_power_kw: CalculationValue;
  annual_energy_kwh: CalculationValue;
  annual_energy_with_dimming_kwh: CalculationValue;
  energy_saving_percent: CalculationValue;
  energy_saved_kwh_year: CalculationValue;
  annual_energy_cost: CalculationValue;
}

export interface PhotometricEstimateResult {
  estimated_average_illuminance_lux: CalculationValue;
  uniformity_u0: CalculationValue;
}

export interface CalculationResult {
  electrical: ElectricalCalculationResult;
  geometry: GeometryCalculationResult;
  thermal: ThermalCalculationResult;
  energy: EnergyCalculationResult;
  photometric: PhotometricEstimateResult;
  warnings: string[];
}

export type ValidationStatus = "pending" | "validated" | "rejected";

export interface ValidateResultRequest {
  validator_name: string;
  comment?: string | null;
}

export interface RecommendationItem {
  id: number;
  rank: number;
  overall_score: number;
  driver: ComponentRef;
  module: ComponentRef;
  lens: ComponentRef | null;
  scores: ScoresOut;
  validated_rules: string[];
  warnings: string[];
  blocking_reasons: string[];
  explanation: string;
  validation_status: ValidationStatus | null;
  documentary_analysis?: DocumentaryAnalysisOut | null;
  technical_calculations?: CalculationResult | null;
}

export interface RejectedSummary {
  drivers_rejected: number;
  modules_rejected: number;
  lenses_rejected: number;
}

export interface RecommendationResponse {
  status: RecommendationStatus;
  request_id: string;
  run_id: number;
  message: string;
  recommendations: RecommendationItem[];
  rejected_summary: RejectedSummary;
  blocking_reasons: string[];
  suggestions: string[];
  created_at: string;
}

// --- Imports ---

export interface ColumnInfo {
  name: string;
  dtype: string;
  missing_count: number;
  missing_percent: number;
  unique_count: number;
}

export interface AnalyzeResponse {
  file_name: string;
  sheet_name: string;
  row_count: number;
  duplicate_rows: number;
  columns: ColumnInfo[];
  preview: Record<string, unknown>[];
}

export interface ImportIssueOut {
  row_number: number;
  external_ref: string | null;
  description: string;
}

export interface ImportResponse {
  entity_type: string;
  file_name: string;
  rows_total: number;
  rows_imported: number;
  rows_updated: number;
  rows_rejected: number;
  import_history_id: number | null;
  issues: ImportIssueOut[];
}

export interface ImportHistoryEntry {
  id: number;
  entity_type: string;
  file_name: string;
  rows_total: number;
  rows_imported: number;
  rows_rejected: number;
  status: string;
  started_at: string;
  finished_at: string | null;
}

export interface DataIssueEntry {
  id: number;
  entity_type: string;
  entity_external_ref: string | null;
  row_number: number | null;
  column_name: string | null;
  issue_category: string | null;
  description: string;
  severity: string;
  recommended_action: string | null;
  manual_review_required: boolean;
  resolution_status: string;
}

// --- Configurateur (selection manuelle / semi-automatique) ---

export type SelectionMode = "automatic" | "manual" | "hybrid";

export interface CriterionOut {
  criterion: string;
  label: string;
  status: "valid" | "warning" | "blocking" | "not_verifiable";
  detail: string;
}

export interface AlternativeConfigurationOut {
  driver: ComponentRef | null;
  module: ComponentRef;
  lens: ComponentRef | null;
  status: RecommendationStatus;
  overall_score: number;
  scores: ScoresOut;
  warnings: string[];
}

export interface ConfiguratorResultResponse {
  selection_mode: SelectionMode;
  status: RecommendationStatus;
  is_compatible: boolean;
  needs_manual_validation: boolean;
  driver: ComponentRef | null;
  module: ComponentRef | null;
  lens: ComponentRef | null;
  scores: ScoresOut | null;
  validated_rules: string[];
  warnings: string[];
  blocking_reasons: string[];
  criteria: CriterionOut[];
  explanation: string;
  suggestions: string[];
  alternatives: AlternativeConfigurationOut[];
}

export interface PartialRequirements {
  required_flux_lm?: number | null;
  max_power_w?: number | null;
  required_cct_k?: number | null;
  voltage_nominal_v?: number | null;
  current_nominal_ma?: number | null;
  protocol?: string | null;
  led_package?: string | null;
  road_type?: string | null;
  pole_height_m?: number | null;
  pole_spacing_m?: number | null;
  ambient_temperature_c?: number | null;
}

export interface ValidateConfigurationRequest {
  selection_mode: "manual" | "hybrid";
  driver_id?: number | null;
  module_id: number;
  lens_id?: number | null;
  project_requirements: PartialRequirements;
}

export interface RecommendMissingRequest {
  driver_id?: number | null;
  module_id?: number | null;
  lens_id?: number | null;
  project_requirements: PartialRequirements;
}

export interface ConfiguratorOptionItem {
  id: number;
  external_ref: string;
  manufacturer: string;
  reference: string;
  product_family?: string | null;
  key_specs: Record<string, unknown>;
  status: RecommendationStatus | null;
  is_active: boolean;
}

export interface ConfiguratorOptionsResponse {
  selection_modes: { value: SelectionMode; label: string }[];
  protocols: string[];
  manufacturers: { drivers: string[]; modules: string[]; lenses: string[] };
  counts: { drivers: number; modules: number; lenses: number };
}

export interface SaveConfigurationRequest {
  project_id?: number | null;
  selection_mode: SelectionMode;
  driver_id?: number | null;
  module_id: number;
  lens_id?: number | null;
  status: string;
  overall_score?: number | null;
  validated_rules?: string[];
  blocking_reasons?: string[];
  warnings?: string[];
  user_comment?: string | null;
  is_favorite?: boolean;
}

export interface SavedConfigurationRead {
  id: number;
  project_id: number | null;
  selection_mode: SelectionMode;
  driver: ComponentRef | null;
  module: ComponentRef;
  lens: ComponentRef | null;
  status: string;
  overall_score: number | null;
  validated_rules: string[];
  blocking_reasons: string[];
  warnings: string[];
  user_comment: string | null;
  is_favorite: boolean;
  created_at: string;
  updated_at: string;
  validated_at: string | null;
}

export interface DashboardSummary {
  drivers_count: number;
  modules_count: number;
  lenses_count: number;
  recommendation_runs_count: number;
  compatible_rate_percent: number;
  recent_imports: ImportHistoryEntry[];
  recent_recommendations: RecommendationResponse[];
}

// --- Projets (CPS -> exigences -> etude -> scenarios) ---

export type ProjectStatus =
  | "draft"
  | "requirements_review"
  | "preliminary_analysis"
  | "study_in_progress"
  | "scenario_selection"
  | "photometric_validation"
  | "validated"
  | "archived";

export interface Project {
  id: number;
  reference: string | null;
  name: string;
  client_name: string | null;
  description: string | null;
  status: ProjectStatus;
  created_at: string;
  updated_at: string;
  cps_document_count: number;
  requirement_count: number;
  requirements_confirmed_count: number;
  requirements_to_review_count: number;
  preliminary_scenario_count: number;
  scenario_count: number;
  selected_scenario_code: string | null;
}

export interface ProjectCreateRequest {
  name: string;
  client_name?: string | null;
  description?: string | null;
}

export interface ProjectUpdateRequest {
  name?: string;
  client_name?: string | null;
  description?: string | null;
  status?: ProjectStatus;
}

export interface CpsDocumentOut {
  id: number;
  project_id: number;
  original_filename: string;
  document_type: string;
  page_count: number;
  uploaded_at: string;
  extraction_status: "pending" | "extracted" | "insufficient_text" | "failed";
  extraction_message: string | null;
}

export type RequirementValidationStatus = "detected" | "confirmed" | "modified" | "ignored" | "manual";
export type RequirementSourceType = "cps" | "natural_language" | "manual";

export interface ExtractedRequirementOut {
  id: number;
  project_id: number;
  cps_document_id: number | null;
  category: string;
  scope: string;
  field_name: string;
  operator: string;
  raw_value: string;
  numeric_value: number | null;
  unit: string | null;
  source_type: RequirementSourceType;
  source_page: number | null;
  source_excerpt: string | null;
  extraction_confidence: "high" | "medium" | "low";
  validation_status: RequirementValidationStatus;
  validated_value: string | null;
  validated_by: string | null;
  validated_at: string | null;
}

export interface RequirementUpdateRequest {
  action: "confirm" | "modify" | "ignore";
  validated_value?: string | null;
  validated_by: string;
}

export interface ManualRequirementCreateRequest {
  category: string;
  scope: string;
  field_name: string;
  operator?: string;
  value: string;
  unit?: string | null;
  validated_by: string;
}

export type ScenarioRunType = "preliminary" | "final";

export interface ProjectScenarioOut {
  id: number;
  project_id: number;
  scenario_code: string;
  run_type: ScenarioRunType;
  selected: boolean;
  selected_by: string | null;
  selected_at: string | null;
  selection_comment: string | null;
  recommendation: RecommendationItem;
  run_id: number;
}

export interface ScenarioSelectRequest {
  selected_by: string;
  selection_comment?: string | null;
}

export interface MissingFieldOut {
  field: string;
  label: string;
}

export interface RequirementsAnalysisOut {
  can_run_preliminary_study: boolean;
  missing_fields: MissingFieldOut[];
  requirements_detected_count: number;
  requirements_confirmed_count: number;
  requirements_to_review_count: number;
}

export interface CpsAnalysisResponse {
  document: CpsDocumentOut | null;
  requirements: ExtractedRequirementOut[] | null;
  analysis: RequirementsAnalysisOut;
  scenarios: ProjectScenarioOut[];
}

// --- Assistant IA (Groq) : autonome, ne depend d'aucun Projet ni du CPS ---

export interface AiFieldOut {
  field_name: string;
  scope: string;
  label: string;
  request_attr: string; // attribut correspondant sur RecommendationRequest
  operator: string;
  value: string | number | null;
  numeric_value: number | null;
  unit: string | null;
  confidence: "high" | "medium" | "low";
  source_text: string;
}

export interface AiAmbiguousFieldOut {
  field_name: string | null;
  scope: string | null;
  source_text: string;
  message: string;
}

export interface AiMissingFieldOut {
  request_attr: string;
  label: string;
}

export interface AiInterpretResponse {
  fields: AiFieldOut[];
  ambiguous_fields: AiAmbiguousFieldOut[];
  // Recap redige par le modele IA de ce qu'il a compris du texte (jamais une
  // recommandation produit/score).
  summary: string | null;
  missing_fields: AiMissingFieldOut[];
  can_search: boolean;
}
