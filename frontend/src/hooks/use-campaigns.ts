"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { PaginatedResponse, SuccessResponse } from "@/types/api";

export interface CampaignItem {
  id: string;
  name: string;
  description: string | null;
  status: string;
  message_type: string;
  template_name: string | null;
  audience_type: string;
  audience_filter: Record<string, unknown>;
  scheduled_at: string | null;
  total_recipients: number;
  sent_count: number;
  delivered_count: number;
  read_count: number;
  failed_count: number;
  reply_count: number;
  created_at: string;
}

export function useCampaigns() {
  return useQuery({
    queryKey: ["campaigns"],
    queryFn: async () => (await apiClient.get<PaginatedResponse<CampaignItem>>("/campaigns")).data,
  });
}

export function useCreateCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: Record<string, unknown>) => (await apiClient.post<CampaignItem>("/campaigns", data)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["campaigns"] }),
  });
}

export function useSendCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => (await apiClient.post<CampaignItem>(`/campaigns/${id}/send`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["campaigns"] }),
  });
}

export function useDeleteCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => (await apiClient.delete<SuccessResponse>(`/campaigns/${id}`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["campaigns"] }),
  });
}
