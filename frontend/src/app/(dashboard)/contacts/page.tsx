"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useContacts, useDeleteContact, useBulkAction } from "@/hooks/use-contacts";
import { useTags } from "@/hooks/use-tags";
import { TagBadge } from "@/components/contacts/tag-badge";
import { StatusBadge } from "@/components/contacts/status-badge";
import { CreateContactDialog } from "@/components/contacts/create-contact-dialog";
import { ImportDialog } from "@/components/contacts/import-dialog";
import { formatRelativeTime } from "@/lib/utils";

const PAGE_SIZE = 20;

export default function ContactsPage() {
  const router = useRouter();
  const [page, setPage] = useState(0);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [tagFilter, setTagFilter] = useState<string[]>([]);
  const [sortField, setSortField] = useState("-created_at");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [showCreate, setShowCreate] = useState(false);
  const [showImport, setShowImport] = useState(false);

  const { data: tags } = useTags();
  const deleteContact = useDeleteContact();
  const bulkAction = useBulkAction();

  // Debounce search
  const handleSearch = useCallback((value: string) => {
    setSearch(value);
    const timeout = setTimeout(() => {
      setDebouncedSearch(value);
      setPage(0);
    }, 300);
    return () => clearTimeout(timeout);
  }, []);

  const { data, isLoading, isError } = useContacts({
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
    search: debouncedSearch || undefined,
    status: statusFilter || undefined,
    source: sourceFilter || undefined,
    tag_id: tagFilter.length > 0 ? tagFilter : undefined,
    sort: sortField,
  });

  const contacts = data?.data ?? [];
  const total = data?.meta?.total ?? 0;
  const totalPages = Math.ceil(total / PAGE_SIZE);

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === contacts.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(contacts.map((c) => c.id)));
    }
  };

  const handleBulkDelete = async () => {
    if (selectedIds.size === 0) return;
    if (!confirm(`Delete ${selectedIds.size} contacts?`)) return;
    await bulkAction.mutateAsync({
      contact_ids: Array.from(selectedIds),
      action: "delete",
    });
    setSelectedIds(new Set());
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this contact?")) return;
    await deleteContact.mutateAsync(id);
  };

  const handleSort = (field: string) => {
    if (sortField === field) setSortField(`-${field}`);
    else if (sortField === `-${field}`) setSortField(field);
    else setSortField(`-${field}`);
  };

  const SortIcon = ({ field }: { field: string }) => {
    if (sortField === field) return <span className="ml-1">&#9650;</span>;
    if (sortField === `-${field}`) return <span className="ml-1">&#9660;</span>;
    return null;
  };

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight" style={{ color: "#0F172A" }}>Contacts</h1>
          <p className="text-sm mt-1" style={{ color: "#64748B" }}>
            {total} contact{total !== 1 ? "s" : ""} in your CRM
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowImport(true)}
            className="rounded-xl px-4 py-2.5 text-sm font-medium transition-all hover:scale-[1.01]"
            style={{ background: "#F1F5F9", color: "#334155", border: "1px solid #E2E8F0" }}
          >
            Import CSV
          </button>
          <button
            onClick={() => setShowCreate(true)}
            className="rounded-xl px-4 py-2.5 text-sm font-semibold text-white transition-all hover:scale-[1.01]"
            style={{ background: "linear-gradient(135deg, #10B981, #059669)", boxShadow: "0 2px 8px rgba(16,185,129,0.25)" }}
          >
            + Add Contact
          </button>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <div className="relative">
          <svg className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4" style={{ color: "#94A3B8" }} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
          <input
            type="text"
            placeholder="Search name, phone, email..."
            value={search}
            onChange={(e) => handleSearch(e.target.value)}
            className="w-64 rounded-xl pl-9 pr-3 py-2.5 text-sm"
            style={{ background: "#F8FAFC", border: "1px solid #E2E8F0", color: "#0F172A" }}
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(0); }}
          className="rounded-lg border border-input bg-background px-3 py-2 text-sm"
        >
          <option value="">All Statuses</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
          <option value="blocked">Blocked</option>
        </select>
        <select
          value={sourceFilter}
          onChange={(e) => { setSourceFilter(e.target.value); setPage(0); }}
          className="rounded-lg border border-input bg-background px-3 py-2 text-sm"
        >
          <option value="">All Sources</option>
          <option value="manual">Manual</option>
          <option value="import">Import</option>
          <option value="whatsapp">WhatsApp</option>
          <option value="landing_page">Landing Page</option>
          <option value="api">API</option>
        </select>
        {tags && tags.length > 0 && (
          <select
            value={tagFilter[0] ?? ""}
            onChange={(e) => {
              setTagFilter(e.target.value ? [e.target.value] : []);
              setPage(0);
            }}
            className="rounded-lg border border-input bg-background px-3 py-2 text-sm"
          >
            <option value="">All Tags</option>
            {tags.map((tag) => (
              <option key={tag.id} value={tag.id}>
                {tag.name}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Bulk Actions */}
      {selectedIds.size > 0 && (
        <div className="flex items-center gap-3 mb-4 rounded-lg bg-blue-50 p-3">
          <span className="text-sm font-medium text-blue-700">
            {selectedIds.size} selected
          </span>
          <button
            onClick={handleBulkDelete}
            className="rounded-lg bg-destructive px-3 py-1 text-xs font-medium text-destructive-foreground hover:bg-destructive/90 transition-colors"
          >
            Delete
          </button>
          <button
            onClick={() => setSelectedIds(new Set())}
            className="text-xs text-blue-600 hover:underline"
          >
            Clear selection
          </button>
        </div>
      )}

      {/* Table */}
      <div className="rounded-2xl bg-white overflow-hidden" style={{ border: "1px solid #E2E8F0", boxShadow: "0 1px 3px rgba(0,0,0,0.04)" }}>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="w-10 px-4 py-3">
                  <input
                    type="checkbox"
                    checked={contacts.length > 0 && selectedIds.size === contacts.length}
                    onChange={toggleSelectAll}
                    className="rounded"
                  />
                </th>
                <th
                  className="px-4 py-3 text-start text-xs font-medium text-muted-foreground uppercase cursor-pointer hover:text-foreground"
                  onClick={() => handleSort("first_name")}
                >
                  Name <SortIcon field="first_name" />
                </th>
                <th className="px-4 py-3 text-start text-xs font-medium text-muted-foreground uppercase">
                  Phone
                </th>
                <th className="px-4 py-3 text-start text-xs font-medium text-muted-foreground uppercase">
                  Email
                </th>
                <th
                  className="px-4 py-3 text-start text-xs font-medium text-muted-foreground uppercase cursor-pointer hover:text-foreground"
                  onClick={() => handleSort("status")}
                >
                  Status <SortIcon field="status" />
                </th>
                <th className="px-4 py-3 text-start text-xs font-medium text-muted-foreground uppercase">
                  Tags
                </th>
                <th className="px-4 py-3 text-start text-xs font-medium text-muted-foreground uppercase">
                  Source
                </th>
                <th
                  className="px-4 py-3 text-start text-xs font-medium text-muted-foreground uppercase cursor-pointer hover:text-foreground"
                  onClick={() => handleSort("lead_score")}
                >
                  Score <SortIcon field="lead_score" />
                </th>
                <th
                  className="px-4 py-3 text-start text-xs font-medium text-muted-foreground uppercase cursor-pointer hover:text-foreground"
                  onClick={() => handleSort("created_at")}
                >
                  Created <SortIcon field="created_at" />
                </th>
                <th className="px-4 py-3 text-end text-xs font-medium text-muted-foreground uppercase">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={10} className="px-4 py-12 text-center text-muted-foreground">
                    <div className="flex items-center justify-center gap-2">
                      <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                      Loading contacts...
                    </div>
                  </td>
                </tr>
              ) : isError ? (
                <tr>
                  <td colSpan={10} className="px-4 py-12 text-center text-destructive">
                    Failed to load contacts
                  </td>
                </tr>
              ) : contacts.length === 0 ? (
                <tr>
                  <td colSpan={10} className="px-4 py-12 text-center text-muted-foreground">
                    {debouncedSearch || statusFilter || sourceFilter
                      ? "No contacts match your filters"
                      : "No contacts yet. Add your first contact!"}
                  </td>
                </tr>
              ) : (
                contacts.map((contact) => (
                  <tr
                    key={contact.id}
                    className="border-b last:border-0 hover:bg-muted/30 transition-colors cursor-pointer"
                    onClick={() => router.push(`/contacts/${contact.id}`)}
                  >
                    <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={selectedIds.has(contact.id)}
                        onChange={() => toggleSelect(contact.id)}
                        className="rounded"
                      />
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-medium text-sm">
                        {contact.full_name}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">
                      {contact.phone}
                    </td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">
                      {contact.email || "—"}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={contact.status} />
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {contact.tags.map((tag) => (
                          <TagBadge key={tag.id} tag={tag} />
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-muted-foreground capitalize">
                      {contact.source}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <span className="font-medium">{contact.lead_score}</span>
                    </td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">
                      {formatRelativeTime(contact.created_at)}
                    </td>
                    <td className="px-4 py-3 text-end" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() => handleDelete(contact.id)}
                        className="text-xs text-muted-foreground hover:text-destructive transition-colors"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between border-t px-4 py-3">
            <p className="text-sm text-muted-foreground">
              Showing {page * PAGE_SIZE + 1}–
              {Math.min((page + 1) * PAGE_SIZE, total)} of {total}
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="rounded-lg border border-border px-3 py-1 text-sm hover:bg-accent transition-colors disabled:opacity-50"
              >
                Previous
              </button>
              <span className="text-sm text-muted-foreground">
                Page {page + 1} of {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="rounded-lg border border-border px-3 py-1 text-sm hover:bg-accent transition-colors disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Dialogs */}
      <CreateContactDialog open={showCreate} onClose={() => setShowCreate(false)} />
      <ImportDialog open={showImport} onClose={() => setShowImport(false)} />
    </div>
  );
}
