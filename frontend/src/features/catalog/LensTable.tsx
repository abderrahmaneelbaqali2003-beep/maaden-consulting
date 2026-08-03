import { useEffect, useState } from "react";
import { Search, Ban } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { listLenses, deleteLens } from "@/api/endpoints";
import { extractErrorMessage } from "@/api/client";
import type { Lens } from "@/types/api";

export function LensTable() {
  const [lenses, setLenses] = useState<Lens[]>([]);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    listLenses({ search: search || undefined, page, page_size: 10 })
      .then((res) => {
        setLenses(res.items);
        setTotalPages(res.total_pages || 1);
        setTotal(res.total);
      })
      .catch((err) => setError(extractErrorMessage(err)));
  };

  useEffect(load, [search, page]);

  const handleDisable = async (id: number) => {
    if (!confirm("Desactiver cette lentille ? Elle ne sera plus proposee dans les recommandations.")) return;
    await deleteLens(id);
    load();
  };

  return (
    <div>
      <div className="mb-3 flex items-center gap-2">
        <div className="relative max-w-sm flex-1">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Rechercher par reference, famille..."
            className="pl-8"
            value={search}
            onChange={(e) => {
              setPage(1);
              setSearch(e.target.value);
            }}
          />
        </div>
        <span className="text-sm text-muted-foreground">{total} lentille(s)</span>
      </div>

      {error && <p className="mb-2 text-sm text-destructive">{error}</p>}

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Reference</TableHead>
            <TableHead>Fabricant</TableHead>
            <TableHead>Packages compatibles</TableHead>
            <TableHead>Distribution</TableHead>
            <TableHead>Fichier IES/LDT</TableHead>
            <TableHead>Qualite</TableHead>
            <TableHead />
          </TableRow>
        </TableHeader>
        <TableBody>
          {lenses.map((l) => (
            <TableRow key={l.id}>
              <TableCell className="font-medium">{l.reference}</TableCell>
              <TableCell>{l.manufacturer.name}</TableCell>
              <TableCell>{l.compatible_led_package ?? "—"}</TableCell>
              <TableCell>{l.iesna_distribution_type ?? "—"}</TableCell>
              <TableCell>
                {l.ies_file_available || l.ldt_file_available ? (
                  <Badge variant="success">Disponible</Badge>
                ) : (
                  <Badge variant="destructive">Absent</Badge>
                )}
              </TableCell>
              <TableCell>
                {l.needs_manual_validation ? (
                  <Badge variant="warning">A valider</Badge>
                ) : (
                  <Badge variant="success">OK</Badge>
                )}
              </TableCell>
              <TableCell>
                <Button variant="ghost" size="sm" onClick={() => handleDisable(l.id)} title="Desactiver">
                  <Ban className="h-4 w-4 text-destructive" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
          {lenses.length === 0 && (
            <TableRow>
              <TableCell colSpan={7} className="text-center text-sm text-muted-foreground">
                Aucune lentille trouvee.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

      <div className="mt-3 flex items-center justify-between text-sm">
        <span className="text-muted-foreground">
          Page {page} / {totalPages}
        </span>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            Precedent
          </Button>
          <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
            Suivant
          </Button>
        </div>
      </div>
    </div>
  );
}
