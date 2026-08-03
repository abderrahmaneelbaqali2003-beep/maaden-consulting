import { Badge } from "@/components/ui/badge";
import type { RecommendationStatus } from "@/types/api";

const STATUS_CONFIG: Record<RecommendationStatus, { label: string; variant: "success" | "warning" | "destructive" | "info" | "default" }> = {
  compatible: { label: "Compatible", variant: "success" },
  compatible_with_warning: { label: "Compatible (avertissement)", variant: "warning" },
  data_incomplete: { label: "Donnees incompletes", variant: "info" },
  manual_validation_required: { label: "Validation manuelle requise", variant: "warning" },
  not_compatible: { label: "Non compatible", variant: "destructive" },
  impossible: { label: "Impossible", variant: "destructive" },
};

export function StatusBadge({ status }: { status: RecommendationStatus }) {
  const config = STATUS_CONFIG[status] ?? { label: status, variant: "default" as const };
  return <Badge variant={config.variant}>{config.label}</Badge>;
}
