import { CheckCircle2, AlertTriangle, XCircle, HelpCircle } from "lucide-react";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/StatusBadge";
import type { ConfiguratorResultResponse } from "@/types/api";

const CRITERION_RESULT_LABEL: Record<string, { label: string; variant: "success" | "warning" | "destructive" | "info"; icon: typeof CheckCircle2 }> = {
  valid: { label: "Valide", variant: "success", icon: CheckCircle2 },
  warning: { label: "Avertissement", variant: "warning", icon: AlertTriangle },
  blocking: { label: "Bloquant", variant: "destructive", icon: XCircle },
  not_verifiable: { label: "A valider", variant: "info", icon: HelpCircle },
};

export function ValidationMatrix({ result }: { result: ConfiguratorResultResponse }) {
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <StatusBadge status={result.status} />
        {result.scores && <span className="text-lg font-semibold">{result.scores.electrical + result.scores.photometric + result.scores.mechanical + result.scores.thermal + result.scores.data_quality}/100</span>}
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Critere</TableHead>
            <TableHead>Resultat</TableHead>
            <TableHead>Detail</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {result.criteria.map((c) => {
            const info = CRITERION_RESULT_LABEL[c.status] ?? CRITERION_RESULT_LABEL.not_verifiable;
            const Icon = info.icon;
            return (
              <TableRow key={c.criterion}>
                <TableCell className="font-medium">{c.label}</TableCell>
                <TableCell>
                  <Badge variant={info.variant}>
                    <Icon className="h-3 w-3" /> {info.label}
                  </Badge>
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">{c.detail}</TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>

      {result.scores && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          {[
            ["Electrique", result.scores.electrical, 35],
            ["Flux / CCT", result.scores.photometric, 25],
            ["Mecanique", result.scores.mechanical, 20],
            ["Thermique", result.scores.thermal, 10],
            ["Qualite donnees", result.scores.data_quality, 10],
          ].map(([label, value, max]) => (
            <div key={label as string} className="rounded-md border border-border p-3 text-center">
              <p className="text-xs text-muted-foreground">{label}</p>
              <p className="text-sm font-semibold">
                {value}/{max}
              </p>
            </div>
          ))}
        </div>
      )}

      {result.blocking_reasons.length > 0 && (
        <div>
          <p className="mb-1 flex items-center gap-1.5 text-sm font-medium text-destructive">
            <XCircle className="h-4 w-4" /> Raisons bloquantes
          </p>
          <ul className="ml-6 list-disc space-y-0.5 text-sm text-foreground">
            {result.blocking_reasons.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </div>
      )}

      {result.warnings.length > 0 && (
        <div>
          <p className="mb-1 flex items-center gap-1.5 text-sm font-medium text-warning">
            <AlertTriangle className="h-4 w-4" /> Avertissements
          </p>
          <ul className="ml-6 list-disc space-y-0.5 text-sm text-muted-foreground">
            {result.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {result.suggestions.length > 0 && (
        <div>
          <p className="mb-1 text-sm font-medium text-foreground">Suggestions</p>
          <ul className="ml-6 list-disc space-y-0.5 text-sm text-muted-foreground">
            {result.suggestions.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>
      )}

      {result.explanation && <p className="rounded-md bg-muted p-3 text-sm text-foreground">{result.explanation}</p>}
    </div>
  );
}
