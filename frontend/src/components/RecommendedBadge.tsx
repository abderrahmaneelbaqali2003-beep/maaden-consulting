import { Star } from "lucide-react";
import { cn } from "@/lib/utils";

export function RecommendedBadge({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border border-[#d8b766] bg-accent px-2.5 py-0.5 text-xs font-semibold text-accent-foreground",
        className
      )}
    >
      <Star className="h-3 w-3 fill-current" aria-hidden="true" />
      Solution recommandee
    </span>
  );
}
