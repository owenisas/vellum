import { useEffect } from "react";
import { useLocation } from "react-router-dom";

const BASE = "Vellum";

export function useRouteDocumentTitle() {
  const { pathname, search } = useLocation();
  useEffect(() => {
    if (pathname === "/") {
      document.title = `${BASE} — Provenance for AI Text`;
      return;
    }
    if (pathname === "/studio") {
      const stage = new URLSearchParams(search).get("stage");
      const byStage: Record<string, string> = {
        write: "Write",
        sign: "Sign",
        anchor: "Anchor",
        prove: "Prove",
      };
      const label = (stage && byStage[stage]) || "Write";
      document.title = `Studio — ${label} — ${BASE}`;
      return;
    }
    if (pathname === "/ledger") {
      document.title = `Public ledger — ${BASE}`;
      return;
    }
    if (pathname === "/principles") {
      document.title = `Principles — ${BASE}`;
      return;
    }
    document.title = BASE;
  }, [pathname, search]);
}
