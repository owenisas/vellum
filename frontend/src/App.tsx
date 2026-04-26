import { Route, Routes } from "react-router-dom";

import { ErrorBoundary } from "./components/ErrorBoundary";
import { AppShell } from "./layout/AppShell";
import { Chain } from "./pages/Chain";
import { Companies } from "./pages/Companies";
import { Dashboard } from "./pages/Dashboard";
import { DemoOverview } from "./pages/DemoOverview";
import { GenerateAndAnchor } from "./pages/GenerateAndAnchor";
import { GuidedDemo } from "./pages/GuidedDemo";
import { Landing } from "./pages/Landing";
import { Verify } from "./pages/Verify";

export default function App() {
  return (
    <ErrorBoundary>
      <AppShell>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/generate" element={<GenerateAndAnchor />} />
          <Route path="/verify" element={<Verify />} />
          <Route path="/companies" element={<Companies />} />
          <Route path="/chain" element={<Chain />} />
          <Route path="/demo" element={<GuidedDemo />} />
          <Route path="/about" element={<DemoOverview />} />
        </Routes>
      </AppShell>
    </ErrorBoundary>
  );
}
