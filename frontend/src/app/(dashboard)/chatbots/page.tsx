"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useChatbots, useCreateChatbot, useToggleChatbot, useDeleteChatbot } from "@/hooks/use-chatbots";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

const TRIGGER_LABELS: Record<string, string> = {
  keyword: "Keyword Match",
  message_received: "Any Message",
  conversation_started: "New Conversation",
  webhook: "Webhook",
};

const NODE_TYPES: Record<string, string> = {
  send_message: "Send Message",
  ask_question: "Ask Question",
  condition: "Condition",
  action: "Action",
  delay: "Delay",
  assign_agent: "Assign Agent",
  api_call: "API Call",
};

export default function ChatbotsPage() {
  const router = useRouter();
  const { data: flows, isLoading } = useChatbots();
  const toggleFlow = useToggleChatbot();
  const deleteFlow = useDeleteChatbot();
  const [showCreate, setShowCreate] = useState(false);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Chatbot Flows</h1>
          <p className="text-sm text-muted-foreground mt-1">Build visual conversation flows</p>
        </div>
        <Button onClick={() => setShowCreate(true)}>+ New Flow</Button>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12"><div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" /></div>
      ) : !flows || flows.length === 0 ? (
        <Card><CardContent className="p-12 text-center text-muted-foreground">No chatbot flows yet. Create your first flow to automate conversations.</CardContent></Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {flows.map((flow) => (
            <Card key={flow.id} className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => router.push(`/chatbots/${flow.id}`)}>
              <CardContent className="p-5">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-medium">{flow.name}</h3>
                      <Badge variant={flow.is_active ? "success" : "secondary"}>{flow.is_active ? "Active" : "Inactive"}</Badge>
                    </div>
                    {flow.description && <p className="text-sm text-muted-foreground mt-1">{flow.description}</p>}
                  </div>
                </div>
                <div className="flex items-center gap-3 mt-3 text-xs text-muted-foreground">
                  <Badge variant="outline">{TRIGGER_LABELS[flow.trigger_type] ?? flow.trigger_type}</Badge>
                  <span>{flow.nodes.length} nodes</span>
                  <span>{flow.edges.length} connections</span>
                  <span>{flow.execution_count} runs</span>
                </div>
                <div className="flex items-center gap-2 mt-3" onClick={(e) => e.stopPropagation()}>
                  <Button size="sm" variant="ghost" onClick={() => toggleFlow.mutate(flow.id)}>
                    {flow.is_active ? "Pause" : "Activate"}
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => { if (confirm("Delete?")) deleteFlow.mutate(flow.id); }}>Delete</Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {showCreate && <CreateFlowDialog onClose={() => setShowCreate(false)} />}
    </div>
  );
}

function CreateFlowDialog({ onClose }: { onClose: () => void }) {
  const router = useRouter();
  const createFlow = useCreateChatbot();
  const [name, setName] = useState("");
  const [trigger, setTrigger] = useState("keyword");
  const [keywords, setKeywords] = useState("menu, help");

  const handleCreate = async () => {
    const flow = await createFlow.mutateAsync({
      name, trigger_type: trigger,
      trigger_config: trigger === "keyword" ? { keywords: keywords.split(",").map((k) => k.trim()), match_type: "contains" } : {},
      nodes: [
        { id: "start", type: "send_message", position: { x: 100, y: 100 }, data: { message: "Welcome! How can I help you today?" } },
      ],
      edges: [],
    });
    onClose();
    router.push(`/chatbots/${flow.id}`);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <Card className="w-full max-w-md">
        <CardContent className="p-6 space-y-4">
          <h2 className="text-lg font-semibold">New Chatbot Flow</h2>
          <div>
            <label className="block text-sm font-medium mb-1">Flow Name</label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g., Welcome Bot" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Trigger</label>
            <select value={trigger} onChange={(e) => setTrigger(e.target.value)}
              className="flex h-9 w-full rounded-lg border border-input bg-background px-3 py-1 text-sm">
              {Object.entries(TRIGGER_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </div>
          {trigger === "keyword" && (
            <div>
              <label className="block text-sm font-medium mb-1">Keywords (comma-separated)</label>
              <Input value={keywords} onChange={(e) => setKeywords(e.target.value)} />
            </div>
          )}
          <div className="flex justify-end gap-3">
            <Button variant="outline" onClick={onClose}>Cancel</Button>
            <Button onClick={handleCreate} disabled={!name || createFlow.isPending}>Create</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
