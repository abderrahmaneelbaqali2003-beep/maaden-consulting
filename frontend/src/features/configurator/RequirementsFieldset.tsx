import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { InfoTooltip } from "@/components/ui/tooltip";
import type { PartialRequirements } from "@/types/api";

const NUMERIC_FIELDS: { name: keyof PartialRequirements; label: string; unit: string; help: string }[] = [
  { name: "required_flux_lm", label: "Flux lumineux demande", unit: "lm", help: "Utilise pour le score de correspondance flux/CCT et pour rechercher un module en mode semi-automatique." },
  { name: "max_power_w", label: "Puissance totale maximale", unit: "W", help: "Puissance electrique maximale autorisee." },
  { name: "required_cct_k", label: "Temperature de couleur (CCT)", unit: "K", help: "Teinte de lumiere blanche souhaitee." },
  { name: "voltage_nominal_v", label: "Tension nominale du module", unit: "V", help: "Tension de fonctionnement attendue." },
  { name: "current_nominal_ma", label: "Courant nominal", unit: "mA", help: "Courant electrique attendu." },
  { name: "ambient_temperature_c", label: "Temperature ambiante", unit: "°C", help: "Verifie la tenue thermique des composants selectionnes." },
];

export function RequirementsFieldset({
  value,
  onChange,
}: {
  value: PartialRequirements;
  onChange: (value: PartialRequirements) => void;
}) {
  const setNumber = (name: keyof PartialRequirements) => (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value;
    onChange({ ...value, [name]: raw === "" ? undefined : Number(raw) });
  };
  const setText = (name: keyof PartialRequirements) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    onChange({ ...value, [name]: e.target.value || undefined });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Besoins du projet</CardTitle>
        <CardDescription>
          Optionnels en selection manuelle/semi-automatique — completez-les pour affiner le score et la matrice de
          validation. Le flux et la CCT sont necessaires pour rechercher un module en mode semi-automatique.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid grid-cols-1 gap-5 pt-0 sm:grid-cols-3">
        {NUMERIC_FIELDS.map((field) => (
          <div key={field.name} className="space-y-1.5">
            <Label htmlFor={`req-${field.name}`} className="flex items-center gap-1.5">
              {field.label}
              <InfoTooltip text={field.help} />
              <span className="ml-auto text-xs font-normal text-muted-foreground">{field.unit}</span>
            </Label>
            <Input
              id={`req-${field.name}`}
              type="number"
              step="any"
              min={0}
              value={(value[field.name] as number | undefined) ?? ""}
              onChange={setNumber(field.name)}
            />
          </div>
        ))}

        <div className="space-y-1.5">
          <Label htmlFor="req-protocol">Protocole demande</Label>
          <Select id="req-protocol" value={value.protocol ?? ""} onChange={setText("protocol")}>
            <option value="">Aucun / peu importe</option>
            <option value="DALI">DALI</option>
            <option value="DALI-2">DALI-2</option>
            <option value="D4i">D4i</option>
            <option value="0-10V">0-10V</option>
            <option value="1-10V">1-10V</option>
          </Select>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="req-led-package">Package LED</Label>
          <Input id="req-led-package" placeholder="Ex: 3535" value={value.led_package ?? ""} onChange={setText("led_package")} />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="req-road-type">Type de voie</Label>
          <Input id="req-road-type" placeholder="Ex: route urbaine" value={value.road_type ?? ""} onChange={setText("road_type")} />
        </div>
      </CardContent>
    </Card>
  );
}
