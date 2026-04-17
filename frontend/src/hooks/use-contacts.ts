"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type {
  ContactListItem,
  ContactResponse,
  ContactCreate,
  ContactUpdate,
  ContactImportResponse,
  PaginatedResponse,
  SuccessResponse,
} from "@/types/api";

interface ContactFilters {
  limit?: number;
  offset?: number;
  search?: string;
  status?: string;
  source?: string;
  tag_id?: string[];
  assigned_to?: string;
  sort?: string;
}

export function useContacts(filters: ContactFilters = {}) {
  return useQuery({
    queryKey: ["contacts", filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.limit) params.set("limit", String(filters.limit));
      if (filters.offset) params.set("offset", String(filters.offset));
      if (filters.search) params.set("search", filters.search);
      if (filters.status) params.set("status", filters.status);
      if (filters.source) params.set("source", filters.source);
      if (filters.sort) params.set("sort", filters.sort);
      if (filters.tag_id) {
        filters.tag_id.forEach((id) => params.append("tag_id", id));
      }
      if (filters.assigned_to) params.set("assigned_to", filters.assigned_to);

      const res = await apiClient.get<PaginatedResponse<ContactListItem>>(
        `/contacts?${params.toString()}`
      );
      return res.data;
    },
  });
}

export function useContact(id: string | null) {
  return useQuery({
    queryKey: ["contact", id],
    queryFn: async () => {
      const res = await apiClient.get<ContactResponse>(`/contacts/${id}`);
      return res.data;
    },
    enabled: !!id,
  });
}

export function useCreateContact() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: ContactCreate) => {
      const res = await apiClient.post<ContactResponse>("/contacts", data);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["contacts"] });
    },
  });
}

export function useUpdateContact() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: ContactUpdate }) => {
      const res = await apiClient.patch<ContactResponse>(`/contacts/${id}`, data);
      return res.data;
    },
    onSuccess: (_, { id }) => {
      qc.invalidateQueries({ queryKey: ["contacts"] });
      qc.invalidateQueries({ queryKey: ["contact", id] });
    },
  });
}

export function useDeleteContact() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const res = await apiClient.delete<SuccessResponse>(`/contacts/${id}`);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["contacts"] });
    },
  });
}

export function useImportContacts() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      const res = await apiClient.post<ContactImportResponse>(
        "/contacts/import",
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["contacts"] });
    },
  });
}

export function useBulkAction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: {
      contact_ids: string[];
      action: string;
      tag_id?: string;
      status?: string;
      assigned_to_user_id?: string;
    }) => {
      const res = await apiClient.post<SuccessResponse>("/contacts/bulk", data);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["contacts"] });
    },
  });
}
