import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Listings from "./pages/Listings";
import ListingDetail from "./pages/ListingDetail";
import Sources from "./pages/Sources";
import ScrapeRuns from "./pages/ScrapeRuns";
import AISettings from "./pages/AISettings";
import AIResults from "./pages/AIResults";
import AIResultDetail from "./pages/AIResultDetail";
import Errors from "./pages/Errors";
import Dedup from "./pages/Dedup";
import NotFound from "./pages/NotFound";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="listings" element={<Listings />} />
        <Route path="listings/:id" element={<ListingDetail />} />
        <Route path="sources" element={<Sources />} />
        <Route path="scrape-runs" element={<ScrapeRuns />} />
        <Route path="ai/settings" element={<AISettings />} />
        <Route path="ai/results" element={<AIResults />} />
        <Route path="ai/results/:id" element={<AIResultDetail />} />
        <Route path="errors" element={<Errors />} />
        <Route path="dedup" element={<Dedup />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
