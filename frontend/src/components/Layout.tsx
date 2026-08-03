import { NavLink, Outlet } from "react-router-dom";
import {
  LayoutDashboard,
  Calculator,
  GitCompare,
  Boxes,
  UploadCloud,
  History,
  Lightbulb,
} from "lucide-react";
import { cn } from "@/lib/utils";

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
      <aside className="flex w-64 shrink-0 flex-col border-r border-border bg-primary text-primary-foreground">
        <div className="flex items-center gap-2 px-5 py-5">
          <Lightbulb className="h-6 w-6" />
          <div>
            <p className="text-sm font-semibold leading-tight">Smart Lighting</p>
            <p className="text-xs text-primary-foreground/70">Aide a la decision</p>
          </div>
        </div>
        <nav className="flex flex-1 flex-col gap-1 px-3 py-2">
          {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-white/15 text-white"
                    : "text-primary-foreground/80 hover:bg-white/10 hover:text-white"
                )
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="px-5 py-4 text-xs text-primary-foreground/60">
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
