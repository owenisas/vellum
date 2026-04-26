import { useMutation, useQuery } from "@tanstack/react-query";

import { get, post } from "./client";
import type { ChatRequest, ChatResponse } from "./types";

export interface ModelEntry {
  id: string;
  name: string;
  provider: string;
}
export interface ModelsResponse {
  models: ModelEntry[];
}

export const chatApi = {
  models: () => get<ModelsResponse>("/api/models"),
  generate: (req: ChatRequest) => post<ChatResponse>("/api/chat", req),
  detect: (text: string) => post<{ watermarked: boolean; tag_count: number; valid_count: number; invalid_count: number; payloads: unknown[] }>(
    "/api/detect",
    { text },
  ),
  strip: (text: string) => post<{ text: string; stripped_count: number }>("/api/strip", { text }),
};

export const useModels = () => useQuery({ queryKey: ["models"], queryFn: chatApi.models });
export const useGenerate = () => useMutation({ mutationFn: chatApi.generate });
export const useDetect = () => useMutation({ mutationFn: chatApi.detect });
export const useStrip = () => useMutation({ mutationFn: chatApi.strip });
