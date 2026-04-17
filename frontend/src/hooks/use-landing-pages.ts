"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { PaginatedResponse, SuccessResponse } from "@/types/api";

export interface BlockContent {
  type: string;
  content: Record<string, unknown>;
  settings: Record<string, unknown>;
}

export interface LandingPageItem {
  id: string;
  title: string;
  slug: string;
  status: string;
  visit_count: number;
  conversion_count: number;
  published_at: string | null;
  created_at: string;
}

export interface LandingPageDetail extends LandingPageItem {
  description: string | null;
  blocks: BlockContent[];
  settings: Record<string, unknown>;
  whatsapp_number: string | null;
  whatsapp_message: string | null;
  meta_title: string | null;
  meta_description: string | null;
  og_image_url: string | null;
  template: string | null;
  company_id: string;
  updated_at: string;
}

export function useLandingPages(status?: string) {
  return useQuery({
    queryKey: ["landing-pages", status],
    queryFn: async () => {
      const params = status ? `?status=${status}` : "";
      const res = await apiClient.get<PaginatedResponse<LandingPageItem>>(
        `/landing-pages${params}`
      );
      return res.data;
    },
  });
}

export function useLandingPage(id: string | null) {
  return useQuery({
    queryKey: ["landing-page", id],
    queryFn: async () => {
      const res = await apiClient.get<LandingPageDetail>(`/landing-pages/${id}`);
      return res.data;
    },
    enabled: !!id,
  });
}

export function useCreateLandingPage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: {
      title: string;
      slug: string;
      blocks?: BlockContent[];
      whatsapp_number?: string;
      whatsapp_message?: string;
    }) => {
      const res = await apiClient.post<LandingPageDetail>("/landing-pages", data);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["landing-pages"] }),
  });
}

export function useUpdateLandingPage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Record<string, unknown> }) => {
      const res = await apiClient.patch<LandingPageDetail>(`/landing-pages/${id}`, data);
      return res.data;
    },
    onSuccess: (_, { id }) => {
      qc.invalidateQueries({ queryKey: ["landing-pages"] });
      qc.invalidateQueries({ queryKey: ["landing-page", id] });
    },
  });
}

export function usePublishLandingPage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const res = await apiClient.post<LandingPageDetail>(`/landing-pages/${id}/publish`);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["landing-pages"] }),
  });
}

export function useDeleteLandingPage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const res = await apiClient.delete<SuccessResponse>(`/landing-pages/${id}`);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["landing-pages"] }),
  });
}
