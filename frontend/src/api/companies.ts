import { get, post } from "./client";
import type { CompanyResponse, CreateCompanyResponse } from "./types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

export const companiesApi = {
  list: () => get<CompanyResponse[]>("/api/companies"),
  create: (req: {
    name: string;
    issuer_id?: number;
    eth_address?: string;
    public_key_hex?: string;
    auto_generate?: boolean;
    admin_secret?: string;
  }) => post<CreateCompanyResponse>("/api/companies", req),
};

export function useCompanies() {
  return useQuery({
    queryKey: ["companies"],
    queryFn: companiesApi.list,
    staleTime: 30_000,
  });
}

export function useCreateCompany() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: companiesApi.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["companies"] }),
  });
}
