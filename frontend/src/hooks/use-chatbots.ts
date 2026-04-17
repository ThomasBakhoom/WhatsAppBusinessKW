"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { SuccessResponse } from "@/types/api";

export interface FlowNode {
  id: string;
  type: string;
  position: { x: number; y: number };
  data: Record<string, unknown>;
}

export interface FlowEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
}

export interface ChatbotFlow {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  trigger_type: string;
  trigger_config: Record<string, unknown>;
  nodes: FlowNode[];
  edges: FlowEdge[];
  execution_count: number;
  created_at: string;
  updated_at: string;
}

export function useChatbots() {
  return useQuery({
    queryKey: ["chatbots"],
    queryFn: async () => (await apiClient.get<ChatbotFlow[]>("/chatbots")).data,
  });
}

export function useChatbot(id: string | null) {
  return useQuery({
    queryKey: ["chatbot", id],
    queryFn: async () => (await apiClient.get<ChatbotFlow>(`/chatbots/${id}`)).data,
    enabled: !!id,
  });
}

export function useCreateChatbot() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: Record<string, unknown>) => (await apiClient.post<ChatbotFlow>("/chatbots", data)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["chatbots"] }),
  });
}

export function useUpdateChatbot() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Record<string, unknown> }) =>
      (await apiClient.patch<ChatbotFlow>(`/chatbots/${id}`, data)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["chatbots"] }),
  });
}

export function useToggleChatbot() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => (await apiClient.post<ChatbotFlow>(`/chatbots/${id}/toggle`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["chatbots"] }),
  });
}

export function useDeleteChatbot() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => (await apiClient.delete<SuccessResponse>(`/chatbots/${id}`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["chatbots"] }),
  });
}
