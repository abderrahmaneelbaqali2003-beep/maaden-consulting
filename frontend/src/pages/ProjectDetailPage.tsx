import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Check, FileUp, Loader2, Upload } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { LoadingState } from "@/components/LoadingState";
import { ErrorState } from "@/components/ErrorState";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { ProjectStatusBadge } from "@/pages/ProjectsPage";
import { getProject, listCpsDocuments, uploadCpsDocument, extractRequirements } from "@/api/endpoints";
import { extractErrorMessage } from "@/api/client";
import type { CpsDocumentOut, Project, ProjectStatus } from "@/types/api";

const WORKFLOW_STEPS: { status: ProjectStatus; label: string }[] = [
  { status: "draft", label: "Projet" },
  { status: "requirements_review", label: "CPS / Exigences" },
  { status: "study_in_progress", label: "Etude" },
  { status: "scenario_selection", label: "Scenarios" },
  { status: "photometric_validation", label: "Validation" },
  { status: "validated", label: "Rapport" },
];

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

export default function ProjectDetailPage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [project, setProject] = useState<Project | null>(null);
  const [documents, setDocuments] = useState<CpsDocumentOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [extractingId, setExtractingId] = useState<number | null>(null);

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
    setUploading(true);
    setUploadError(null);
    try {
      await uploadCpsDocument(Number(projectId), file);
      load();
    } catch (err) {
      setUploadError(extractErrorMessage(err));
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleExtract = async (documentId: number) => {
    if (!projectId) return;
    setExtractingId(documentId);
    setUploadError(null);
    try {
      await extractRequirements(Number(projectId), documentId);
      navigate(`/projets/${projectId}/exigences`);
    } catch (err) {
      setUploadError(extractErrorMessage(err));
    } finally {
      setExtractingId(null);
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

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="pt-5">
            <p className="text-2xl font-semibold text-foreground">{documents.length}</p>
            <p className="text-sm text-muted-foreground">Document(s) CPS/CCTP</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5">
            <p className="text-2xl font-semibold text-foreground">{project.requirement_count}</p>
            <p className="text-sm text-muted-foreground">Exigence(s) extraite(s)</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5">
            <p className="text-2xl font-semibold text-foreground">{project.scenario_count}</p>
            <p className="text-sm text-muted-foreground">Scenario(s) etudie(s)</p>
          </CardContent>
        </Card>
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
            <Button variant="outline" onClick={() => fileInputRef.current?.click()} disabled={uploading}>
              {uploading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> Import...
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4" aria-hidden="true" /> Importer un CPS/CCTP (PDF)
                </>
              )}
            </Button>
            {uploadError && <p className="mt-2 text-sm text-destructive">{uploadError}</p>}
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
                  {doc.extraction_status === "extracted" && (
                    <Button size="sm" onClick={() => handleExtract(doc.id)} disabled={extractingId === doc.id}>
                      {extractingId === doc.id ? "Extraction..." : "Extraire les exigences"}
                    </Button>
                  )}
                  {doc.extraction_status === "insufficient_text" && (
                    <span className="text-xs text-warning">{doc.extraction_message}</span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <div className="mt-6 flex flex-wrap gap-3">
        <Link to={`/projets/${project.id}/exigences`} className="text-sm text-accent-foreground hover:underline">
          Voir les exigences ({project.requirement_count})
        </Link>
        <Link to={`/projets/${project.id}/scenarios`} className="text-sm text-accent-foreground hover:underline">
          Voir les scenarios ({project.scenario_count})
        </Link>
      </div>
    </div>
  );
}
