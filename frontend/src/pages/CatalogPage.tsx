import { Link } from "react-router-dom";
import { UploadCloud } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { buttonVariants } from "@/components/ui/button";
import { DriverTable } from "@/features/catalog/DriverTable";
import { ModuleTable } from "@/features/catalog/ModuleTable";
import { LensTable } from "@/features/catalog/LensTable";

export default function CatalogPage() {
  return (
    <div>
      <div className="mb-6 flex items-start justify-between">
        <PageHeader
          title="Catalogue"
          description="Drivers, modules LED et lentilles disponibles pour les recommandations."
        />
        <Link to="/imports" className={buttonVariants({ variant: "outline" })}>
          <UploadCloud className="h-4 w-4" /> Importer des references
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
