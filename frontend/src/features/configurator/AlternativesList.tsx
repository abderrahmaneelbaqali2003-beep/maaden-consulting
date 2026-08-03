import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/StatusBadge";
import type { AlternativeConfigurationOut } from "@/types/api";

export function AlternativesList({
  alternatives,
  onUseAlternative,
}: {
  alternatives: AlternativeConfigurationOut[];
  onUseAlternative?: (alt: AlternativeConfigurationOut) => void;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div>
      <Button type="button" variant="outline" size="sm" onClick={() => setOpen((v) => !v)} disabled={alternatives.length === 0}>
        {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        Voir les alternatives ({alternatives.length})
      </Button>

      {open && (
        <ul className="mt-3 space-y-2">
          {alternatives.length === 0 && (
            <li className="text-sm text-muted-foreground">Aucune alternative compatible trouvee pour ce module.</li>
          )}
          {alternatives.map((alt, i) => (
            <li key={i} className="flex items-center justify-between gap-3 rounded-md border border-border p-3">
              <div className="min-w-0 flex-1 text-sm">
                <div className="flex items-center gap-2">
                  <span className="font-medium">
                    {alt.driver ? `${alt.driver.manufacturer} ${alt.driver.reference}` : "Sans driver"}
                    {alt.lens ? ` + ${alt.lens.manufacturer} ${alt.lens.reference}` : " + sans lentille"}
                  </span>
                  <StatusBadge status={alt.status} />
                </div>
                <p className="text-xs text-muted-foreground">Score global : {alt.overall_score}/100</p>
              </div>
              {onUseAlternative && (
                <Button type="button" size="sm" variant="outline" onClick={() => onUseAlternative(alt)}>
                  Utiliser
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
