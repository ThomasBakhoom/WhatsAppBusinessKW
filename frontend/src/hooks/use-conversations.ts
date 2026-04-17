"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { PaginatedResponse } from "@/types/api";

export interface ConversationItem {
  id: string;
  contact_id: string;
  contact: {
    id: string;
    phone: string;
    full_name: string;
    email: string | null;
    status: string;
    tags: { id: string; name: string; color: string }[];
  } | null;
  status: string;
  assigned_to_user_id: string | null;
  last_message_at: string | null;
  last_message_preview: string | null;
  unread_count: number;
  channel: string;
  created_at: string;
}

export interface MessageItem {
  id: string;
  conversation_id: string;
  direction: string;
  sender_type: string;
  sender_id: string | null;
  message_type: string;
  content: string | null;
  media_url: string | null;
  external_id: string | null;
  delivery_status: string;
  delivery_error: string | null;
  created_at: string;
}

export interface ConversationDetail extends ConversationItem {
  messages: MessageItem[];
}

export function useConversations(filters: {
  status?: string;
  limit?: number;
  offset?: number;
} = {}) {
  return useQuery({
    queryKey: ["conversations", filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.status) params.set("status", filters.status);
      if (filters.limit) params.set("limit", String(filters.limit));
      if (filters.offset) params.set("offset", String(filters.offset));
      const res = await apiClient.get<PaginatedResponse<ConversationItem>>(
        `/conversations?${params.toString()}`
      );
      return res.data;
    },
    refetchInterval: 5000,
  });
}

export function useConversation(id: string | null) {
  return useQuery({
    queryKey: ["conversation", id],
    queryFn: async () => {
      const res = await apiClient.get<ConversationDetail>(
        `/conversations/${id}`
      );
      return res.data;
    },
    enabled: !!id,
    refetchInterval: 3000,
  });
}

export function useSendMessage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: {
      conversation_id: string;
      content: string;
      message_type?: string;
    }) => {
      const res = await apiClient.post<MessageItem>(
        "/conversations/messages/send",
        data
      );
      return res.data;
    },
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["conversation", vars.conversation_id] });
      qc.invalidateQueries({ queryKey: ["conversations"] });
    },
  });
}

export function useUpdateConversation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      data,
    }: {
      id: string;
      data: { status?: string; assigned_to_user_id?: string };
    }) => {
      const res = await apiClient.patch<ConversationItem>(
        `/conversations/${id}`,
        data
      );
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["conversations"] });
    },
  });
}
