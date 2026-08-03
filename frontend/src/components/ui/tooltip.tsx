import * as React from "react";
import { Info } from "lucide-react";
import { cn } from "@/lib/utils";

export function InfoTooltip({ text, className }: { text: string; className?: string }) {
  const [open, setOpen] = React.useState(false);

  return (
    <span className={cn("relative inline-flex", className)}>
      <button
        type="button"
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        className="inline-flex text-muted-foreground hover:text-secondary"
        aria-label="Aide"
      >
        <Info className="h-3.5 w-3.5" />
      </button>
      {open && (
        <span className="absolute bottom-full left-1/2 z-50 mb-2 w-56 -translate-x-1/2 rounded-md border border-border bg-card p-2 text-xs text-foreground shadow-md">
          {text}
        </span>
      )}
    </span>
  );
}
