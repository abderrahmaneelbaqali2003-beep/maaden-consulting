import { useEffect, useState } from "react";
import { Search, Ban } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { listDrivers, deleteDriver } from "@/api/endpoints";
import { extractErrorMessage } from "@/api/client";
import type { Driver } from "@/types/api";

export function DriverTable() {
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    listDrivers({ search: search || undefined, page, page_size: 10 })
      .then((res) => {
        setDrivers(res.items);
        setTotalPages(res.total_pages || 1);
        setTotal(res.total);
      })
      .catch((err) => setError(extractErrorMessage(err)));
  };

  useEffect(load, [search, page]);

  const handleDisable = async (id: number) => {
    if (!confirm("Desactiver ce driver ? Il ne sera plus propose dans les recommandations.")) return;
    await deleteDriver(id);
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
        <span className="text-sm text-muted-foreground">{total} driver(s)</span>
      </div>

      {error && <p className="mb-2 text-sm text-destructive">{error}</p>}

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Reference</TableHead>
            <TableHead>Fabricant</TableHead>
            <TableHead>Tension (V)</TableHead>
            <TableHead>Puissance max (W)</TableHead>
            <TableHead>Protocoles</TableHead>
            <TableHead>Qualite</TableHead>
            <TableHead />
          </TableRow>
        </TableHeader>
        <TableBody>
          {drivers.map((d) => (
            <TableRow key={d.id}>
              <TableCell className="font-medium">{d.reference}</TableCell>
              <TableCell>{d.manufacturer.name}</TableCell>
              <TableCell>
                {d.output_voltage_min_v}-{d.output_voltage_max_v}
              </TableCell>
              <TableCell>{d.output_power_max_w}</TableCell>
              <TableCell className="space-x-1">
                {d.dali_2 && <Badge variant="info">DALI-2</Badge>}
                {d.d4i && <Badge variant="info">D4i</Badge>}
                {d.dimming_0_10v && <Badge variant="info">0-10V</Badge>}
                {d.dimming_1_10v && <Badge variant="info">1-10V</Badge>}
              </TableCell>
              <TableCell>
                {d.needs_manual_validation ? (
                  <Badge variant="warning">A valider</Badge>
                ) : (
                  <Badge variant="success">OK</Badge>
                )}
              </TableCell>
              <TableCell>
                <Button variant="ghost" size="sm" onClick={() => handleDisable(d.id)} title="Desactiver">
                  <Ban className="h-4 w-4 text-destructive" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
          {drivers.length === 0 && (
            <TableRow>
              <TableCell colSpan={7} className="text-center text-sm text-muted-foreground">
                Aucun driver trouve.
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
