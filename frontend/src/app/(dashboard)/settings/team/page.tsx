"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

interface TeamMember {
  id: string; email: string; first_name: string; last_name: string;
  is_active: boolean; is_online: boolean; roles: string[]; created_at: string;
}

export default function TeamPage() {
  const qc = useQueryClient();
  const { data: members, isLoading } = useQuery({
    queryKey: ["team"],
    queryFn: async () => (await apiClient.get<TeamMember[]>("/users")).data,
  });
  const inviteUser = useMutation({
    mutationFn: async (data: { email: string; first_name: string; last_name: string; role: string }) =>
      (await apiClient.post("/users/invite", data)).data,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["team"] }); setShowInvite(false); },
  });
  const deactivate = useMutation({
    mutationFn: async (id: string) => (await apiClient.delete(`/users/${id}`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["team"] }),
  });

  const [showInvite, setShowInvite] = useState(false);
  const [form, setForm] = useState({ email: "", first_name: "", last_name: "", role: "agent" });

  return (
    <div className="max-w-3xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Team Members</h1>
          <p className="text-sm text-muted-foreground mt-1">{members?.length ?? 0} members</p>
        </div>
        <Button onClick={() => setShowInvite(true)}>+ Invite Member</Button>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12"><div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" /></div>
      ) : (
        <div className="rounded-lg border bg-card divide-y">
          {members?.map((m) => (
            <div key={m.id} className="flex items-center justify-between p-4">
              <div className="flex items-center gap-3">
                <div className="relative">
                  <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center text-sm font-bold text-primary">
                    {m.first_name[0]}{m.last_name?.[0] ?? ""}
                  </div>
                  <span className={cn("absolute bottom-0 right-0 h-3 w-3 rounded-full border-2 border-card", m.is_online ? "bg-green-500" : "bg-gray-300")} />
                </div>
                <div>
                  <p className="text-sm font-medium">{m.first_name} {m.last_name}</p>
                  <p className="text-xs text-muted-foreground">{m.email}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                {m.roles.map((r) => <Badge key={r} variant="outline" className="capitalize">{r}</Badge>)}
                <Badge variant={m.is_active ? "success" : "secondary"}>{m.is_active ? "Active" : "Inactive"}</Badge>
                <Button size="sm" variant="ghost" onClick={() => { if (confirm("Deactivate?")) deactivate.mutate(m.id); }}>
                  Deactivate
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showInvite && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <Card className="w-full max-w-md">
            <CardContent className="p-6 space-y-4">
              <h2 className="text-lg font-semibold">Invite Team Member</h2>
              <div className="grid grid-cols-2 gap-3">
                <div><label className="text-xs font-medium">First Name</label>
                  <Input value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} /></div>
                <div><label className="text-xs font-medium">Last Name</label>
                  <Input value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} /></div>
              </div>
              <div><label className="text-xs font-medium">Email</label>
                <Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
              <div><label className="text-xs font-medium">Role</label>
                <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}
                  className="flex h-9 w-full rounded-lg border border-input bg-background px-3 py-1 text-sm">
                  <option value="agent">Agent</option>
                  <option value="manager">Manager</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div className="flex justify-end gap-3">
                <Button variant="outline" onClick={() => setShowInvite(false)}>Cancel</Button>
                <Button onClick={() => inviteUser.mutate(form)} disabled={!form.email || !form.first_name || inviteUser.isPending}>
                  {inviteUser.isPending ? "Inviting..." : "Send Invite"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
