import { get, post } from "./client";
import type { DemoScenarioResponse } from "./types";
import { useMutation, useQuery } from "@tanstack/react-query";

export const demoApi = {
  scenario: () => get<DemoScenarioResponse>("/api/demo/scenario"),
  reset: () => post<{ status: string; cleared: Record<string, number> }>(
    "/api/demo/reset",
    {},
  ),
};

export function useDemoScenario() {
  return useQuery({
    queryKey: ["demo", "scenario"],
    queryFn: demoApi.scenario,
    enabled: false, // user-triggered
  });
}

export function useDemoReset() {
  return useMutation({ mutationFn: demoApi.reset });
}
