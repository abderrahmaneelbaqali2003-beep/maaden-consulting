import { useEffect, useState } from "react";
import { CheckCircle2, Loader2, Save } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ProductPicker } from "@/features/configurator/ProductPicker";
import { StandaloneCatalogPicker } from "@/features/configurator/StandaloneCatalogPicker";
import { ValidationMatrix } from "@/features/configurator/ValidationMatrix";
import { AlternativesList } from "@/features/configurator/AlternativesList";
import { RequirementsFieldset } from "@/features/configurator/RequirementsFieldset";
import { getConfiguratorOptions, recommendMissing, saveConfiguration } from "@/api/configurator";
import { extractErrorMessage } from "@/api/client";
import type { ComponentRef, ConfiguratorOptionsResponse, ConfiguratorResultResponse, PartialRequirements } from "@/types/api";

type Slot = "module" | "driver" | "lens";

const SLOT_LABEL: Record<Slot, string> = { module: "le module LED", driver: "le driver", lens: "la lentille" };

export function HybridConfigurator() {
  const [imposedSlots, setImposedSlots] = useState<Slot[]>(["module"]);
  const [requirement, setRequirement] = useState<PartialRequirements>({});
  const [module, setModule] = useState<ComponentRef | null>(null);
  const [driver, setDriver] = useState<ComponentRef | null>(null);
  const [lens, setLens] = useState<ComponentRef | null>(null);
  const [options, setOptions] = useState<ConfiguratorOptionsResponse | null>(null);

  const [result, setResult] = useState<ConfiguratorResultResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  useEffect(() => {
    getConfiguratorOptions().then(setOptions).catch((err) => setError(extractErrorMessage(err)));
  }, []);

  const toggleSlot = (slot: Slot) => {
    setImposedSlots((current) => {
      if (current.includes(slot)) return current.filter((s) => s !== slot);
      if (current.length >= 2) return current; // maximum 2 composants imposes
      return [...current, slot];
    });
    setResult(null);
    setSaveMessage(null);
  };

  const handleRecommend = async () => {
    setLoading(true);
    setError(null);
    setSaveMessage(null);
    try {
      const res = await recommendMissing({
        driver_id: imposedSlots.includes("driver") ? driver?.id ?? null : null,
        module_id: imposedSlots.includes("module") ? module?.id ?? null : null,
        lens_id: imposedSlots.includes("lens") ? lens?.id ?? null : null,
        project_requirements: requirement,
      });
      setResult(res);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!result?.module) return;
    setSaving(true);
    setError(null);
    try {
      await saveConfiguration({
        selection_mode: "hybrid",
        driver_id: result.driver?.id ?? null,
        module_id: result.module.id,
        lens_id: result.lens?.id ?? null,
        status: result.status,
        overall_score: result.scores
          ? Math.round(
              (result.scores.electrical + result.scores.photometric + result.scores.mechanical + result.scores.thermal + result.scores.data_quality) * 10
            ) / 10
          : null,
        validated_rules: result.validated_rules,
        blocking_reasons: result.blocking_reasons,
        warnings: result.warnings,
      });
      setSaveMessage("Configuration enregistree avec succes.");
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const canRecommend = imposedSlots.every((slot) => (slot === "module" ? module : slot === "driver" ? driver : lens));

  return (
    <div className="space-y-6">
      <RequirementsFieldset value={requirement} onChange={setRequirement} />

      <Card>
        <CardHeader>
          <CardTitle>Composant(s) impose(s)</CardTitle>
          <CardDescription>
            Choisissez 1 ou 2 composants a imposer ; le moteur recommandera automatiquement le(s) reste.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3 pt-0">
          {(["module", "driver", "lens"] as Slot[]).map((slot) => (
            <label
              key={slot}
              className="flex cursor-pointer items-center gap-2 rounded-md border border-border px-3 py-2 text-sm has-[:checked]:border-secondary has-[:checked]:bg-accent"
            >
              <input type="checkbox" checked={imposedSlots.includes(slot)} onChange={() => toggleSlot(slot)} />
              Imposer {SLOT_LABEL[slot]}
            </label>
          ))}
        </CardContent>
      </Card>

      {imposedSlots.includes("module") && (
        <Card>
          <CardHeader>
            <CardTitle>Module LED impose</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <ProductPicker
              entityType="module"
              requirement={requirement}
              manufacturers={options?.manufacturers.modules ?? []}
              selectedId={module?.id ?? null}
              onSelect={(item) => {
                setModule(item);
                setResult(null);
              }}
              label="module"
            />
          </CardContent>
        </Card>
      )}

      {imposedSlots.includes("driver") && (
        <Card>
          <CardHeader>
            <CardTitle>Driver impose</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            {imposedSlots.includes("module") && module ? (
              <ProductPicker
                entityType="driver"
                moduleId={module.id}
                requirement={requirement}
                manufacturers={options?.manufacturers.drivers ?? []}
                selectedId={driver?.id ?? null}
                onSelect={(item) => {
                  setDriver(item);
                  setResult(null);
                }}
                label="driver"
              />
            ) : (
              <StandaloneCatalogPicker
                entityType="driver"
                selectedId={driver?.id ?? null}
                onSelect={(item) => {
                  setDriver(item);
                  setResult(null);
                }}
              />
            )}
          </CardContent>
        </Card>
      )}

      {imposedSlots.includes("lens") && (
        <Card>
          <CardHeader>
            <CardTitle>Lentille imposee</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            {imposedSlots.includes("module") && module ? (
              <ProductPicker
                entityType="lens"
                moduleId={module.id}
                requirement={requirement}
                manufacturers={options?.manufacturers.lenses ?? []}
                selectedId={lens?.id ?? null}
                onSelect={(item) => {
                  setLens(item);
                  setResult(null);
                }}
                label="lentille"
              />
            ) : (
              <StandaloneCatalogPicker
                entityType="lens"
                selectedId={lens?.id ?? null}
                onSelect={(item) => {
                  setLens(item);
                  setResult(null);
                }}
              />
            )}
          </CardContent>
        </Card>
      )}

      <Button onClick={handleRecommend} disabled={!canRecommend || loading}>
        {loading && <Loader2 className="h-4 w-4 animate-spin" />}
        Lancer la recommandation semi-automatique
      </Button>

      {error && (
        <div className="rounded-md border border-destructive-bg bg-destructive-bg p-3 text-sm text-destructive">{error}</div>
      )}
      {saveMessage && (
        <p className="flex items-center gap-1.5 text-sm text-success">
          <CheckCircle2 className="h-4 w-4" /> {saveMessage}
        </p>
      )}

      {result && (
        <Card>
          <CardHeader>
            <CardTitle>Configuration recommandee</CardTitle>
            <CardDescription>
              {result.driver ? `${result.driver.manufacturer} ${result.driver.reference}` : "Sans driver"} —{" "}
              {result.module ? `${result.module.manufacturer} ${result.module.reference}` : "Sans module"} —{" "}
              {result.lens ? `${result.lens.manufacturer} ${result.lens.reference}` : "Sans lentille"}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 pt-0">
            <ValidationMatrix result={result} />
            <div className="flex gap-3">
              <Button variant="outline" onClick={handleSave} disabled={saving || !result.module}>
                {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                Enregistrer la configuration
              </Button>
            </div>
            <AlternativesList alternatives={result.alternatives} />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
