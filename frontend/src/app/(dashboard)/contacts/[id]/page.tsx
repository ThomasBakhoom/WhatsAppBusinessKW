"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useContact, useUpdateContact, useDeleteContact } from "@/hooks/use-contacts";
import { useTags } from "@/hooks/use-tags";
import { TagBadge } from "@/components/contacts/tag-badge";
import { StatusBadge } from "@/components/contacts/status-badge";
import { formatDate } from "@/lib/utils";

export default function ContactDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { data: contact, isLoading, isError } = useContact(id);
  const { data: allTags } = useTags();
  const updateContact = useUpdateContact();
  const deleteContact = useDeleteContact();

  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<Record<string, string>>({});
  const [selectedTagIds, setSelectedTagIds] = useState<string[]>([]);
  const [error, setError] = useState("");

  const startEditing = () => {
    if (!contact) return;
    setForm({
      first_name: contact.first_name,
      last_name: contact.last_name,
      phone: contact.phone,
      email: contact.email ?? "",
      notes: contact.notes ?? "",
      status: contact.status,
    });
    setSelectedTagIds(contact.tags.map((t) => t.id));
    setEditing(true);
    setError("");
  };

  const handleSave = async () => {
    if (!contact) return;
    setError("");

    try {
      await updateContact.mutateAsync({
        id: contact.id,
        data: {
          first_name: form.first_name,
          last_name: form.last_name,
          phone: form.phone,
          email: form.email || undefined,
          notes: form.notes || undefined,
          status: form.status,
          tag_ids: selectedTagIds,
        },
      });
      setEditing(false);
    } catch (err: any) {
      setError(err.response?.data?.title || "Failed to update contact");
    }
  };

  const handleDelete = async () => {
    if (!contact) return;
    if (!confirm("Delete this contact?")) return;
    await deleteContact.mutateAsync(contact.id);
    router.push("/contacts");
  };

  const toggleTag = (tagId: string) => {
    setSelectedTagIds((prev) =>
      prev.includes(tagId) ? prev.filter((id) => id !== tagId) : [...prev, tagId]
    );
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (isError || !contact) {
    return (
      <div className="py-24 text-center">
        <p className="text-destructive">Contact not found</p>
        <button
          onClick={() => router.push("/contacts")}
          className="mt-4 text-sm text-primary hover:underline"
        >
          Back to contacts
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-3xl">
      {/* Back button + Header */}
      <div className="mb-6">
        <button
          onClick={() => router.push("/contacts")}
          className="text-sm text-muted-foreground hover:text-foreground transition-colors mb-4 block"
        >
          &larr; Back to contacts
        </button>

        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold">{contact.full_name}</h1>
            <p className="text-muted-foreground mt-1">{contact.phone}</p>
          </div>
          <div className="flex gap-2">
            {!editing ? (
              <>
                <button
                  onClick={startEditing}
                  className="rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-accent transition-colors"
                >
                  Edit
                </button>
                <button
                  onClick={handleDelete}
                  className="rounded-lg border border-destructive px-4 py-2 text-sm font-medium text-destructive hover:bg-destructive/10 transition-colors"
                >
                  Delete
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => setEditing(false)}
                  className="rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-accent transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSave}
                  disabled={updateContact.isPending}
                  className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
                >
                  {updateContact.isPending ? "Saving..." : "Save"}
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>
      )}

      {/* Detail Card */}
      <div className="rounded-lg border bg-card">
        {editing ? (
          <div className="p-6 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">First Name</label>
                <input
                  value={form.first_name}
                  onChange={(e) => setForm({ ...form, first_name: e.target.value })}
                  className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Last Name</label>
                <input
                  value={form.last_name}
                  onChange={(e) => setForm({ ...form, last_name: e.target.value })}
                  className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Phone</label>
              <input
                value={form.phone}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
                className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Email</label>
              <input
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Status</label>
              <select
                value={form.status}
                onChange={(e) => setForm({ ...form, status: e.target.value })}
                className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
              >
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
                <option value="blocked">Blocked</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Notes</label>
              <textarea
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
                rows={3}
                className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
              />
            </div>
            {allTags && allTags.length > 0 && (
              <div>
                <label className="block text-sm font-medium mb-2">Tags</label>
                <div className="flex flex-wrap gap-2">
                  {allTags.map((tag) => (
                    <button
                      key={tag.id}
                      type="button"
                      onClick={() => toggleTag(tag.id)}
                      className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                        selectedTagIds.includes(tag.id)
                          ? "text-white"
                          : "bg-gray-100 text-gray-600"
                      }`}
                      style={
                        selectedTagIds.includes(tag.id)
                          ? { backgroundColor: tag.color }
                          : undefined
                      }
                    >
                      {tag.name}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="divide-y">
            <div className="grid grid-cols-2 gap-x-8 gap-y-4 p-6">
              <Field label="Phone" value={contact.phone} />
              <Field label="Email" value={contact.email || "—"} />
              <Field label="Status">
                <StatusBadge status={contact.status} />
              </Field>
              <Field label="Source" value={contact.source} />
              <Field label="Lead Score" value={String(contact.lead_score)} />
              <Field
                label="WhatsApp Opt-In"
                value={contact.opt_in_whatsapp ? "Yes" : "No"}
              />
              <Field
                label="Last Contacted"
                value={
                  contact.last_contacted_at
                    ? formatDate(contact.last_contacted_at)
                    : "Never"
                }
              />
              <Field label="Created" value={formatDate(contact.created_at)} />
            </div>

            {contact.tags.length > 0 && (
              <div className="p-6">
                <h3 className="text-sm font-medium text-muted-foreground mb-2">Tags</h3>
                <div className="flex flex-wrap gap-2">
                  {contact.tags.map((tag) => (
                    <TagBadge key={tag.id} tag={tag} />
                  ))}
                </div>
              </div>
            )}

            {contact.notes && (
              <div className="p-6">
                <h3 className="text-sm font-medium text-muted-foreground mb-2">Notes</h3>
                <p className="text-sm whitespace-pre-wrap">{contact.notes}</p>
              </div>
            )}

            {contact.custom_fields && contact.custom_fields.length > 0 && (
              <div className="p-6">
                <h3 className="text-sm font-medium text-muted-foreground mb-3">
                  Custom Fields
                </h3>
                <div className="grid grid-cols-2 gap-x-8 gap-y-3">
                  {contact.custom_fields.map((cf) => (
                    <Field
                      key={cf.custom_field_id}
                      label={cf.field_label}
                      value={cf.value || "—"}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  children,
}: {
  label: string;
  value?: string;
  children?: React.ReactNode;
}) {
  return (
    <div>
      <dt className="text-xs font-medium text-muted-foreground uppercase">{label}</dt>
      <dd className="mt-1 text-sm">{children ?? value}</dd>
    </div>
  );
}
