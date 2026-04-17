"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { SuccessResponse } from "@/types/api";

export interface StageItem {
  id: string;
  name: string;
  color: string;
  sort_order: number;
  is_won: boolean;
  is_lost: boolean;
}

export interface PipelineItem {
  id: string;
  name: string;
  description: string | null;
  is_default: boolean;
  is_active: boolean;
  stages: StageItem[];
  created_at: string;
}

export interface DealItem {
  id: string;
  pipeline_id: string;
  stage_id: string | null;
  stage: StageItem | null;
  title: string;
  description: string | null;
  value: string;
  currency: string;
  status: string;
  contact_id: string | null;
  assigned_to_user_id: string | null;
  expected_close_date: string | null;
  position: number;
  created_at: string;
}

export interface KanbanColumn {
  stage: StageItem;
  deals: DealItem[];
  total_value: string;
  deal_count: number;
}

export interface KanbanBoard {
  pipeline: PipelineItem;
  columns: KanbanColumn[];
}

export function usePipelines() {
  return useQuery({
    queryKey: ["pipelines"],
    queryFn: async () => {
      const res = await apiClient.get<PipelineItem[]>("/pipelines");
      return res.data;
    },
  });
}

export function useKanbanBoard(pipelineId: string | null) {
  return useQuery({
    queryKey: ["kanban", pipelineId],
    queryFn: async () => {
      const res = await apiClient.get<KanbanBoard>(`/pipelines/${pipelineId}/board`);
      return res.data;
    },
    enabled: !!pipelineId,
  });
}

export function useCreatePipeline() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: {
      name: string;
      description?: string;
      stages: { name: string; color: string; sort_order: number; is_won?: boolean; is_lost?: boolean }[];
    }) => {
      const res = await apiClient.post<PipelineItem>("/pipelines", data);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["pipelines"] }),
  });
}

export function useCreateDeal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: {
      pipeline_id: string;
      stage_id?: string;
      title: string;
      value?: number;
      contact_id?: string;
    }) => {
      const res = await apiClient.post<DealItem>("/pipelines/deals", data);
      return res.data;
    },
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["kanban", vars.pipeline_id] });
    },
  });
}

export function useMoveDeal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: {
      deal_id: string;
      stage_id: string;
      position: number;
      pipeline_id: string;
    }) => {
      const res = await apiClient.post<DealItem>(`/pipelines/deals/${data.deal_id}/move`, {
        stage_id: data.stage_id,
        position: data.position,
      });
      return res.data;
    },
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["kanban", vars.pipeline_id] });
    },
  });
}

export function useUpdateDeal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Record<string, unknown> }) => {
      const res = await apiClient.patch<DealItem>(`/pipelines/deals/${id}`, data);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["kanban"] });
    },
  });
}
