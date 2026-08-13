import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { FolderKanban, Plus } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { LoadingState } from "@/components/LoadingState";
import { ErrorState } from "@/components/ErrorState";
import { EmptyState } from "@/components/EmptyState";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog } from "@/components/ui/dialog";
import { createProject, listProjects } from "@/api/endpoints";
import { extractErrorMessage } from "@/api/client";
import type { Project, ProjectStatus } from "@/types/api";

const STATUS_CONFIG: Record<ProjectStatus, { label: string; variant: "success" | "warning" | "info" | "accent" | "default" }> = {
  draft: { label: "Brouillon", variant: "default" },
  requirements_review: { label: "Exigences en revue", variant: "info" },
  preliminary_analysis: { label: "Pre-analyse CPS", variant: "info" },
  study_in_progress: { label: "Etude en cours", variant: "info" },
  scenario_selection: { label: "Selection du scenario", variant: "accent" },
  photometric_validation: { label: "Validation photometrique", variant: "warning" },
  validated: { label: "Valide", variant: "success" },
  archived: { label: "Archive", variant: "default" },
};

export function ProjectStatusBadge({ status }: { status: ProjectStatus }) {
  const config = STATUS_CONFIG[status] ?? { label: status, variant: "default" as const };
  return <Badge variant={config.variant}>{config.label}</Badge>;
}

function NewProjectDialog({ open, onClose, onCreated }: { open: boolean; onClose: () => void; onCreated: (p: Project) => void }) {
  const [name, setName] = useState("");
  const [clientName, setClientName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (open) {
      setName("");
      setClientName("");
      setError(null);
      setSubmitting(false);
    }
  }, [open]);

  const handleCreate = async () => {
    if (!name.trim()) {
      setError("Le nom du projet est obligatoire.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const project = await createProject({ name: name.trim(), client_name: clientName.trim() || null });
      onCreated(project);
    } catch (err) {
      setError(extractErrorMessage(err));
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} title="Nouveau projet">
      <div className="space-y-4">
        <div>
          <Label htmlFor="project_name">Nom du projet *</Label>
          <Input id="project_name" value={name} onChange={(e) => setName(e.target.value)} className="mt-1" placeholder="Ex: BHNS Rabat-Sale-Temara" />
        </div>
        <div>
          <Label htmlFor="project_client">Client</Label>
          <Input id="project_client" value={clientName} onChange={(e) => setClientName(e.target.value)} className="mt-1" placeholder="Optionnel" />
        </div>
        {error && <p className="text-sm text-destructive">{error}</p>}
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" onClick={onClose} disabled={submitting}>
            Annuler
          </Button>
          <Button onClick={handleCreate} disabled={submitting}>
            {submitting ? "Creation..." : "Creer le projet"}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}

export default function ProjectsPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<Project[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);

  const load = () => {
    setLoading(true);
    setError(null);
    listProjects()
      .then((res) => setItems(res.items))
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  return (
    <div>
      <PageHeader title="Projets" description="Projets de consulting, du CPS/CCTP au rapport final." />

      <div className="mb-4 flex justify-end">
        <Button onClick={() => setDialogOpen(true)}>
          <Plus className="h-4 w-4" aria-hidden="true" /> Nouveau projet
        </Button>
      </div>

      {loading && <LoadingState rows={5} />}
      {!loading && error && <ErrorState message={error} onRetry={load} />}

      {!loading && !error && items.length === 0 && (
        <EmptyState icon={FolderKanban} title="Aucun projet pour le moment." description="Creez un projet pour importer un CPS/CCTP et lancer une etude." />
      )}

      {!loading && !error && items.length > 0 && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Reference</TableHead>
              <TableHead>Nom</TableHead>
              <TableHead>Client</TableHead>
              <TableHead>Statut</TableHead>
              <TableHead>Scenarios</TableHead>
              <TableHead>Configuration retenue</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((project) => (
              <TableRow key={project.id}>
                <TableCell className="text-sm text-muted-foreground">{project.reference ?? "—"}</TableCell>
                <TableCell className="font-medium text-foreground">{project.name}</TableCell>
                <TableCell className="text-sm">{project.client_name ?? "—"}</TableCell>
                <TableCell>
                  <ProjectStatusBadge status={project.status} />
                </TableCell>
                <TableCell className="text-sm">{project.scenario_count}</TableCell>
                <TableCell className="text-sm">{project.selected_scenario_code ?? "—"}</TableCell>
                <TableCell>
                  <Link to={`/projets/${project.id}`} className="text-sm text-accent-foreground hover:underline">
                    Ouvrir
                  </Link>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <NewProjectDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onCreated={(project) => {
          setDialogOpen(false);
          navigate(`/projets/${project.id}`);
        }}
      />
    </div>
  );
}
