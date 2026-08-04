import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useNavigate } from "react-router-dom";
import { Loader2, Sparkles, MousePointerClick, SlidersHorizontal } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { InfoTooltip } from "@/components/ui/tooltip";
import { ManualConfigurator } from "@/features/configurator/ManualConfigurator";
import { HybridConfigurator } from "@/features/configurator/HybridConfigurator";
import { recommendationFormSchema, setValueAsNumber, type RecommendationFormValues } from "@/schemas/recommendation";
import { createRecommendation } from "@/api/endpoints";
import { extractErrorMessage } from "@/api/client";
import type { SelectionMode } from "@/types/api";

const MODE_CARDS: { value: SelectionMode; title: string; description: string; icon: typeof Sparkles }[] = [
  {
    value: "automatic",
    title: "Recommandation automatique",
    description: "Le systeme choisit les trois composants selon les besoins du projet.",
    icon: Sparkles,
  },
  {
    value: "manual",
    title: "Selection manuelle assistee",
    description: "Vous choisissez module, driver et lentille ; le systeme verifie et note chaque choix.",
    icon: MousePointerClick,
  },
  {
    value: "hybrid",
    title: "Selection semi-automatique",
    description: "Vous imposez 1 ou 2 composants ; le systeme recommande le reste.",
    icon: SlidersHorizontal,
  },
];

interface FieldConfig {
  name: keyof RecommendationFormValues;
  label: string;
  unit: string;
  help: string;
  required?: boolean;
}

const REQUIRED_FIELDS: FieldConfig[] = [
  { name: "required_flux_lm", label: "Flux lumineux demande", unit: "lm", required: true, help: "Quantite de lumiere totale attendue du luminaire, en lumens." },
  { name: "max_power_w", label: "Puissance totale maximale", unit: "W", required: true, help: "Puissance electrique maximale autorisee pour l'ensemble driver + module." },
  { name: "required_cct_k", label: "Temperature de couleur (CCT)", unit: "K", required: true, help: "Teinte de la lumiere blanche souhaitee (ex: 3000 K = blanc chaud, 4000 K = blanc neutre)." },
  { name: "voltage_nominal_v", label: "Tension nominale du module", unit: "V", required: true, help: "Tension de fonctionnement attendue du module LED." },
  { name: "current_nominal_ma", label: "Courant nominal", unit: "mA", required: true, help: "Courant electrique attendu, en milliamperes." },
];

const OPTIONAL_NUMERIC_FIELDS: FieldConfig[] = [
  { name: "pole_height_m", label: "Hauteur du candelabre", unit: "m", help: "Hauteur de mât du candélabre (optionnel, utile pour l'analyse photometrique future)." },
  { name: "pole_spacing_m", label: "Espacement entre candelabres", unit: "m", help: "Distance entre deux mâts consecutifs (optionnel)." },
  { name: "ambient_temperature_c", label: "Temperature ambiante", unit: "°C", help: "Temperature ambiante maximale attendue sur site (optionnel, verifie la tenue thermique des composants)." },
];

