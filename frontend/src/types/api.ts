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

export interface RecommendationItem {
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
  validation_status: string | null;
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
