import { apiClient } from "@/api/client";
import type {
  ConfiguratorOptionItem,
  ConfiguratorOptionsResponse,
  ConfiguratorResultResponse,
  PaginatedResponse,
  RecommendMissingRequest,
  SaveConfigurationRequest,
  SavedConfigurationRead,
  ValidateConfigurationRequest,
} from "@/types/api";

export const getConfiguratorOptions = () =>
  apiClient.get<ConfiguratorOptionsResponse>("/api/configurator/options").then((r) => r.data);

export interface ConfiguratorListParams {
  search?: string;
  manufacturer?: string;
  led_package?: string;
  protocol?: string;
  include_inactive?: boolean;
  page?: number;
  page_size?: number;
  required_flux_lm?: number;
  max_power_w?: number;
  required_cct_k?: number;
  ambient_temperature_c?: number;
  [key: string]: string | number | boolean | undefined;
}

export const listConfiguratorModules = (params: ConfiguratorListParams = {}) =>
  apiClient
    .get<PaginatedResponse<ConfiguratorOptionItem>>("/api/configurator/modules", { params })
    .then((r) => r.data);

export const listConfiguratorDrivers = (moduleId: number, params: ConfiguratorListParams = {}) =>
  apiClient
    .get<PaginatedResponse<ConfiguratorOptionItem>>("/api/configurator/drivers", {
      params: { ...params, module_id: moduleId },
    })
    .then((r) => r.data);

export const listConfiguratorLenses = (moduleId: number, params: ConfiguratorListParams = {}) =>
  apiClient
    .get<PaginatedResponse<ConfiguratorOptionItem>>("/api/configurator/lenses", {
      params: { ...params, module_id: moduleId },
    })
    .then((r) => r.data);

export const validateConfiguration = (payload: ValidateConfigurationRequest) =>
  apiClient.post<ConfiguratorResultResponse>("/api/configurator/validate", payload).then((r) => r.data);

export const recommendMissing = (payload: RecommendMissingRequest) =>
  apiClient.post<ConfiguratorResultResponse>("/api/configurator/recommend-missing", payload).then((r) => r.data);

export const saveConfiguration = (payload: SaveConfigurationRequest) =>
  apiClient.post<SavedConfigurationRead>("/api/configurator/save", payload).then((r) => r.data);
