"use client";

import { useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { useChatbot, useUpdateChatbot } from "@/hooks/use-chatbots";
import type { FlowNode, FlowEdge } from "@/hooks/use-chatbots";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

const NODE_PALETTE = [
  { type: "send_message", label: "Send Message", color: "#25D366" },
  { type: "ask_question", label: "Ask Question", color: "#3B82F6" },
  { type: "condition", label: "Condition", color: "#F97316" },
  { type: "delay", label: "Delay", color: "#8B5CF6" },
  { type: "assign_agent", label: "Assign Agent", color: "#EC4899" },
  { type: "action", label: "Action", color: "#14B8A6" },
  { type: "api_call", label: "API Call", color: "#6366F1" },
];

export default function ChatbotEditorPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { data: flow, isLoading } = useChatbot(id);
  const updateFlow = useUpdateChatbot();
  const [editingNode, setEditingNode] = useState<string | null>(null);

  const addNode = useCallback(async (type: string) => {
    if (!flow) return;
    const newNode: FlowNode = {
      id: `node_${Date.now()}`, type,
      position: { x: 100 + flow.nodes.length * 50, y: 100 + flow.nodes.length * 80 },
      data: type === "send_message" ? { message: "Edit this message" }
        : type === "ask_question" ? { question: "What do you need?", options: ["Option A", "Option B"] }
        : type === "delay" ? { seconds: 5 }
        : type === "condition" ? { field: "message.content", operator: "contains", value: "" }
        : {},
    };
    await updateFlow.mutateAsync({ id, data: { nodes: [...flow.nodes, newNode] } });
  }, [flow, id, updateFlow]);

  const removeNode = useCallback(async (nodeId: string) => {
    if (!flow) return;
    await updateFlow.mutateAsync({
      id,
      data: {
        nodes: flow.nodes.filter((n) => n.id !== nodeId),
        edges: flow.edges.filter((e) => e.source !== nodeId && e.target !== nodeId),
      },
    });
  }, [flow, id, updateFlow]);

  const updateNodeData = useCallback(async (nodeId: string, data: Record<string, unknown>) => {
    if (!flow) return;
    const updated = flow.nodes.map((n) => n.id === nodeId ? { ...n, data: { ...n.data, ...data } } : n);
    await updateFlow.mutateAsync({ id, data: { nodes: updated } });
    setEditingNode(null);
  }, [flow, id, updateFlow]);

  const connectNodes = useCallback(async (sourceId: string, targetId: string) => {
    if (!flow) return;
    const newEdge: FlowEdge = { id: `edge_${Date.now()}`, source: sourceId, target: targetId };
    await updateFlow.mutateAsync({ id, data: { edges: [...flow.edges, newEdge] } });
  }, [flow, id, updateFlow]);

  if (isLoading || !flow) return <div className="flex justify-center py-24"><div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" /></div>;

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div>
          <button onClick={() => router.push("/chatbots")} className="text-sm text-muted-foreground hover:text-foreground mb-1 block">&larr; Back to flows</button>
          <h1 className="text-2xl font-bold">{flow.name}</h1>
          <div className="flex items-center gap-2 mt-1">
            <Badge variant={flow.is_active ? "success" : "secondary"}>{flow.is_active ? "Active" : "Inactive"}</Badge>
            <span className="text-xs text-muted-foreground">{flow.execution_count} executions</span>
          </div>
        </div>
      </div>

      {/* Node Palette */}
      <div className="flex flex-wrap gap-2 mb-4 p-3 rounded-lg border bg-muted/30">
        <span className="text-xs font-medium text-muted-foreground self-center mr-2">Add node:</span>
        {NODE_PALETTE.map((n) => (
          <Button key={n.type} size="sm" variant="outline" onClick={() => addNode(n.type)}
            className="text-xs" style={{ borderColor: n.color, color: n.color }}>
            + {n.label}
          </Button>
        ))}
      </div>

      {/* Visual Flow Canvas */}
      <div className="rounded-lg border bg-card min-h-[500px] p-4">
        {flow.nodes.length === 0 ? (
          <p className="text-center text-muted-foreground py-20">Add nodes from the palette above to build your flow</p>
        ) : (
          <div className="space-y-3">
            {flow.nodes.map((node, idx) => {
              const palette = NODE_PALETTE.find((p) => p.type === node.type);
              const connections = flow.edges.filter((e) => e.source === node.id);
              return (
                <div key={node.id} className="rounded-lg border p-4" style={{ borderLeftWidth: 4, borderLeftColor: palette?.color }}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold rounded px-2 py-0.5" style={{ backgroundColor: palette?.color + "20", color: palette?.color }}>
                        {palette?.label ?? node.type}
                      </span>
                      <span className="text-xs text-muted-foreground">#{idx + 1}</span>
                    </div>
                    <div className="flex gap-1">
                      <Button size="sm" variant="ghost" onClick={() => setEditingNode(editingNode === node.id ? null : node.id)}>Edit</Button>
                      <Button size="sm" variant="ghost" onClick={() => removeNode(node.id)}>Remove</Button>
                    </div>
                  </div>

                  {/* Node content preview */}
                  <div className="mt-2 text-sm">
                    {Boolean(node.data.message) && <p>{String(node.data.message)}</p>}
                    {Boolean(node.data.question) && <p>{String(node.data.question)}</p>}
                    {Boolean(node.data.seconds) && <p>Wait {String(node.data.seconds)}s</p>}
                  </div>

                  {/* Connections */}
                  {connections.length > 0 && (
                    <div className="mt-2 text-xs text-muted-foreground">
                      &darr; connects to: {connections.map((e) => {
                        const target = flow.nodes.find((n) => n.id === e.target);
                        return target ? `${NODE_PALETTE.find((p) => p.type === target.type)?.label ?? target.type}` : e.target;
                      }).join(", ")}
                    </div>
                  )}

                  {/* Inline editor */}
                  {editingNode === node.id && (
                    <NodeEditor node={node} onSave={(data) => updateNodeData(node.id, data)} onCancel={() => setEditingNode(null)}
                      availableTargets={flow.nodes.filter((n) => n.id !== node.id).map((n) => ({ id: n.id, label: NODE_PALETTE.find((p) => p.type === n.type)?.label ?? n.type }))}
                      onConnect={(targetId) => connectNodes(node.id, targetId)} />
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function NodeEditor({ node, onSave, onCancel, availableTargets, onConnect }: {
  node: FlowNode; onSave: (data: Record<string, unknown>) => void; onCancel: () => void;
  availableTargets: { id: string; label: string }[]; onConnect: (targetId: string) => void;
}) {
  const [data, setData] = useState<Record<string, string>>(
    Object.fromEntries(Object.entries(node.data).map(([k, v]) => [k, String(v)]))
  );

  const fields = node.type === "send_message" ? ["message"]
    : node.type === "ask_question" ? ["question"]
    : node.type === "delay" ? ["seconds"]
    : node.type === "condition" ? ["field", "operator", "value"]
    : ["config"];

  return (
    <div className="mt-3 border-t pt-3 space-y-3">
      {fields.map((f) => (
        <div key={f}>
          <label className="text-xs font-medium capitalize">{f}</label>
          {f === "message" || f === "question" ? (
            <textarea value={data[f] || ""} onChange={(e) => setData({ ...data, [f]: e.target.value })} rows={2}
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm mt-1" />
          ) : (
            <Input value={data[f] || ""} onChange={(e) => setData({ ...data, [f]: e.target.value })} className="mt-1" />
          )}
        </div>
      ))}
      {availableTargets.length > 0 && (
        <div>
          <label className="text-xs font-medium">Connect to:</label>
          <select onChange={(e) => { if (e.target.value) onConnect(e.target.value); }}
            className="flex h-8 w-full rounded-lg border border-input bg-background px-2 text-xs mt-1">
            <option value="">Select next node...</option>
            {availableTargets.map((t) => <option key={t.id} value={t.id}>{t.label}</option>)}
          </select>
        </div>
      )}
      <div className="flex gap-2">
        <Button size="sm" variant="outline" onClick={onCancel}>Cancel</Button>
        <Button size="sm" onClick={() => onSave(data)}>Save</Button>
      </div>
    </div>
  );
}
