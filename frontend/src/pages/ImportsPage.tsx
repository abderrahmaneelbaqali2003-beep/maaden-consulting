import { useState } from "react";
import { UploadCloud, FileSearch, CheckCircle2, AlertTriangle } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { analyzeImportFile, importFile } from "@/api/endpoints";
import { extractErrorMessage } from "@/api/client";
import type { AnalyzeResponse, ImportResponse } from "@/types/api";

type EntityKey = "drivers" | "modules" | "lenses";

const ENTITY_LABELS: Record<EntityKey, string> = {
  drivers: "Drivers",
  modules: "Modules LED",
  lenses: "Lentilles",
};

export default function ImportsPage() {
  const [entity, setEntity] = useState<EntityKey>("drivers");
  const [file, setFile] = useState<File | null>(null);
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null);
  const [result, setResult] = useState<ImportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const reset = () => {
    setAnalysis(null);
    setResult(null);
    setError(null);
  };

  const handleAnalyze = async () => {
    if (!file) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const res = await analyzeImportFile(file);
      setAnalysis(res);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const handleConfirmImport = async () => {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const res = await importFile(entity, file);
      setResult(res);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <PageHeader
        title="Imports"
        description="Importez de nouvelles references (drivers, modules LED, lentilles) au format Excel (.xlsx, .xls) ou CSV."
      />

      <Card>
        <CardHeader>
          <CardTitle>1. Selection du fichier</CardTitle>
          <CardDescription>Extensions autorisees : .xlsx, .xls, .csv.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 pt-0">
          <div className="max-w-xs space-y-1.5">
            <Label htmlFor="entity">Type de donnees</Label>
            <Select
              id="entity"
              value={entity}
              onChange={(e) => {
                setEntity(e.target.value as EntityKey);
                reset();
                setFile(null);
              }}
            >
              <option value="drivers">Drivers</option>
              <option value="modules">Modules LED</option>
              <option value="lenses">Lentilles</option>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="file">Fichier</Label>
            <input
              id="file"
              type="file"
              accept=".xlsx,.xls,.csv"
              onChange={(e) => {
                setFile(e.target.files?.[0] ?? null);
                reset();
              }}
              className="block w-full text-sm text-foreground file:mr-4 file:rounded-md file:border-0 file:bg-secondary file:px-4 file:py-2 file:text-sm file:font-medium file:text-secondary-foreground"
            />
          </div>

          <div className="flex gap-3">
            <Button onClick={handleAnalyze} disabled={!file || busy} variant="outline">
              <FileSearch className="h-4 w-4" /> Analyser
            </Button>
            <Button onClick={handleConfirmImport} disabled={!file || busy}>
              <UploadCloud className="h-4 w-4" /> Confirmer l'import ({ENTITY_LABELS[entity]})
            </Button>
          </div>
        </CardContent>
      </Card>

      {error && (
        <div className="mt-4 rounded-md border border-destructive-bg bg-destructive-bg p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {analysis && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>2. Analyse et apercu</CardTitle>
            <CardDescription>
              Feuille detectee : {analysis.sheet_name} — {analysis.row_count} lignes —{" "}
              {analysis.duplicate_rows} doublon(s) exact(s) detecte(s)
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-0">
            <p className="mb-2 text-sm font-medium">Colonnes detectees ({analysis.columns.length})</p>
            <div className="mb-4 max-h-52 overflow-y-auto rounded-md border border-border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Colonne</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Manquants</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {analysis.columns.map((col) => (
                    <TableRow key={col.name}>
                      <TableCell className="font-mono text-xs">{col.name}</TableCell>
                      <TableCell className="text-xs">{col.dtype}</TableCell>
                      <TableCell className="text-xs">
                        {col.missing_count} ({col.missing_percent}%)
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            <p className="mb-2 text-sm font-medium">Apercu (10 premieres lignes)</p>
            <div className="overflow-x-auto rounded-md border border-border">
              <table className="w-full text-xs">
                <thead className="bg-muted">
                  <tr>
                    {analysis.columns.slice(0, 8).map((col) => (
                      <th key={col.name} className="px-2 py-1.5 text-left font-medium">
                        {col.name}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {analysis.preview.map((row, i) => (
                    <tr key={i} className="border-t border-border">
                      {analysis.columns.slice(0, 8).map((col) => (
                        <td key={col.name} className="px-2 py-1.5">
                          {row[col.name] === null || row[col.name] === undefined
                            ? "—"
                            : String(row[col.name])}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {result && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-success" /> 3. Rapport d'import
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="mb-4 grid grid-cols-4 gap-4 text-sm">
              <div>
                <p className="text-xl font-semibold">{result.rows_total}</p>
                <p className="text-muted-foreground">Lignes totales</p>
              </div>
              <div>
                <p className="text-xl font-semibold text-success">{result.rows_imported}</p>
                <p className="text-muted-foreground">Nouvelles</p>
              </div>
              <div>
                <p className="text-xl font-semibold text-secondary">{result.rows_updated}</p>
                <p className="text-muted-foreground">Mises a jour</p>
              </div>
              <div>
                <p className="text-xl font-semibold text-destructive">{result.rows_rejected}</p>
                <p className="text-muted-foreground">Rejetees</p>
              </div>
            </div>

            {result.issues.length > 0 && (
              <div>
                <p className="mb-1 flex items-center gap-1.5 text-sm font-medium text-warning">
                  <AlertTriangle className="h-4 w-4" /> Erreurs ligne par ligne
                </p>
                <ul className="max-h-64 space-y-1 overflow-y-auto text-sm text-muted-foreground">
                  {result.issues.map((issue, i) => (
                    <li key={i} className="border-b border-border py-1">
                      Ligne {issue.row_number}
                      {issue.external_ref ? ` (${issue.external_ref})` : ""} : {issue.description}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
