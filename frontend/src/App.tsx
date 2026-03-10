import { Navigate, Route, Routes } from "react-router-dom";

import LayoutShell from "./components/LayoutShell";
import LoginGate from "./components/LoginGate";
import RelationalSection from "./sections/RelationalSection";
import JsonSection from "./sections/JsonSection";
import GraphSection from "./sections/GraphSection";
import VectorSection from "./sections/VectorSection";
import DataEntrySection from "./sections/DataEntrySection";
import PrismViewSection from "./sections/PrismViewSection";
import { defaultSectionPath } from "./lib/sections";

function App() {
  return (
    <LoginGate>
      <LayoutShell>
        <Routes>
          <Route path="/relational" element={<RelationalSection />} />
          <Route path="/json" element={<JsonSection />} />
          <Route path="/graph" element={<GraphSection />} />
          <Route path="/vector" element={<VectorSection />} />
          <Route path="/data-entry" element={<DataEntrySection />} />
          <Route path="/prism" element={<PrismViewSection />} />
          <Route path="/" element={<Navigate to={defaultSectionPath} replace />} />
          <Route path="*" element={<Navigate to={defaultSectionPath} replace />} />
        </Routes>
      </LayoutShell>
    </LoginGate>
  );
}

export default App;
