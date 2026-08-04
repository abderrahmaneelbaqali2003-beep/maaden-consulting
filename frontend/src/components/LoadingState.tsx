import { cn } from "@/lib/utils";

interface LoadingStateProps {
  rows?: number;
  className?: string;
}

export function LoadingState({ rows = 3, className }: LoadingStateProps) {
  return (
    <div className={cn("space-y-3", className)} role="status" aria-label="Chargement">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-12 w-full animate-pulse rounded-md bg-muted" />
      ))}
    </div>
  );
}
