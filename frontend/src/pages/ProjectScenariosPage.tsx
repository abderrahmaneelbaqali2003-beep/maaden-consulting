import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, AlertTriangle, CheckCircle2, FileDown, Loader2 } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { LoadingState } from "@/components/LoadingState";
import { ErrorState } from "@/components/ErrorState";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog } from "@/components/ui/dialog";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { getProject, listScenarios, selectScenario, downloadProjectReport } from "@/api/endpoints";
import { extractErrorMessage, extractBlobErrorMessage } from "@/api/client";
import type { Project, ProjectScenarioOut } from "@/types/api";

function SelectScenarioDialog({
  scenario, open, onClose, onSelected,
}: {
  scenario: ProjectScenarioOut | null; open: boolean; onClose: () => void; onSelected: () => void;
}) {
  const [name, setName] = useState("");
  const [comment, setComment] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (open) {
      setName("");
      setComment("");
      setError(null);
      setSubmitting(false);
    }
  }, [open]);

  if (!scenario) return null;

  const handleConfirm = async () => {
    if (!name.trim()) {
      setError("Le nom du consultant est obligatoire.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await selectScenario(scenario.project_id, scenario.id, { selected_by: name.trim(), selection_comment: comment.trim() || null });
      onSelected();
    } catch (err) {
      setError(extractErrorMessage(err));
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} title={`Confirmer le choix du scenario ${scenario.scenario_code}`}>
      <div className="space-y-4">
        <div>
          <Label htmlFor="select_name">Consultant *</Label>
          <Input id="select_name" value={name} onChange={(e) => setName(e.target.value)} className="mt-1" />
        </div>
        <div>
          <Label htmlFor="select_comment">Motif du choix</Label>
          <textarea
            id="select_comment" value={comment} onChange={(e) => setComment(e.target.value)} rows={3}
            className="mt-1 flex w-full rounded-md border border-input bg-card px-3 py-2 text-sm text-foreground"
            placeholder="Optionnel — ex: meilleur compromis consommation / cout"
          />
        </div>
        {error && <p className="text-sm text-destructive">{error}</p>}
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" onClick={onClose} disabled={submitting}>Annuler</Button>
          <Button onClick={handleConfirm} disabled={submitting}>{submitting ? "Envoi..." : "Confirmer"}</Button>
        </div>
      </div>
    </Dialog>
  );
}

