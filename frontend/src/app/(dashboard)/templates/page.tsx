"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { cn } from "@/lib/utils";

interface TemplateItem {
  id: string;
  name: string;
  language: string;
  category: string;
  status: string;
  body: string;
  header_type: string | null;
  footer: string | null;
  created_at: string;
}

export default function TemplatesPage() {
  // Templates are stored as MessageTemplate model - query will work once API is added
  // For now show the UI shell with placeholder data
  const [showCreate, setShowCreate] = useState(false);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Message Templates</h1>
          <p className="text-sm text-muted-foreground mt-1">
            WhatsApp message templates for marketing and utility messages
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          + New Template
        </button>
      </div>

      <div className="rounded-lg border bg-card p-12 text-center text-muted-foreground">
        <p className="mb-2">No message templates yet.</p>
        <p className="text-xs">Templates must be approved by WhatsApp before use. Create a template to submit for review.</p>
      </div>

      {showCreate && <CreateTemplateDialog onClose={() => setShowCreate(false)} />}
    </div>
  );
}

function CreateTemplateDialog({ onClose }: { onClose: () => void }) {
  const [form, setForm] = useState({
    name: "",
    language: "en",
    category: "MARKETING",
    body: "",
    footer: "",
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-lg rounded-xl bg-card p-6 shadow-xl">
        <h2 className="text-lg font-semibold mb-4">Create Template</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Template Name</label>
            <input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
              placeholder="e.g., welcome_message"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Language</label>
              <select
                value={form.language}
                onChange={(e) => setForm({ ...form, language: e.target.value })}
                className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
              >
                <option value="en">English</option>
                <option value="ar">Arabic</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Category</label>
              <select
                value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value })}
                className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
              >
                <option value="MARKETING">Marketing</option>
                <option value="UTILITY">Utility</option>
                <option value="AUTHENTICATION">Authentication</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Body</label>
            <textarea
              value={form.body}
              onChange={(e) => setForm({ ...form, body: e.target.value })}
              rows={4}
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
              placeholder="Hello {{1}}! Thank you for choosing us."
            />
            <p className="text-xs text-muted-foreground mt-1">Use {"{{1}}"}, {"{{2}}"} for variable placeholders</p>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Footer (optional)</label>
            <input
              value={form.footer}
              onChange={(e) => setForm({ ...form, footer: e.target.value })}
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
            />
          </div>
          <div className="flex justify-end gap-3">
            <button onClick={onClose} className="rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-accent">Cancel</button>
            <button className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90">
              Create (Coming Soon)
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
