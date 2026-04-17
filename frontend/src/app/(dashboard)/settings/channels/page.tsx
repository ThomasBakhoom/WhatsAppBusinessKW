"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";

const CHANNEL_ICONS: Record<string, string> = {
  whatsapp: "💬", instagram: "📸", facebook_messenger: "💙",
  web_chat: "🌐", sms: "📱", email: "📧",
};

export default function ChannelsPage() {
  const qc = useQueryClient();
  const { data: channels, isLoading } = useQuery({
    queryKey: ["channels"],
    queryFn: async () => (await apiClient.get("/channels")).data,
  });
  const createWidget = useMutation({
    mutationFn: async () => (await apiClient.post("/channels/web-chat-widget")).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["channels"] }),
  });
  const [showAdd, setShowAdd] = useState(false);
  const [widget, setWidget] = useState<{ embed_code: string; widget_token: string } | null>(null);

  const handleCreateWidget = async () => {
    const w = await createWidget.mutateAsync();
    setWidget(w);
  };

  return (
    <div className="max-w-3xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Channels</h1>
          <p className="text-sm text-muted-foreground mt-1">Manage your messaging channels</p>
        </div>
        <Button onClick={() => setShowAdd(true)}>+ Add Channel</Button>
      </div>

      {/* Available channels */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-6">
        {["whatsapp", "instagram", "facebook_messenger", "web_chat", "sms", "email"].map((ch) => {
          const connected = (channels as any[])?.find((c: any) => c.channel_type === ch);
          return (
            <Card key={ch} className={connected ? "ring-2 ring-primary" : ""}>
              <CardContent className="p-4 text-center">
                <span className="text-3xl">{CHANNEL_ICONS[ch]}</span>
                <p className="text-sm font-medium mt-2 capitalize">{ch.replace("_", " ")}</p>
                <Badge variant={connected ? "success" : "secondary"} className="mt-2">
                  {connected ? "Connected" : "Not connected"}
                </Badge>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Web Chat Widget */}
      <Card>
        <CardHeader><CardTitle>Web Chat Widget</CardTitle></CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground mb-4">Add a live chat widget to your website that connects to your inbox.</p>
          {widget ? (
            <div className="space-y-3">
              <label className="block text-sm font-medium">Embed Code (paste before &lt;/body&gt;)</label>
              <div className="rounded-lg bg-muted p-3 text-xs font-mono break-all">{widget.embed_code}</div>
              <Button size="sm" variant="outline" onClick={() => navigator.clipboard.writeText(widget.embed_code)}>Copy Code</Button>
            </div>
          ) : (
            <Button onClick={handleCreateWidget} disabled={createWidget.isPending}>Generate Widget</Button>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
