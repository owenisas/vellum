import { BrowserRouter, Route, Routes } from "react-router";
import { AppShell } from "./layout/AppShell";
import { Landing } from "./pages/Landing";
import { Dashboard } from "./pages/Dashboard";
import { GenerateAndAnchor } from "./pages/GenerateAndAnchor";
import { Verify } from "./pages/Verify";
import { Companies } from "./pages/Companies";
import { Chain } from "./pages/Chain";
import { GuidedDemo } from "./pages/GuidedDemo";
import { DemoOverview } from "./pages/DemoOverview";
import { AuthGuard } from "./auth/AuthGuard";
import { ErrorBoundary } from "./components/ErrorBoundary";

export function App() {
  return (
    <BrowserRouter>
      <ErrorBoundary>
        <Routes>
          <Route element={<AppShell />}>
            <Route index element={<Landing />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route
              path="generate"
              element={
                <AuthGuard>
                  <GenerateAndAnchor />
                </AuthGuard>
              }
            />
            <Route path="verify" element={<Verify />} />
            <Route
              path="companies"
              element={
                <AuthGuard>
                  <Companies />
                </AuthGuard>
              }
            />
            <Route path="chain" element={<Chain />} />
            <Route
              path="demo"
              element={
                <AuthGuard>
                  <GuidedDemo />
                </AuthGuard>
              }
            />
            <Route path="about" element={<DemoOverview />} />
          </Route>
        </Routes>
      </ErrorBoundary>
    </BrowserRouter>
  );
}
