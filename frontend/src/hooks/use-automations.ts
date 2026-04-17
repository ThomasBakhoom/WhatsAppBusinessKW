"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { SuccessResponse } from "@/types/api";

export interface AutomationAction {
  id?: string;
  action_type: string;
  config: Record<string, unknown>;
  sort_order: number;
}

export interface AutomationCondition {
  field: string;
  operator: string;
  value: unknown;
}

export interface AutomationItem {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  trigger_event: string;
  conditions: AutomationCondition[];
  actions: AutomationAction[];
  priority: number;
  execution_count: number;
  last_executed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AutomationLog {
  id: string;
  automation_id: string;
  trigger_event: string;
  trigger_data: Record<string, unknown>;
  status: string;
  actions_executed: number;
  error_message: string | null;
  duration_ms: number | null;
  created_at: string;
}

export function useAutomations() {
  return useQuery({
    queryKey: ["automations"],
    queryFn: async () => {
      const res = await apiClient.get<AutomationItem[]>("/automations");
      return res.data;
    },
  });
}

export function useCreateAutomation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: {
      name: string;
      description?: string;
      trigger_event: string;
      conditions?: AutomationCondition[];
      actions: { action_type: string; config: Record<string, unknown>; sort_order: number }[];
      priority?: number;
    }) => {
      const res = await apiClient.post<AutomationItem>("/automations", data);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["automations"] }),
  });
}

export function useToggleAutomation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const res = await apiClient.post<AutomationItem>(`/automations/${id}/toggle`);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["automations"] }),
  });
}

export function useDeleteAutomation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const res = await apiClient.delete<SuccessResponse>(`/automations/${id}`);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["automations"] }),
  });
}

export function useAutomationLogs(id: string | null) {
  return useQuery({
    queryKey: ["automation-logs", id],
    queryFn: async () => {
      const res = await apiClient.get<AutomationLog[]>(`/automations/${id}/logs`);
      return res.data;
    },
    enabled: !!id,
  });
}
