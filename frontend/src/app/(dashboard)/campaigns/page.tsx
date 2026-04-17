"use client";

import { useState } from "react";
import { useCampaigns, useCreateCampaign, useSendCampaign, useDeleteCampaign } from "@/hooks/use-campaigns";
import { useTags } from "@/hooks/use-tags";
import { formatRelativeTime } from "@/lib/utils";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";

export default function CampaignsPage() {
  const { data, isLoading } = useCampaigns();
  const createCampaign = useCreateCampaign();
  const sendCampaign = useSendCampaign();
  const deleteCampaign = useDeleteCampaign();
  const { data: tags } = useTags();
  const [showCreate, setShowCreate] = useState(false);

  const campaigns = data?.data ?? [];

  const handleCreate = async (form: Record<string, unknown>) => {
    await createCampaign.mutateAsync(form);
    setShowCreate(false);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Campaigns</h1>
          <p className="text-sm text-muted-foreground mt-1">Send bulk WhatsApp broadcasts</p>
        </div>
        <Button onClick={() => setShowCreate(true)}>+ New Campaign</Button>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12"><div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" /></div>
      ) : campaigns.length === 0 ? (
        <Card><CardContent className="p-12 text-center text-muted-foreground">No campaigns yet. Create your first broadcast campaign.</CardContent></Card>
      ) : (
        <div className="space-y-3">
          {campaigns.map((c) => (
            <Card key={c.id}>
              <CardContent className="p-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3">
                      <h3 className="font-medium">{c.name}</h3>
                      <Badge variant={c.status === "sent" ? "success" : c.status === "sending" ? "warning" : "secondary"}>
                        {c.status}
                      </Badge>
                    </div>
                    {c.description && <p className="text-sm text-muted-foreground mt-1">{c.description}</p>}
                    <div className="flex items-center gap-4 mt-3 text-xs text-muted-foreground">
                      <span>{c.audience_type} audience</span>
                      <span>{c.total_recipients} recipients</span>
                      {c.template_name && <span>Template: {c.template_name}</span>}
                    </div>
                    {c.total_recipients > 0 && (
                      <div className="flex gap-4 mt-3">
                        <StatPill label="Sent" value={c.sent_count} total={c.total_recipients} color="bg-blue-500" />
                        <StatPill label="Delivered" value={c.delivered_count} total={c.total_recipients} color="bg-green-500" />
                        <StatPill label="Read" value={c.read_count} total={c.total_recipients} color="bg-purple-500" />
                        <StatPill label="Failed" value={c.failed_count} total={c.total_recipients} color="bg-red-500" />
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {c.status === "draft" && (
                      <Button size="sm" onClick={() => sendCampaign.mutate(c.id)}>Send</Button>
                    )}
                    <Button size="sm" variant="ghost" onClick={() => { if (confirm("Delete?")) deleteCampaign.mutate(c.id); }}>Delete</Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {showCreate && <CreateCampaignDialog onClose={() => setShowCreate(false)} onCreate={handleCreate} tags={tags || []} />}
    </div>
  );
}

function StatPill({ label, value, total, color }: { label: string; value: number; total: number; color: string }) {
  const pct = total > 0 ? Math.round(value / total * 100) : 0;
  return (
    <div className="text-xs">
      <span className="text-muted-foreground">{label}: </span>
      <span className="font-medium">{value}</span>
      <span className="text-muted-foreground"> ({pct}%)</span>
      <div className="mt-1 h-1.5 w-16 bg-muted rounded-full overflow-hidden">
        <div className={cn("h-full rounded-full", color)} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function CreateCampaignDialog({ onClose, onCreate, tags }: { onClose: () => void; onCreate: (data: Record<string, unknown>) => void; tags: { id: string; name: string }[] }) {
  const [form, setForm] = useState({ name: "", message_type: "template", template_name: "", message_body: "", audience_type: "all" });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <Card className="w-full max-w-lg">
        <CardHeader><CardTitle>New Campaign</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Campaign Name</label>
            <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g., Ramadan 2026 Promo" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Message Type</label>
            <select value={form.message_type} onChange={(e) => setForm({ ...form, message_type: e.target.value })}
              className="flex h-9 w-full rounded-lg border border-input bg-background px-3 py-1 text-sm">
              <option value="template">Template</option>
              <option value="text">Text</option>
            </select>
          </div>
          {form.message_type === "template" ? (
            <div>
              <label className="block text-sm font-medium mb-1">Template Name</label>
              <Input value={form.template_name} onChange={(e) => setForm({ ...form, template_name: e.target.value })} placeholder="e.g., ramadan_offer" />
            </div>
          ) : (
            <div>
              <label className="block text-sm font-medium mb-1">Message</label>
              <textarea value={form.message_body} onChange={(e) => setForm({ ...form, message_body: e.target.value })} rows={3}
                className="flex w-full rounded-lg border border-input bg-background px-3 py-2 text-sm" />
            </div>
          )}
          <div>
            <label className="block text-sm font-medium mb-1">Audience</label>
            <select value={form.audience_type} onChange={(e) => setForm({ ...form, audience_type: e.target.value })}
              className="flex h-9 w-full rounded-lg border border-input bg-background px-3 py-1 text-sm">
              <option value="all">All Contacts (opted-in)</option>
              <option value="tag">By Tag</option>
              <option value="segment">By Segment</option>
            </select>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="outline" onClick={onClose}>Cancel</Button>
            <Button onClick={() => form.name && onCreate(form)} disabled={!form.name}>Create</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
