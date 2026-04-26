import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { AnimatePresence } from "framer-motion";

import { ErrorBoundary } from "./components/ErrorBoundary";
import { useRouteDocumentTitle } from "./hooks/useRouteDocumentTitle";
import { AppShell } from "./layout/AppShell";
import { Cover } from "./pages/Cover";
import { Studio } from "./pages/Studio";
import { Ledger } from "./pages/Ledger";
import { Principles } from "./pages/Principles";

export default function App() {
  useRouteDocumentTitle();
  const location = useLocation();
  return (
    <ErrorBoundary>
      <AppShell>
        <AnimatePresence mode="wait">
          <Routes location={location} key={location.pathname}>
            <Route path="/" element={<Cover />} />
            <Route path="/studio" element={<Studio />} />
            <Route path="/ledger" element={<Ledger />} />
            <Route path="/principles" element={<Principles />} />

            {/* Legacy redirects */}
            <Route path="/demo" element={<Navigate replace to="/studio" />} />
            <Route path="/generate" element={<Navigate replace to="/studio?stage=write" />} />
            <Route path="/verify" element={<Navigate replace to="/studio?stage=prove" />} />
            <Route path="/companies" element={<Navigate replace to="/ledger?tab=issuers" />} />
            <Route path="/chain" element={<Navigate replace to="/ledger" />} />
            <Route path="/dashboard" element={<Navigate replace to="/ledger" />} />
            <Route path="/about" element={<Navigate replace to="/principles" />} />

            <Route path="*" element={<Navigate replace to="/" />} />
          </Routes>
        </AnimatePresence>
      </AppShell>
    </ErrorBoundary>
  );
}
