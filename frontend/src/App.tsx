import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Layout } from "@/components/Layout";
import DashboardPage from "@/pages/DashboardPage";
import NewCalculationPage from "@/pages/NewCalculationPage";
import ResultsPage from "@/pages/ResultsPage";
import ComparisonPage from "@/pages/ComparisonPage";
import CatalogPage from "@/pages/CatalogPage";
import ImportsPage from "@/pages/ImportsPage";
import HistoryPage from "@/pages/HistoryPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<DashboardPage />} />
          <Route path="nouveau-calcul" element={<NewCalculationPage />} />
          <Route path="resultats/:runId" element={<ResultsPage />} />
          <Route path="comparaison" element={<ComparisonPage />} />
          <Route path="catalogue" element={<CatalogPage />} />
          <Route path="imports" element={<ImportsPage />} />
          <Route path="historique" element={<HistoryPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