function ScenarioCard({ scenario, onSelect }: { scenario: ProjectScenarioOut; onSelect?: () => void }) {
  const item = scenario.recommendation;
  const isPreliminary = scenario.run_type === "preliminary";
  return (
    <Card
      className={cn(
        scenario.selected && "border-secondary shadow-[0_6px_18px_rgba(201,154,50,0.10)]",
        isPreliminary && "border-dashed"
      )}
    >
      <CardHeader className="flex flex-row items-center justify-between gap-3">
        <CardTitle>Scenario {scenario.scenario_code}</CardTitle>
        <span className="text-lg font-semibold text-secondary">{item.overall_score}/100</span>
      </CardHeader>
      <CardContent className="space-y-3 pt-0">
        <div className="grid grid-cols-1 gap-2 text-sm sm:grid-cols-3">
          <div className="rounded-md border border-border p-2">
            <p className="text-xs font-medium uppercase text-muted-foreground">Driver</p>
            <p className="font-medium text-foreground">{item.driver.manufacturer}</p>
            <p className="text-muted-foreground">{item.driver.reference}</p>
          </div>
          <div className="rounded-md border border-border p-2">
            <p className="text-xs font-medium uppercase text-muted-foreground">Module</p>
            <p className="font-medium text-foreground">{item.module.manufacturer}</p>
            <p className="text-muted-foreground">{item.module.reference}</p>
          </div>
          <div className="rounded-md border border-border p-2">
            <p className="text-xs font-medium uppercase text-muted-foreground">Lentille</p>
            {item.lens ? (
              <>
                <p className="font-medium text-foreground">{item.lens.manufacturer}</p>
                <p className="text-muted-foreground">{item.lens.reference}</p>
              </>
            ) : (
              <p className="text-warning">Aucune</p>
            )}
          </div>
        </div>

        {item.warnings.length > 0 && (
          <p className="text-xs text-warning">{item.warnings.length} avertissement(s)</p>
        )}
        {item.documentary_analysis && (
          <p className="text-xs text-muted-foreground">Confiance documentaire : {item.documentary_analysis.confidence}</p>
        )}

        <div className="flex flex-wrap items-center gap-2 border-t border-border pt-3">
          {isPreliminary ? (
            <Badge variant="accent">PRELIMINAIRE</Badge>
          ) : scenario.selected ? (
            <Badge variant="success">
              <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" /> SCENARIO RETENU
            </Badge>
          ) : (
            <Button size="sm" variant="outline" onClick={onSelect}>
              Selectionner ce scenario
            </Button>
          )}
          <Link to={`/resultats/${scenario.run_id}`} className="text-sm text-accent-foreground hover:underline">
            Voir le detail{!isPreliminary && " / valider"}
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}

function PreliminaryDisclaimer() {
  return (
    <div className="flex items-start gap-2 rounded-md border border-warning-bg bg-warning-bg p-3 text-sm text-warning">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
      <p>
        Ces resultats sont bases sur l'extraction automatique du CPS. Ils doivent etre confirmes apres validation des
        exigences par le consultant.
      </p>
    </div>
  );
}

function PreliminaryVsFinalDiffNote({ preliminary, final }: { preliminary: ProjectScenarioOut[]; final: ProjectScenarioOut[] }) {
  if (preliminary.length === 0 || final.length === 0) return null;

  const changes = final
    .map((finalScenario) => {
      const match = preliminary.find((p) => p.scenario_code === finalScenario.scenario_code);
      if (!match) return null;
      const driverChanged = match.recommendation.driver.id !== finalScenario.recommendation.driver.id;
      const moduleChanged = match.recommendation.module.id !== finalScenario.recommendation.module.id;
      if (!driverChanged && !moduleChanged) return null;
      return { code: finalScenario.scenario_code, before: match.recommendation, after: finalScenario.recommendation };
    })
    .filter((c): c is NonNullable<typeof c> => c !== null);

  if (changes.length === 0) return null;

  return (
    <div className="mt-4 rounded-md border border-info-bg bg-info-bg p-3 text-sm text-info">
      <p className="mb-1 font-medium">La validation des exigences a modifie la recommandation.</p>
      <ul className="space-y-1">
        {changes.map((c) => (
          <li key={c.code}>
            Scenario {c.code} — Pre-analyse : {c.before.driver.reference} + {c.before.module.reference} → Etude finale :{" "}
            {c.after.driver.reference} + {c.after.module.reference}
          </li>
        ))}
      </ul>
    </div>
  );
}

function ComparisonTable({ scenarios }: { scenarios: ProjectScenarioOut[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="min-w-[160px]">Critere</TableHead>
          {scenarios.map((s) => (
            <TableHead key={s.id} className={cn(s.selected && "bg-accent/50")}>
              Scenario {s.scenario_code}
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        <TableRow>
          <TableCell className="font-medium">Score global</TableCell>
          {scenarios.map((s) => (
            <TableCell key={s.id} className="font-semibold">{s.recommendation.overall_score}/100</TableCell>
          ))}
        </TableRow>
        <TableRow>
          <TableCell className="font-medium">Electrique (/35)</TableCell>
          {scenarios.map((s) => (
            <TableCell key={s.id}>{s.recommendation.scores.electrical}</TableCell>
          ))}
        </TableRow>
        <TableRow>
          <TableCell className="font-medium">Flux / CCT (/25)</TableCell>
          {scenarios.map((s) => (
            <TableCell key={s.id}>{s.recommendation.scores.photometric}</TableCell>
          ))}
        </TableRow>
        <TableRow>
          <TableCell className="font-medium">Mecanique / optique (/20)</TableCell>
          {scenarios.map((s) => (
            <TableCell key={s.id}>{s.recommendation.scores.mechanical}</TableCell>
          ))}
        </TableRow>
        <TableRow>
          <TableCell className="font-medium">Thermique (/10)</TableCell>
          {scenarios.map((s) => (
            <TableCell key={s.id}>{s.recommendation.scores.thermal}</TableCell>
          ))}
        </TableRow>
        <TableRow>
          <TableCell className="font-medium">Avertissements</TableCell>
          {scenarios.map((s) => (
            <TableCell key={s.id}>{s.recommendation.warnings.length}</TableCell>
          ))}
        </TableRow>
      </TableBody>
    </Table>
  );
}

export default function ProjectScenariosPage() {
  const { projectId } = useParams();
  const [project, setProject] = useState<Project | null>(null);
  const [scenarios, setScenarios] = useState<ProjectScenarioOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [dialogScenario, setDialogScenario] = useState<ProjectScenarioOut | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const load = () => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    Promise.all([getProject(Number(projectId)), listScenarios(Number(projectId))])
      .then(([p, s]) => {
        setProject(p);
        setScenarios(s);
      })
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  };

  useEffect(load, [projectId]);

  const handleDownload = async () => {
    if (!projectId) return;
    setDownloading(true);
    setDownloadError(null);
    try {
      await downloadProjectReport(Number(projectId));
    } catch (err) {
      const message = await extractBlobErrorMessage(err, "Impossible de telecharger le rapport du projet.");
      setDownloadError(message);
    } finally {
      setDownloading(false);
    }
  };

  if (loading) return <LoadingState rows={5} />;
  if (error) return <ErrorState message={error} onRetry={load} />;

  const preliminaryScenarios = scenarios.filter((s) => s.run_type === "preliminary");
  const finalScenarios = scenarios.filter((s) => s.run_type === "final");
  const selected = finalScenarios.find((s) => s.selected);

  return (
    <div>
      <Link to={`/projets/${projectId}`} className="mb-3 flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Retour au projet
      </Link>

      <PageHeader
        title="Scenarios techniques"
        description={project ? `${finalScenarios.length} scenario(s) definitif(s) pour ${project.name}` : undefined}
      />

      {scenarios.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          Aucune configuration compatible trouvee avec les exigences confirmees du CPS. Revoyez les exigences ou completez la base
          catalogue.
        </p>
      ) : (
        <>
          {preliminaryScenarios.length > 0 && (
            <div className="mb-8">
              <h2 className="mb-2 text-base font-semibold text-foreground">Resultats preliminaires</h2>
              <div className="mb-3">
                <PreliminaryDisclaimer />
              </div>
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
                {preliminaryScenarios.map((s) => (
                  <ScenarioCard key={s.id} scenario={s} />
                ))}
              </div>
            </div>
          )}

          {finalScenarios.length > 0 ? (
            <div>
              <h2 className="mb-2 text-base font-semibold text-foreground">Resultats definitifs</h2>
              <PreliminaryVsFinalDiffNote preliminary={preliminaryScenarios} final={finalScenarios} />
              <div className="mt-3 grid grid-cols-1 gap-4 lg:grid-cols-3">
                {finalScenarios.map((s) => (
                  <ScenarioCard key={s.id} scenario={s} onSelect={() => setDialogScenario(s)} />
                ))}
              </div>

              <Card className="mt-6">
                <CardHeader>
                  <CardTitle>Comparaison</CardTitle>
                </CardHeader>
                <CardContent className="pt-0">
                  <ComparisonTable scenarios={finalScenarios} />
                </CardContent>
              </Card>

              {selected && (
                <Card className="mt-6">
                  <CardHeader>
                    <CardTitle>Rapport final du projet</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2 pt-0">
                    <p className="text-sm text-muted-foreground">
                      Scenario retenu : {selected.scenario_code}. Validez d'abord la configuration depuis la page Resultats, puis
                      telechargez le rapport du projet.
                    </p>
                    <div className="flex items-center gap-3">
                      <Button variant="outline" onClick={handleDownload} disabled={downloading}>
                        {downloading ? (
                          <>
                            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> Generation...
                          </>
                        ) : (
                          <>
                            <FileDown className="h-4 w-4" aria-hidden="true" /> Telecharger le rapport du projet
                          </>
                        )}
                      </Button>
                      {downloadError && <span className="text-sm text-destructive">{downloadError}</span>}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              Etude definitive en attente : validez les exigences puis lancez l'etude depuis la page des exigences.
            </p>
          )}
        </>
      )}

      <SelectScenarioDialog
        scenario={dialogScenario}
        open={dialogScenario !== null}
        onClose={() => setDialogScenario(null)}
        onSelected={() => {
          setDialogScenario(null);
          load();
        }}
      />
    </div>
  );
}
