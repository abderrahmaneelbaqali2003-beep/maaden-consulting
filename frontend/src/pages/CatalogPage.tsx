import { Link } from "react-router-dom";
import { UploadCloud } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { DriverTable } from "@/features/catalog/DriverTable";
import { ModuleTable } from "@/features/catalog/ModuleTable";
import { LensTable } from "@/features/catalog/LensTable";

export default function CatalogPage() {
  return (
    <div>
      <div className="mb-6 flex flex-col items-start justify-between gap-3 sm:flex-row sm:items-center">
        <PageHeader
          title="Catalogue"
          description="Drivers, modules LED et lentilles disponibles pour les recommandations."
        />
        <Link to="/imports" className={cn(buttonVariants({ variant: "outline" }), "shrink-0")}>
          <UploadCloud className="h-4 w-4" aria-hidden="true" /> Importer des references
        </Link>
      </div>

      <Tabs defaultValue="drivers">
        <TabsList>
          <TabsTrigger value="drivers">Drivers</TabsTrigger>
          <TabsTrigger value="modules">Modules LED</TabsTrigger>
          <TabsTrigger value="lenses">Lentilles</TabsTrigger>
        </TabsList>
        <TabsContent value="drivers" className="mt-4">
          <DriverTable />
        </TabsContent>
        <TabsContent value="modules" className="mt-4">
          <ModuleTable />
        </TabsContent>
        <TabsContent value="lenses" className="mt-4">
          <LensTable />
        </TabsContent>
      </Tabs>
    </div>
  );
}
