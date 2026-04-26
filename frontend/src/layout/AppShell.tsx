import { type ReactNode, useEffect } from "react";
import { useLocation } from "react-router-dom";

import { Masthead } from "./Masthead";
import { Footer } from "./Footer";
import { Cursor } from "../components/ui/Cursor";
import { SmoothScroll } from "../components/ui/SmoothScroll";

const SURFACE_BY_ROUTE: Record<string, "ink" | "paper"> = {
  "/": "ink",
  "/studio": "paper",
  "/ledger": "paper",
  "/principles": "ink",
};

function surfaceFor(pathname: string): "ink" | "paper" {
  for (const [prefix, surface] of Object.entries(SURFACE_BY_ROUTE)) {
    if (prefix === "/" ? pathname === "/" : pathname.startsWith(prefix)) return surface;
  }
  return "ink";
}

export function AppShell({ children }: { children: ReactNode }) {
  const { pathname } = useLocation();
  const surface = surfaceFor(pathname);
  useEffect(() => {
    document.documentElement.dataset.surface = surface;
  }, [surface]);
  return (
    <>
      <SmoothScroll />
      <Cursor />
      <Masthead />
      <main data-page>{children}</main>
      <Footer />
    </>
  );
}
