"use client";

import Link from "next/link";
import { use, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { useAuthStore } from "@/stores/auth-store";
import {
  ArrowLeft, Users, Database, MessageSquare, Building2,
  ShieldAlert, Pause, Play, UserCog,
} from "lucide-react";

type CompanyDetail = {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
  whatsapp_connected: boolean;
  created_at: string;
  stats: { users: number; contacts: number; conversations: number; messages: number };
  subscription: {
    id: string; status: string; billing_cycle: string; current_period_end: string | null;
  } | null;
  recent_audit: Array<{
    action: string; description: string; user_email: string | null;
    ip_address: string | null; created_at: string;
  }>;
};

export default function CompanyDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const qc = useQueryClient();
  const { user } = useAuthStore();
  const isPlatformAdmin = user?.roles?.includes("platform_admin");
  const [impersonating, setImpersonating] = useState(false);

  const { data, isLoading } = useQuery<CompanyDetail>({
    queryKey: ["platform", "company", id],
    queryFn: async () => (await apiClient.get(`/platform/companies/${id}`)).data,
    enabled: isPlatformAdmin,
  });

  const suspend = useMutation({
    mutationFn: async () => apiClient.post(`/platform/companies/${id}/suspend`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["platform"] }),
  });
  const activate = useMutation({
    mutationFn: async () => apiClient.post(`/platform/companies/${id}/activate`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["platform"] }),
  });

  async function handleImpersonate() {
    setImpersonating(true);
    try {
      const res = await apiClient.post(`/platform/impersonate/${id}`);
      const { access_token, refresh_token, impersonating: target } = res.data;
      // Save the admin's current tokens so we can return later (optional).
      const adminAccess = localStorage.getItem("access_token");
      const adminRefresh = localStorage.getItem("refresh_token");
      if (adminAccess && adminRefresh) {
        localStorage.setItem("impersonation_origin_access", adminAccess);
        localStorage.setItem("impersonation_origin_refresh", adminRefresh);
        localStorage.setItem("impersonation_target_name", target.company_name);
      }
      localStorage.setItem("access_token", access_token);
      localStorage.setItem("refresh_token", refresh_token);
      // Kick back to inbox under the impersonated tenant
      window.location.href = "/inbox";
    } catch (err) {
      // @ts-expect-error axios error shape
      alert("Impersonation failed: " + (err?.response?.data?.detail || "unknown"));
    } finally {
      setImpersonating(false);
    }
  }

  if (!isPlatformAdmin) {
    return (
      <div className="max-w-2xl mx-auto mt-20 text-center">
        <ShieldAlert className="h-12 w-12 mx-auto text-destructive mb-4" />
        <h1 className="text-2xl font-bold">Platform Admin Only</h1>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!data) {
    return <div className="text-center text-muted-foreground mt-20">Company not found</div>;
  }

  return (
    <div className="space-y-6 max-w-5xl">
      <Link
        href="/platform/companies"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" /> All companies
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center">
            <Building2 className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">{data.name}</h1>
            <p className="text-sm text-muted-foreground">
              {data.slug} · Created {new Date(data.created_at).toLocaleDateString()}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          {data.is_active ? (
            <button
              onClick={() => {
                if (confirm(`Suspend "${data.name}"? Its users will see "Account suspended" on login.`)) {
                  suspend.mutate();
                }
              }}
              disabled={suspend.isPending}
              className="inline-flex items-center gap-1 rounded-lg border border-destructive/30 bg-destructive/10 text-destructive px-3 py-1.5 text-sm font-medium hover:bg-destructive/20 transition-colors disabled:opacity-50"
            >
              <Pause className="h-4 w-4" /> Suspend
            </button>
          ) : (
            <button
              onClick={() => activate.mutate()}
              disabled={activate.isPending}
              className="inline-flex items-center gap-1 rounded-lg border border-green-600/30 bg-green-600/10 text-green-700 px-3 py-1.5 text-sm font-medium hover:bg-green-600/20 transition-colors disabled:opacity-50"
            >
              <Play className="h-4 w-4" /> Activate
            </button>
          )}
          <button
            onClick={handleImpersonate}
            disabled={impersonating}
            className="inline-flex items-center gap-1 rounded-lg bg-primary text-primary-foreground px-3 py-1.5 text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            <UserCog className="h-4 w-4" />
            {impersonating ? "Opening..." : "Impersonate"}
          </button>
        </div>
      </div>

      {/* Status badge */}
      <div>
        {data.is_active ? (
          <span className="rounded-full bg-green-100 text-green-700 px-2 py-0.5 text-xs font-medium">
            Active
          </span>
        ) : (
          <span className="rounded-full bg-red-100 text-red-700 px-2 py-0.5 text-xs font-medium">
            Suspended
          </span>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MiniStat icon={<Users className="h-4 w-4" />} label="Users" value={data.stats.users} />
        <MiniStat icon={<Database className="h-4 w-4" />} label="Contacts" value={data.stats.contacts} />
        <MiniStat icon={<MessageSquare className="h-4 w-4" />} label="Conversations" value={data.stats.conversations} />
        <MiniStat icon={<MessageSquare className="h-4 w-4" />} label="Messages" value={data.stats.messages} />
      </div>

      {/* Subscription */}
      {data.subscription && (
        <div className="rounded-lg border bg-card p-4">
          <h2 className="font-semibold mb-2 text-sm">Subscription</h2>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <p className="text-xs text-muted-foreground">Status</p>
              <p className="font-medium capitalize">{data.subscription.status}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Billing</p>
              <p className="font-medium capitalize">{data.subscription.billing_cycle}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Period end</p>
              <p className="font-medium">
                {data.subscription.current_period_end
                  ? new Date(data.subscription.current_period_end).toLocaleDateString()
                  : "—"}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Recent audit */}
      <div className="rounded-lg border bg-card">
        <div className="p-4 border-b">
          <h2 className="font-semibold text-sm">Recent Activity</h2>
        </div>
        {data.recent_audit.length === 0 ? (
          <div className="p-8 text-center text-sm text-muted-foreground">No audit entries yet</div>
        ) : (
          <div className="divide-y">
            {data.recent_audit.map((a, i) => (
              <div key={i} className="p-3 text-sm">
                <p className="font-mono text-xs text-muted-foreground">{a.action}</p>
                <p>{a.description}</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {a.user_email || "—"} · {a.ip_address || "—"} ·{" "}
                  {new Date(a.created_at).toLocaleString()}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function MiniStat({
  icon, label, value,
}: { icon: React.ReactNode; label: string; value: number }) {
  return (
    <div className="rounded-lg border bg-card p-3">
      <div className="flex items-center gap-1 text-xs text-muted-foreground">
        {icon} {label}
      </div>
      <p className="text-xl font-bold mt-1">{new Intl.NumberFormat().format(value)}</p>
    </div>
  );
}
