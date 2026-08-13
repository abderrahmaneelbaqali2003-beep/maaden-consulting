import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { AlertTriangle, ArrowLeft, Check, CheckCircle2, FileUp, Loader2, Sparkles, Upload } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { LoadingState } from "@/components/LoadingState";
import { ErrorState } from "@/components/ErrorState";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { ProjectStatusBadge } from "@/pages/ProjectsPage";
import { MissingFieldsForm } from "@/features/project/MissingFieldsForm";
import { getProject, listCpsDocuments, analyzeCpsDocument } from "@/api/endpoints";
import { extractErrorMessage } from "@/api/client";
import type { CpsAnalysisResponse, CpsDocumentOut, Project, ProjectStatus } from "@/types/api";

const WORKFLOW_STEPS: { status: ProjectStatus; label: string }[] = [
  { status: "draft", label: "Projet" },
  { status: "requirements_review", label: "CPS" },
  { status: "preliminary_analysis", label: "Pre-analyse" },
  { status: "study_in_progress", label: "Etude" },
  { status: "scenario_selection", label: "Scenarios" },
  { status: "photometric_validation", label: "Validation" },
  { status: "validated", label: "Rapport" },
];

const ANALYSIS_STEPS = ["Upload du CPS", "Lecture du document", "Extraction des exigences", "Analyse des donnees", "Recherche des configurations"];

function WorkflowProgress({ status }: { status: ProjectStatus }) {
  const currentIndex = Math.max(
    0,
    WORKFLOW_STEPS.findIndex((s) => s.status === status)
  );
  return (
    <ol className="mb-6 flex flex-wrap items-center gap-2 text-xs sm:text-sm">
      {WORKFLOW_STEPS.map((step, i) => (
        <li key={step.status} className="flex items-center gap-2">
          <span
            className={cn(
              "flex h-6 w-6 items-center justify-center rounded-full border text-xs font-semibold",
              i < currentIndex && "border-success bg-success-bg text-success",
              i === currentIndex && "border-secondary bg-accent text-accent-foreground",
              i > currentIndex && "border-border text-muted-foreground"
            )}
          >
            {i < currentIndex ? <Check className="h-3.5 w-3.5" aria-hidden="true" /> : i + 1}
          </span>
          <span className={cn(i === currentIndex ? "font-medium text-foreground" : "text-muted-foreground")}>{step.label}</span>
          {i < WORKFLOW_STEPS.length - 1 && <span className="mx-1 h-px w-4 bg-border sm:w-8" aria-hidden="true" />}
        </li>
      ))}
    </ol>
  );
}