export default function NewCalculationPage() {
  const navigate = useNavigate();
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [mode, setMode] = useState<SelectionMode>("automatic");

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RecommendationFormValues>({
    resolver: zodResolver(recommendationFormSchema),
  });

  const onSubmit = async (values: RecommendationFormValues) => {
    setSubmitError(null);
    try {
      const response = await createRecommendation({
        required_flux_lm: values.required_flux_lm,
        max_power_w: values.max_power_w,
        required_cct_k: values.required_cct_k,
        voltage_nominal_v: values.voltage_nominal_v,
        current_nominal_ma: values.current_nominal_ma,
        protocol: values.protocol || undefined,
        led_package: values.led_package || undefined,
        road_type: values.road_type || undefined,
        pole_height_m: values.pole_height_m,
        pole_spacing_m: values.pole_spacing_m,
        ambient_temperature_c: values.ambient_temperature_c,
      });
      navigate(`/resultats/${response.run_id}`);
    } catch (err) {
      setSubmitError(extractErrorMessage(err));
    }
  };

  return (
    <div>
      <PageHeader
        title="Nouveau calcul"
        description="Saisissez les besoins du projet pour obtenir une recommandation de driver, module et lentille."
      />

      <div className="mb-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
        {MODE_CARDS.map(({ value, title, description, icon: Icon }) => (
          <button
            key={value}
            type="button"
            onClick={() => setMode(value)}
            className={`flex flex-col items-start gap-2 rounded-lg border p-4 text-left transition-colors ${
              mode === value ? "border-primary bg-accent" : "border-border bg-card hover:bg-muted"
            }`}
          >
            <Icon className={`h-5 w-5 ${mode === value ? "text-accent-foreground" : "text-muted-foreground"}`} />
            <span className="text-sm font-semibold text-foreground">{title}</span>
            <span className="text-xs text-muted-foreground">{description}</span>
          </button>
        ))}
      </div>

      {mode === "manual" && <ManualConfigurator />}
      {mode === "hybrid" && <HybridConfigurator />}

      {mode === "automatic" && (
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Criteres obligatoires</CardTitle>
            <CardDescription>Ces cinq champs sont necessaires pour lancer un calcul.</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-1 gap-5 pt-0 sm:grid-cols-2">
            {REQUIRED_FIELDS.map((field) => (
              <div key={field.name} className="space-y-1.5">
                <Label htmlFor={field.name} className="flex items-center gap-1.5">
                  {field.label} <span className="text-destructive">*</span>
                  <InfoTooltip text={field.help} />
                  <span className="ml-auto text-xs font-normal text-muted-foreground">{field.unit}</span>
                </Label>
                <Input
                  id={field.name}
                  type="number"
                  step="any"
                  min={0}
                  placeholder={`Ex: en ${field.unit}`}
                  {...register(field.name, { setValueAs: setValueAsNumber })}
                />
                {errors[field.name] && (
                  <p className="text-xs text-destructive">{errors[field.name]?.message as string}</p>
                )}
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Criteres optionnels</CardTitle>
            <CardDescription>
              Affinent la recommandation. Laissez vide si inconnu — le systeme ne devine jamais une valeur.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-1 gap-5 pt-0 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="protocol" className="flex items-center gap-1.5">
                Protocole demande
                <InfoTooltip text="Protocole de variation / pilotage souhaite pour le driver." />
              </Label>
              <Select id="protocol" {...register("protocol")}>
                <option value="">Aucun / peu importe</option>
                <option value="DALI">DALI</option>
                <option value="DALI-2">DALI-2</option>
                <option value="D4i">D4i</option>
                <option value="0-10V">0-10V</option>
                <option value="1-10V">1-10V</option>
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="led_package" className="flex items-center gap-1.5">
                Package LED
                <InfoTooltip text="Format physique des LED du module (ex: 3535, 5050, COB)." />
              </Label>
              <Input id="led_package" placeholder="Ex: 3535" {...register("led_package")} />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="road_type" className="flex items-center gap-1.5">
                Type de voie
                <InfoTooltip text="Type de voie eclairee (route urbaine, nationale, autoroute...)." />
              </Label>
              <Input id="road_type" placeholder="Ex: route urbaine" {...register("road_type")} />
            </div>

            {OPTIONAL_NUMERIC_FIELDS.map((field) => (
              <div key={field.name} className="space-y-1.5">
                <Label htmlFor={field.name} className="flex items-center gap-1.5">
                  {field.label}
                  <InfoTooltip text={field.help} />
                  <span className="ml-auto text-xs font-normal text-muted-foreground">{field.unit}</span>
                </Label>
                <Input id={field.name} type="number" step="any" min={0} {...register(field.name, { setValueAs: setValueAsNumber })} />
                {errors[field.name] && (
                  <p className="text-xs text-destructive">{errors[field.name]?.message as string}</p>
                )}
              </div>
            ))}
          </CardContent>
        </Card>

        {submitError && (
          <div className="rounded-md border border-destructive-bg bg-destructive-bg p-3 text-sm text-destructive">
            {submitError}
          </div>
        )}

        <Button type="submit" size="lg" disabled={isSubmitting}>
          {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
          Lancer la recommandation
        </Button>
      </form>
      )}
    </div>
  );
}
