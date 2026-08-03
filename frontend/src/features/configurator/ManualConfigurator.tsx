import { useEffect, useState } from "react";
import { CheckCircle2, Loader2, Save } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ProductPicker } from "@/features/configurator/ProductPicker";
import { ValidationMatrix } from "@/features/configurator/ValidationMatrix";
import { AlternativesList } from "@/features/configurator/AlternativesList";
import { RequirementsFieldset } from "@/features/configurator/RequirementsFieldset";
import { getConfiguratorOptions, saveConfiguration, validateConfiguration } from "@/api/configurator";
import { extractErrorMessage } from "@/api/client";
import type { ComponentRef, ConfiguratorOptionsResponse, ConfiguratorResultResponse, PartialRequirements } from "@/types/api";

export function ManualConfigurator() {
  const [requirement, setRequirement] = useState<PartialRequirements>({});
  const [module, setModule] = useState<ComponentRef | null>(null);
  const [driver, setDriver] = useState<ComponentRef | null>(null);
  const [lens, setLens] = useState<ComponentRef | null>(null);
  const [options, setOptions] = useState<ConfiguratorOptionsResponse | null>(null);

  const [result, setResult] = useState<ConfiguratorResultResponse | null>(null);
  const [validating, setValidating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [comment, setComment] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  useEffect(() => {
    getConfiguratorOptions().then(setOptions).catch((err) => setError(extractErrorMessage(err)));
  }, []);

  const handleSelectModule = (item: ComponentRef) => {
    setModule(item);
    setDriver(null);
    setLens(null);
    setResult(null);
    setSaveMessage(null);
  };

  const handleValidate = async () => {
    if (!module) return;
    setValidating(true);
    setError(null);
    setSaveMessage(null);
    try {
      const res = await validateConfiguration({
        selection_mode: "manual",
        driver_id: driver?.id ?? null,
        module_id: module.id,
        lens_id: lens?.id ?? null,
        project_requirements: requirement,
      });
      setResult(res);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setValidating(false);
    }
  };

  const handleSave = async () => {
    if (!module || !result) return;
    setSaving(true);
    setError(null);
    try {
      await saveConfiguration({
        selection_mode: "manual",
        driver_id: driver?.id ?? null,
        module_id: module.id,
        lens_id: lens?.id ?? null,
        status: result.status,
        overall_score: result.scores
          ? Math.round(
              (result.scores.electrical + result.scores.photometric + result.scores.mechanical + result.scores.thermal + result.scores.data_quality) * 10
            ) / 10
          : null,
        validated_rules: result.validated_rules,
        blocking_reasons: result.blocking_reasons,
        warnings: result.warnings,
        user_comment: comment || null,
      });
      setSaveMessage("Configuration enregistree avec succes.");
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <RequirementsFieldset value={requirement} onChange={setRequirement} />

      <Card>
        <CardHeader>
          <CardTitle>1. Module LED</CardTitle>
          <CardDescription>Choisissez le module LED de depart.</CardDescription>
        </CardHeader>
        <CardContent className="pt-0">
          <ProductPicker
            entityType="module"
            requirement={requirement}
            manufacturers={options?.manufacturers.modules ?? []}
            selectedId={module?.id ?? null}
            onSelect={handleSelectModule}
            label="module"
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>2. Driver</CardTitle>
          <CardDescription>Drivers affiches avec leur statut de compatibilite vis-a-vis du module choisi.</CardDescription>
        </CardHeader>
        <CardContent className="pt-0">
          <ProductPicker
            entityType="driver"
            moduleId={module?.id}
            requirement={requirement}
            manufacturers={options?.manufacturers.drivers ?? []}
            selectedId={driver?.id ?? null}
            onSelect={(item) => {
              setDriver(item);
              setResult(null);
              setSaveMessage(null);
            }}
            label="driver"
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>3. Lentille</CardTitle>
          <CardDescription>Optionnelle — la lentille peut etre completee plus tard.</CardDescription>
        </CardHeader>
        <CardContent className="pt-0">
          <ProductPicker
            entityType="lens"
            moduleId={module?.id}
            requirement={requirement}
            manufacturers={options?.manufacturers.lenses ?? []}
            selectedId={lens?.id ?? null}
            onSelect={(item) => {
              setLens(item);
              setResult(null);
              setSaveMessage(null);
            }}
            label="lentille"
          />
        </CardContent>
      </Card>

      <div className="flex flex-wrap items-center gap-3">
        <Button onClick={handleValidate} disabled={!module || validating}>
          {validating && <Loader2 className="h-4 w-4 animate-spin" />}
          4. Verifier la configuration
        </Button>
        {result && (
          <Button variant="outline" onClick={handleSave} disabled={saving}>
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            Enregistrer la configuration
          </Button>
        )}
      </div>

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
            <CardTitle>Resultat de la validation</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 pt-0">
            <ValidationMatrix result={result} />

            <div className="space-y-1.5">
              <Label htmlFor="manual-comment">Commentaire (optionnel, enregistre avec la configuration)</Label>
              <Input id="manual-comment" value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Ex: valide pour le projet Rue de la Gare" />
            </div>

            <AlternativesList
              alternatives={result.alternatives}
              onUseAlternative={(alt) => {
                if (alt.driver) setDriver(alt.driver);
                if (alt.lens) setLens(alt.lens);
                setResult(null);
                setSaveMessage(null);
              }}
            />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
