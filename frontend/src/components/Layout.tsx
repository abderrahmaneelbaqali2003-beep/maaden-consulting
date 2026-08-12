import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { LayoutDashboard, Calculator, GitCompare, Boxes, UploadCloud, History, FolderKanban } from "lucide-react";
import { cn } from "@/lib/utils";
import { AppLogo } from "@/components/AppLogo";
import { TopHeader } from "@/components/TopHeader";

const NAV_ITEMS = [
  { to: "/", label: "Tableau de bord", icon: LayoutDashboard, end: true },
  { to: "/projets", label: "Projets", icon: FolderKanban },
  { to: "/nouveau-calcul", label: "Nouveau calcul", icon: Calculator },
  { to: "/comparaison", label: "Comparaison", icon: GitCompare },
  { to: "/catalogue", label: "Catalogue", icon: Boxes },
  { to: "/imports", label: "Imports", icon: UploadCloud },
  { to: "/historique", label: "Historique", icon: History },
];

const PAGE_TITLES: { test: (path: string) => boolean; label: string }[] = [
  { test: (p) => p === "/", label: "Tableau de bord" },
  { test: (p) => p.startsWith("/projets"), label: "Projets" },
  { test: (p) => p.startsWith("/nouveau-calcul"), label: "Nouveau calcul" },
  { test: (p) => p.startsWith("/comparaison"), label: "Comparaison" },
  { test: (p) => p.startsWith("/catalogue"), label: "Catalogue" },
  { test: (p) => p.startsWith("/imports"), label: "Imports" },
  { test: (p) => p.startsWith("/historique"), label: "Historique" },
  { test: (p) => p.startsWith("/resultats"), label: "Resultats" },
];

function getPageTitle(pathname: string) {
  return PAGE_TITLES.find(({ test }) => test(pathname))?.label ?? "MAADEN Consulting";
}

export function Layout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();
  const pageTitle = getPageTitle(location.pathname);

  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setMobileOpen(false);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  return (
    <div className="flex min-h-screen w-full bg-background">
      {mobileOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/40 lg:hidden"
          onClick={() => setMobileOpen(false)}
          aria-hidden="true"
        />
      )}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex h-screen w-[260px] flex-col bg-sidebar text-sidebar-foreground transition-transform duration-200 lg:translate-x-0",
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
        style={{ borderRight: "1px solid #35393c", boxShadow: "4px 0 18px rgba(0, 0, 0, 0.05)" }}
      >
        <div className="flex min-h-[92px] items-center justify-center px-5 py-4">
          <AppLogo />
        </div>

        <nav className="flex flex-1 flex-col gap-1 px-3 py-2" aria-label="Navigation principale">
          {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-md border-l-[3px] px-3 py-2.5 text-sm font-medium transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary focus-visible:ring-offset-2 focus-visible:ring-offset-sidebar",
                  isActive
                    ? "border-secondary bg-sidebar-active text-[#e1b652]"
                    : "border-transparent text-[#b9bec1] hover:bg-sidebar-hover hover:text-white"
                )
              }
            >
              {({ isActive }) => (
                <>
                  <Icon
                    className={cn("h-4 w-4 shrink-0", isActive ? "text-[#d4a63d]" : "text-[#9ea4a7]")}
                    aria-hidden="true"
                  />
                  {label}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-sidebar-hover px-5 py-4 text-xs leading-relaxed text-[#8b9094]">
          MAADEN Consulting
          <br />
          Version 1.0
        </div>
      </aside>

      <div className="flex min-h-screen flex-1 flex-col lg:ml-[260px]">
        <TopHeader title={pageTitle} mobileOpen={mobileOpen} onMenuClick={() => setMobileOpen((v) => !v)} />
        <main className="flex-1 overflow-x-hidden">
          <div className="mx-auto w-full max-w-[1600px] px-5 py-6 sm:px-6 lg:px-7 lg:py-7 xl:px-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
