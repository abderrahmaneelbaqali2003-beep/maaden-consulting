import { NavLink, Outlet } from "react-router-dom";
import {
  LayoutDashboard,
  Calculator,
  GitCompare,
  Boxes,
  UploadCloud,
  History,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Logo } from "@/components/Logo";

const NAV_ITEMS = [
  { to: "/", label: "Tableau de bord", icon: LayoutDashboard, end: true },
  { to: "/nouveau-calcul", label: "Nouveau calcul", icon: Calculator },
  { to: "/comparaison", label: "Comparaison", icon: GitCompare },
  { to: "/catalogue", label: "Catalogue", icon: Boxes },
  { to: "/imports", label: "Imports", icon: UploadCloud },
  { to: "/historique", label: "Historique", icon: History },
];

export function Layout() {
  return (
    <div className="flex min-h-screen w-full bg-background">
      <aside className="flex w-64 shrink-0 flex-col bg-sidebar text-sidebar-foreground">
        <div className="flex items-center gap-2.5 border-b border-sidebar-border px-5 py-5">
          <Logo showWordmark theme="dark" />
        </div>
        <nav className="flex flex-1 flex-col gap-1 px-3 py-4">
          {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-md border-l-2 px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "border-primary bg-primary/12 text-primary"
                    : "border-transparent text-sidebar-muted-foreground hover:bg-white/5 hover:text-sidebar-foreground"
                )
              }
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-sidebar-border px-5 py-4 text-xs text-sidebar-muted-foreground">
          Outil de consulting eclairage public — V1
        </div>
      </aside>
      <main className="flex-1 overflow-x-hidden">
        <div className="mx-auto max-w-7xl p-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
