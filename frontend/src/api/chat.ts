import { get, post } from "./client";
import type {
  ApplyResponse,
  ChatRequest,
  ChatResponse,
  DetectResponse,
  ModelsResponse,
  StripResponse,
  WmParams,
} from "./types";
import { useMutation, useQuery } from "@tanstack/react-query";

export const chatApi = {
  models: () => get<ModelsResponse>("/api/models"),
  generate: (req: ChatRequest) =>
    post<ChatResponse>("/api/chat", req, { timeout: 120_000 }),
  detect: (text: string, wm_params?: WmParams) =>
    post<DetectResponse>("/api/detect", { text, wm_params }),
  strip: (text: string) => post<StripResponse>("/api/strip", { text }),
  apply: (text: string, wm_params?: WmParams) =>
    post<ApplyResponse>("/api/apply", { text, wm_params }),
};

export function useModels() {
  return useQuery({
    queryKey: ["models"],
    queryFn: chatApi.models,
    staleTime: 60_000,
  });
}

export function useGenerate() {
  return useMutation({ mutationFn: chatApi.generate });
}

export function useDetect() {
  return useMutation({
    mutationFn: ({ text, wm_params }: { text: string; wm_params?: WmParams }) =>
      chatApi.detect(text, wm_params),
  });
}

export function useStrip() {
  return useMutation({ mutationFn: chatApi.strip });
}

export function useApply() {
  return useMutation({
    mutationFn: ({ text, wm_params }: { text: string; wm_params?: WmParams }) =>
      chatApi.apply(text, wm_params),
  });
}
