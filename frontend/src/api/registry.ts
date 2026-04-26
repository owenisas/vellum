import { useMutation } from "@tanstack/react-query";

import { post } from "./client";
import type { AnchorRequest, AnchorResponse, VerifyResponse } from "./types";

export const registryApi = {
  anchor: (req: AnchorRequest) => post<AnchorResponse>("/api/anchor", req),
  verify: (text: string) => post<VerifyResponse>("/api/verify", { text }),
};

export const useAnchor = () => useMutation({ mutationFn: registryApi.anchor });
export const useVerify = () => useMutation({ mutationFn: registryApi.verify });