function AnalysisResultCard({ projectId, result, onRerun }: { projectId: number; result: CpsAnalysisResponse; onRerun: (r: CpsAnalysisResponse) => void }) {
  const { analysis, scenarios } = result;

  if (analysis.can_run_preliminary_study) {
    return (
      <Card className="mt-4 border-success">
        <CardContent className="space-y-3 pt-5">
          <p className="flex items-center gap-2 text-sm font-semibold text-success">
            <CheckCircle2 className="h-4 w-4" aria-hidden="true" /> CPS analyse avec succes
          </p>
          <p className="text-sm text-muted-foreground">
            {analysis.requirements_detected_count} exigence(s) detectee(s) — {analysis.requirements_confirmed_count} deja exploitables,{" "}
            {analysis.requirements_to_review_count} a verifier.
          </p>
          {scenarios.length > 0 ? (
            <>
              <p className="flex items-center gap-2 text-sm font-medium text-foreground">
                <Sparkles className="h-4 w-4 text-secondary" aria-hidden="true" />
                {scenarios.length} configuration(s) preliminaire(s) trouvee(s)
              </p>
              <Badge variant="accent">PRELIMINAIRE</Badge>
              <p className="text-xs text-muted-foreground">
                Ces resultats sont bases sur l'extraction automatique du CPS. Ils doivent etre confirmes apres validation
                des exigences par le consultant.
              </p>
              <Link to={`/projets/${projectId}/scenarios`} className="text-sm text-accent-foreground hover:underline">
                Voir les configurations preliminaires
              </Link>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">
              Aucune configuration compatible trouvee avec les exigences actuellement extraites.
            </p>
          )}
          <div>
            <Link to={`/projets/${projectId}/exigences`} className="text-sm text-accent-foreground hover:underline">
              Verifier / confirmer les exigences
            </Link>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="mt-4 border-warning">
      <CardContent className="space-y-3 pt-5">
        <p className="flex items-center gap-2 text-sm font-semibold text-warning">
          <AlertTriangle className="h-4 w-4" aria-hidden="true" /> CPS analyse
        </p>
        <p className="text-sm text-muted-foreground">{analysis.requirements_detected_count} exigence(s) detectee(s).</p>
        <p className="text-sm text-foreground">
          Etude impossible pour le moment : {analysis.missing_fields.length} donnee(s) obligatoire(s) manque(nt).
        </p>
        <ul className="space-y-1">
          {analysis.missing_fields.map((f) => (
            <li key={f.field} className="flex items-center gap-1.5 text-sm text-warning">
              <AlertTriangle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" /> {f.label}
            </li>
          ))}
        </ul>
        <MissingFieldsForm projectId={projectId} missingFields={analysis.missing_fields} onCompleted={onRerun} />
      </CardContent>
    </Card>
  );
}

export default function ProjectDetailPage() {
  const { projectId } = useParams();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [project, setProject] = useState<Project | null>(null);
  const [documents, setDocuments] = useState<CpsDocumentOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);
  const [analysisResult, setAnalysisResult] = useState<CpsAnalysisResponse | null>(null);

  const load = () => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    Promise.all([getProject(Number(projectId)), listCpsDocuments(Number(projectId))])
      .then(([p, docs]) => {
        setProject(p);
        setDocuments(docs);
      })
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  };

  useEffect(load, [projectId]);

  const handleFileSelected = async (file: File) => {
    if (!projectId) return;
    setAnalyzing(true);
    setAnalyzeError(null);
    setAnalysisResult(null);
    try {
      const result = await analyzeCpsDocument(Number(projectId), file);
      setAnalysisResult(result);
      load();
    } catch (err) {
      setAnalyzeError(extractErrorMessage(err));
    } finally {
      setAnalyzing(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  if (loading) return <LoadingState rows={5} />;
  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!project) return null;

  return (
    <div>
      <Link to="/projets" className="mb-3 flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Retour aux projets
      </Link>

      <PageHeader title={project.name} description={project.reference ?? undefined} />

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <ProjectStatusBadge status={project.status} />
        {project.client_name && <span className="text-sm text-muted-foreground">Client : {project.client_name}</span>}
      </div>

      <WorkflowProgress status={project.status} />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
        <Card>
          <CardContent className="pt-5">
            <p className="text-2xl font-semibold text-foreground">{documents.length}</p>
            <p className="text-sm text-muted-foreground">Document(s) CPS/CCTP</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5">
            <p className="text-2xl font-semibold text-foreground">{project.requirement_count}</p>
            <p className="text-sm text-muted-foreground">
              Exigence(s) — {project.requirements_confirmed_count} confirmee(s), {project.requirements_to_review_count} a traiter
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5">
            <p className="text-2xl font-semibold text-foreground">{project.preliminary_scenario_count}</p>
            <p className="text-sm text-muted-foreground">Scenario(s) preliminaire(s)</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5">
            <p className="text-2xl font-semibold text-foreground">{project.scenario_count}</p>
            <p className="text-sm text-muted-foreground">Scenario(s) de l'etude definitive</p>
          </CardContent>
        </Card>
      </div>

      <div className="mt-8 mb-3">
        <h2 className="text-base font-semibold text-foreground">Definir les exigences du projet</h2>
        <p className="text-sm text-muted-foreground">Deux methodes disponibles, toutes convergent vers la meme etude.</p>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Saisie manuelle</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <p className="mb-3 text-sm text-muted-foreground">Renseignez chaque exigence technique vous-meme, champ par champ.</p>
            <Link to={`/projets/${project.id}/exigences`} className="text-sm text-accent-foreground hover:underline">
              Formulaire technique
            </Link>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>CPS / CCTP</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <p className="text-sm text-muted-foreground">Importez le cahier des charges : les exigences sont extraites automatiquement (ci-dessous).</p>
          </CardContent>
        </Card>
      </div>

      <div className="mt-6 rounded-md border border-border bg-accent/40 p-4 text-sm">
        <p className="font-medium text-foreground">Vous preferez decrire le besoin avec vos propres mots ?</p>
        <p className="mt-1 text-muted-foreground">
          L'assistant IA (independant de ce projet) transforme un texte libre en configurations compatibles a partir du
          catalogue.
        </p>
        <Link to="/assistant-ia" className="mt-2 inline-block text-accent-foreground hover:underline">
          Ouvrir l'assistant IA
        </Link>
      </div>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle>CPS / CCTP</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 pt-0">
          <div>
            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleFileSelected(file);
              }}
            />
            <Button variant="outline" onClick={() => fileInputRef.current?.click()} disabled={analyzing}>
              {analyzing ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> Analyse en cours...
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4" aria-hidden="true" /> Importer et analyser le CPS
                </>
              )}
            </Button>
            {analyzing && (
              <ul className="mt-3 space-y-1 text-sm text-muted-foreground">
                {ANALYSIS_STEPS.map((step) => (
                  <li key={step} className="flex items-center gap-2">
                    <Loader2 className="h-3.5 w-3.5 animate-spin text-secondary" aria-hidden="true" /> {step}
                  </li>
                ))}
              </ul>
            )}
            {analyzeError && <p className="mt-2 text-sm text-destructive">{analyzeError}</p>}
          </div>

          {documents.length === 0 ? (
            <p className="text-sm text-muted-foreground">Aucun document importe pour ce projet.</p>
          ) : (
            <ul className="space-y-2">
              {documents.map((doc) => (
                <li key={doc.id} className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-border p-3">
                  <div className="flex items-center gap-2">
                    <FileUp className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                    <div>
                      <p className="text-sm font-medium text-foreground">{doc.original_filename}</p>
                      <p className="text-xs text-muted-foreground">
                        {doc.page_count} page(s) —{" "}
                        {doc.extraction_status === "extracted" && "Texte extrait"}
                        {doc.extraction_status === "insufficient_text" && "Document probablement scanne"}
                        {doc.extraction_status === "failed" && "Extraction impossible"}
                        {doc.extraction_status === "pending" && "En attente"}
                      </p>
                    </div>
                  </div>
                  {doc.extraction_status === "insufficient_text" && (
                    <span className="text-xs text-warning">{doc.extraction_message}</span>
                  )}
                </li>
              ))}
            </ul>
          )}

          {analysisResult && (
            <AnalysisResultCard
              projectId={Number(projectId)}
              result={analysisResult}
              onRerun={(result) => {
                setAnalysisResult(result);
                load();
              }}
            />
          )}
        </CardContent>
      </Card>

      <div className="mt-6 flex flex-wrap gap-3">
        <Link to={`/projets/${project.id}/exigences`} className="text-sm text-accent-foreground hover:underline">
          Voir les exigences ({project.requirement_count})
        </Link>
        <Link to={`/projets/${project.id}/scenarios`} className="text-sm text-accent-foreground hover:underline">
          Voir les scenarios
        </Link>
      </div>
    </div>
  );
}
