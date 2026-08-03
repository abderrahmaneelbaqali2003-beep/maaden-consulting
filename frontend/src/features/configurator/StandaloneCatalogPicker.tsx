import { useEffect, useState } from "react";
import { Search, Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { extractErrorMessage } from "@/api/client";
import { listDrivers, listLenses } from "@/api/endpoints";
import type { ComponentRef, Driver, Lens } from "@/types/api";

/** Selecteur simple (recherche + pagination, sans statut de compatibilite) utilise quand un
 * driver ou une lentille est impose(e) SANS module de reference (mode semi-automatique). */
export function StandaloneCatalogPicker({
  entityType,
  selectedId,
  onSelect,
}: {
  entityType: "driver" | "lens";
  selectedId: number | null;
  onSelect: (item: ComponentRef) => void;
}) {
  const [items, setItems] = useState<(Driver | Lens)[]>([]);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    const request = entityType === "driver" ? listDrivers({ search, page, page_size: 8 }) : listLenses({ search, page, page_size: 8 });
    request
      .then((res) => {
        setItems(res.items);
        setTotalPages(res.total_pages || 1);
      })
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [entityType, search, page]);

  useEffect(() => setPage(1), [search]);

  return (
    <div>
      <div className="relative mb-3 max-w-xs">
        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
        <Input placeholder="Rechercher par reference..." className="pl-8" value={search} onChange={(e) => setSearch(e.target.value)} />
      </div>

      {error && <p className="mb-2 text-sm text-destructive">{error}</p>}

      {loading ? (
        <div className="flex items-center justify-center gap-2 py-6 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Chargement...
        </div>
      ) : items.length === 0 ? (
        <p className="py-6 text-center text-sm text-muted-foreground">Aucun resultat.</p>
      ) : (
        <ul className="divide-y divide-border rounded-md border border-border">
          {items.map((item) => (
            <li key={item.id} className={`flex items-center justify-between gap-3 p-3 ${item.id === selectedId ? "bg-accent" : ""}`}>
              <p className="text-sm font-medium">
                {item.manufacturer.name} {item.reference}
              </p>
              <Button
                type="button"
                size="sm"
                variant={item.id === selectedId ? "default" : "outline"}
                onClick={() => onSelect({ id: item.id, manufacturer: item.manufacturer.name, reference: item.reference })}
              >
                {item.id === selectedId ? "Selectionne" : "Choisir"}
              </Button>
            </li>
          ))}
        </ul>
      )}

      {totalPages > 1 && (
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
      )}
    </div>
  );
}
