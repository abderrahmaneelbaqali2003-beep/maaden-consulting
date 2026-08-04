import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
}

export function ErrorState({ title = "Une erreur est survenue", message, onRetry }: ErrorStateProps) {
  return (
    <div className="flex items-start gap-3 rounded-md border border-destructive-bg bg-destructive-bg p-4">
      <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-destructive" aria-hidden="true" />
      <div className="flex-1">
        <p className="text-sm font-semibold text-destructive">{title}</p>
        <p className="mt-1 text-sm text-destructive">{message}</p>
        {onRetry && (
          <Button variant="outline" size="sm" className="mt-3" onClick={onRetry}>
            Reessayer
          </Button>
        )}
      </div>
    </div>
  );
}
