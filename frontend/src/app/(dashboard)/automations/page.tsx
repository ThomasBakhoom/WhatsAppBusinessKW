"use client";

import { useState } from "react";
import {
  useAutomations,
  useCreateAutomation,
  useToggleAutomation,
  useDeleteAutomation,
  useAutomationLogs,
} from "@/hooks/use-automations";
import type { AutomationItem } from "@/hooks/use-automations";
import { formatRelativeTime } from "@/lib/utils";
import { cn } from "@/lib/utils";

const TRIGGER_LABELS: Record<string, string> = {
  "message.received": "Message Received",
  "contact.created": "Contact Created",
  "contact.updated": "Contact Updated",
  "conversation.created": "Conversation Created",
  "deal.stage_changed": "Deal Stage Changed",
};

const ACTION_LABELS: Record<string, string> = {
  send_message: "Send Message",
  auto_reply: "Auto Reply",
  assign_agent: "Assign Agent",
  add_tag: "Add Tag",
  remove_tag: "Remove Tag",
  change_status: "Change Status",
  update_lead_score: "Update Lead Score",
  send_template: "Send Template",
  webhook: "Webhook",
};

export default function AutomationsPage() {
  const { data: automations, isLoading } = useAutomations();
  const toggleAutomation = useToggleAutomation();
  const deleteAutomation = useDeleteAutomation();
  const [showCreate, setShowCreate] = useState(false);
  const [viewLogs, setViewLogs] = useState<string | null>(null);

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this automation?")) return;
    await deleteAutomation.mutateAsync(id);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Automations</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Automate actions based on events
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          + New Automation
        </button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
      ) : !automations || automations.length === 0 ? (
        <div className="rounded-lg border bg-card p-12 text-center text-muted-foreground">
          No automations yet. Create your first automation to get started.
        </div>
      ) : (
        <div className="space-y-3">
          {automations.map((auto) => (
            <div key={auto.id} className="rounded-lg border bg-card p-4">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <h3 className="font-medium">{auto.name}</h3>
                    <span
                      className={cn(
                        "rounded-full px-2 py-0.5 text-[10px] font-medium",
                        auto.is_active
                          ? "bg-green-100 text-green-700"
                          : "bg-gray-100 text-gray-600"
                      )}
                    >
                      {auto.is_active ? "Active" : "Paused"}
                    </span>
                  </div>
                  {auto.description && (
                    <p className="text-sm text-muted-foreground mt-1">
                      {auto.description}
                    </p>
                  )}
                  <div className="flex flex-wrap items-center gap-2 mt-2">
                    <span className="text-xs bg-blue-50 text-blue-700 rounded px-2 py-0.5">
                      {TRIGGER_LABELS[auto.trigger_event] ?? auto.trigger_event}
                    </span>
                    {auto.conditions.length > 0 && (
                      <span className="text-xs text-muted-foreground">
                        {auto.conditions.length} condition(s)
                      </span>
                    )}
                    <span className="text-xs text-muted-foreground">&rarr;</span>
                    {auto.actions.map((a, i) => (
                      <span
                        key={i}
                        className="text-xs bg-purple-50 text-purple-700 rounded px-2 py-0.5"
                      >
                        {ACTION_LABELS[a.action_type] ?? a.action_type}
                      </span>
                    ))}
                  </div>
                  <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                    <span>Executed {auto.execution_count} times</span>
                    {auto.last_executed_at && (
                      <span>Last: {formatRelativeTime(auto.last_executed_at)}</span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setViewLogs(viewLogs === auto.id ? null : auto.id)}
                    className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                  >
                    Logs
                  </button>
                  <button
                    onClick={() => toggleAutomation.mutate(auto.id)}
                    className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {auto.is_active ? "Pause" : "Activate"}
                  </button>
                  <button
                    onClick={() => handleDelete(auto.id)}
                    className="text-xs text-muted-foreground hover:text-destructive transition-colors"
                  >
                    Delete
                  </button>
                </div>
              </div>

              {viewLogs === auto.id && <LogsPanel automationId={auto.id} />}
            </div>
          ))}
        </div>
      )}

      {showCreate && <CreateAutomationDialog onClose={() => setShowCreate(false)} />}
    </div>
  );
}

