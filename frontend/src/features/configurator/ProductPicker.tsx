import { useEffect, useState } from "react";
import { Search, Loader2, Eye, EyeOff, Check } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { extractErrorMessage } from "@/api/client";
import { listConfiguratorDrivers, listConfiguratorLenses, listConfiguratorModules } from "@/api/configurator";
import type { ConfiguratorOptionItem, PartialRequirements, RecommendationStatus } from "@/types/api";

type EntityType = "module" | "driver" | "lens";

const STATUS_LABEL: Record<RecommendationStatus, { label: string; variant: "success" | "warning" | "destructive" | "info" }> = {
  compatible: { label: "Compatible", variant: "success" },
  compatible_with_warning: { label: "Compatible avec avertissement", variant: "warning" },
  manual_validation_required: { label: "Compatible avec avertissement", variant: "warning" },
  data_incomplete: { label: "Donnees incompletes", variant: "info" },
  not_compatible: { label: "Incompatible", variant: "destructive" },
  impossible: { label: "Incompatible", variant: "destructive" },
};

function specsLine(entityType: EntityType, specs: Record<string, unknown>): string {
  if (entityType === "module") {
    return `${specs.flux_lm ?? "?"} lm · ${specs.cct_k ?? "?"} K · ${specs.power_w ?? "?"} W · pkg ${specs.led_package ?? "?"}`;
  }
  if (entityType === "driver") {
    const protocols = Array.isArray(specs.protocols) && specs.protocols.length ? specs.protocols.join(", ") : "aucun protocole avance";
    return `${specs.voltage_range_v ?? "?"} V · ${specs.current_range_ma ?? "?"} mA · ${specs.power_max_w ?? "?"} W max · ${protocols}`;
  }
  return `pkg ${specs.compatible_led_package ?? "?"} · ${specs.distribution ?? "distribution inconnue"} · IES/LDT ${
    specs.ies_or_ldt_available ? "disponible" : "absent"
  }`;
}

export function ProductPicker({
  entityType,
  moduleId,
  requirement,
  manufacturers,
  selectedId,
  onSelect,
  label,
}: {
  entityType: EntityType;
  moduleId?: number | null;
  requirement: PartialRequirements;
  manufacturers: string[];
  selectedId: number | null;
  onSelect: (item: ConfiguratorOptionItem) => void;
  label: string;
}) {
  const [items, setItems] = useState<ConfiguratorOptionItem[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [manufacturer, setManufacturer] = useState("");
  const [showIncompatible, setShowIncompatible] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const needsModule = entityType !== "module";

  useEffect(() => {
    if (needsModule && !moduleId) {
      setItems([]);
      return;
    }
    setLoading(true);
    setError(null);

    const params = {
      search: search || undefined,
      manufacturer: manufacturer || undefined,
      page,
      page_size: 10,
      required_flux_lm: requirement.required_flux_lm ?? undefined,
      max_power_w: requirement.max_power_w ?? undefined,
      required_cct_k: requirement.required_cct_k ?? undefined,
      ambient_temperature_c: requirement.ambient_temperature_c ?? undefined,
    };

    const request =
      entityType === "module"
        ? listConfiguratorModules(params)
        : entityType === "driver"
          ? listConfiguratorDrivers(moduleId as number, params)
          : listConfiguratorLenses(moduleId as number, params);

    request
      .then((res) => {
        setItems(res.items);
        setTotal(res.total);
        setTotalPages(res.total_pages || 1);
      })
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entityType, moduleId, search, manufacturer, page]);

  useEffect(() => {
    setPage(1);
  }, [search, manufacturer, entityType, moduleId]);

  if (needsModule && !moduleId) {
    return (
      <div className="rounded-md border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
        Choisissez d'abord un module LED.
      </div>
    );
  }

  const visibleItems = showIncompatible ? items : items.filter((i) => i.status !== "not_compatible" && i.status !== "impossible");

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <div className="relative max-w-xs flex-1">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder={`Rechercher un ${label.toLowerCase()}...`}
            className="pl-8"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Select className="max-w-[180px]" value={manufacturer} onChange={(e) => setManufacturer(e.target.value)}>
          <option value="">Tous les fabricants</option>
          {manufacturers.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </Select>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => setShowIncompatible((v) => !v)}
          title="Afficher les composants incompatibles"
        >
          {showIncompatible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          {showIncompatible ? "Masquer les incompatibles" : "Afficher les incompatibles"}
        </Button>
        <span className="ml-auto text-xs text-muted-foreground">{total} resultat(s)</span>
      </div>

      {error && <p className="mb-2 text-sm text-destructive">{error}</p>}

      {loading ? (
        <div className="flex items-center justify-center gap-2 py-8 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Chargement...
        </div>
      ) : visibleItems.length === 0 ? (
        <div className="rounded-md border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
          Aucun resultat.{" "}
          {!showIncompatible && items.length > 0 && (
            <button type="button" className="text-secondary hover:underline" onClick={() => setShowIncompatible(true)}>
              Afficher les {items.length} composant(s) incompatible(s) masque(s).
            </button>
          )}
        </div>
      ) : (
        <ul className="divide-y divide-border rounded-md border border-border">
          {visibleItems.map((item) => {
            const statusInfo = item.status ? STATUS_LABEL[item.status] : null;
            const isIncompatible = item.status === "not_compatible" || item.status === "impossible";
            const isSelected = item.id === selectedId;
            return (
              <li key={item.id} className={`flex items-center justify-between gap-3 p-3 ${isSelected ? "bg-accent" : ""}`}>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="truncate text-sm font-medium text-foreground">
                      {item.manufacturer} {item.reference}
                    </p>
                    {statusInfo && <Badge variant={statusInfo.variant}>{statusInfo.label}</Badge>}
                  </div>
                  <p className="truncate text-xs text-muted-foreground">{specsLine(entityType, item.key_specs)}</p>
                </div>
                <Button
                  type="button"
                  size="sm"
                  variant={isSelected ? "default" : "outline"}
                  disabled={isIncompatible && !showIncompatible}
                  onClick={() => onSelect(item)}
                  title={isIncompatible ? "Composant marque incompatible avec le module/besoin actuel" : undefined}
                >
                  {isSelected && <Check className="h-4 w-4" />}
                  {isSelected ? "Selectionne" : "Choisir"}
                </Button>
              </li>
            );
          })}
        </ul>
      )}

      {totalPages > 1 && (
        <div className="mt-3 flex items-center justify-between text-sm">
          <span className="text-muted-foreground">
            Page {page} / {totalPages}
          </span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              Precedent
            </Button>
            <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
              Suivant
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
