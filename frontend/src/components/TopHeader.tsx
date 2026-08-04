import { Menu, User } from "lucide-react";

interface TopHeaderProps {
  title: string;
  mobileOpen: boolean;
  onMenuClick: () => void;
}

export function TopHeader({ title, mobileOpen, onMenuClick }: TopHeaderProps) {
  return (
    <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-border bg-card px-4 sm:px-6 lg:px-7">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onMenuClick}
          aria-label="Ouvrir le menu de navigation"
          aria-expanded={mobileOpen}
          className="inline-flex h-9 w-9 items-center justify-center rounded-md text-foreground transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring lg:hidden"
        >
          <Menu className="h-5 w-5" aria-hidden="true" />
        </button>
        <h2 className="text-sm font-semibold text-foreground sm:text-base">{title}</h2>
      </div>

      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <User className="h-4 w-4" aria-hidden="true" />
        <span className="hidden sm:inline">Espace consultant</span>
      </div>
    </header>
  );
}