function LogsPanel({ automationId }: { automationId: string }) {
  const { data: logs, isLoading } = useAutomationLogs(automationId);

  if (isLoading) return <p className="text-xs text-muted-foreground mt-3">Loading logs...</p>;
  if (!logs || logs.length === 0)
    return <p className="text-xs text-muted-foreground mt-3">No execution logs yet.</p>;

  return (
    <div className="mt-3 border-t pt-3">
      <h4 className="text-xs font-medium mb-2">Recent Executions</h4>
      <div className="space-y-1">
        {logs.slice(0, 10).map((log) => (
          <div key={log.id} className="flex items-center gap-3 text-xs">
            <span
              className={cn(
                "h-2 w-2 rounded-full",
                log.status === "success" ? "bg-green-500" : "bg-red-500"
              )}
            />
            <span className="text-muted-foreground">
              {formatRelativeTime(log.created_at)}
            </span>
            <span>
              {log.actions_executed} action(s) in {log.duration_ms}ms
            </span>
            {log.error_message && (
              <span className="text-destructive truncate max-w-xs">
                {log.error_message}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function CreateAutomationDialog({ onClose }: { onClose: () => void }) {
  const createAutomation = useCreateAutomation();
  const [form, setForm] = useState({
    name: "",
    description: "",
    trigger_event: "message.received",
    condition_field: "",
    condition_operator: "contains",
    condition_value: "",
    action_type: "auto_reply",
    action_config: '{"message": "Thank you for your message! We will get back to you shortly."}',
  });
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    const conditions =
      form.condition_field && form.condition_value
        ? [{ field: form.condition_field, operator: form.condition_operator, value: form.condition_value }]
        : [];

    let actionConfig: Record<string, unknown>;
    try {
      actionConfig = JSON.parse(form.action_config);
    } catch {
      setError("Invalid action config JSON");
      return;
    }

    try {
      await createAutomation.mutateAsync({
        name: form.name,
        description: form.description || undefined,
        trigger_event: form.trigger_event,
        conditions,
        actions: [{ action_type: form.action_type, config: actionConfig, sort_order: 0 }],
      });
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.title || "Failed to create automation");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-lg rounded-xl bg-card p-6 shadow-xl max-h-[90vh] overflow-y-auto">
        <h2 className="text-lg font-semibold mb-4">Create Automation</h2>
        {error && (
          <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>
        )}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Name</label>
            <input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
              placeholder="e.g., Auto-reply to new messages"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Description</label>
            <input
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Trigger</label>
            <select
              value={form.trigger_event}
              onChange={(e) => setForm({ ...form, trigger_event: e.target.value })}
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
            >
              {Object.entries(TRIGGER_LABELS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>

          <fieldset className="rounded-lg border p-3">
            <legend className="text-xs font-medium px-1">Condition (optional)</legend>
            <div className="grid grid-cols-3 gap-2">
              <input
                value={form.condition_field}
                onChange={(e) => setForm({ ...form, condition_field: e.target.value })}
                className="rounded-lg border border-input bg-background px-2 py-1 text-xs"
                placeholder="message.content"
              />
              <select
                value={form.condition_operator}
                onChange={(e) => setForm({ ...form, condition_operator: e.target.value })}
                className="rounded-lg border border-input bg-background px-2 py-1 text-xs"
              >
                <option value="contains">Contains</option>
                <option value="equals">Equals</option>
                <option value="starts_with">Starts with</option>
                <option value="not_equals">Not equals</option>
              </select>
              <input
                value={form.condition_value}
                onChange={(e) => setForm({ ...form, condition_value: e.target.value })}
                className="rounded-lg border border-input bg-background px-2 py-1 text-xs"
                placeholder="value"
              />
            </div>
          </fieldset>

          <div>
            <label className="block text-sm font-medium mb-1">Action</label>
            <select
              value={form.action_type}
              onChange={(e) => setForm({ ...form, action_type: e.target.value })}
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm mb-2"
            >
              {Object.entries(ACTION_LABELS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
            <textarea
              value={form.action_config}
              onChange={(e) => setForm({ ...form, action_config: e.target.value })}
              rows={3}
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-xs font-mono"
              placeholder='{"message": "Hello!"}'
            />
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-accent transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createAutomation.isPending}
              className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
            >
              {createAutomation.isPending ? "Creating..." : "Create"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
