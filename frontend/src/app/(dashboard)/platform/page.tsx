"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { useAuthStore } from "@/stores/auth-store";
import {
  Building2, Users, MessageSquare, Database, TrendingUp, ShieldAlert,
} from "lucide-react";

type Overview = {
  companies: { total: number; active: number; new_last_30d: number };
  users: { total: number };
  data: { contacts: number; conversations: number; messages: number };
  subscriptions: { active: number };
  generated_at: string;
};

function formatNumber(n: number): string {
  return new Intl.NumberFormat().format(n);
}

export default function PlatformDashboardPage() {
  const { user } = useAuthStore();
  const isPlatformAdmin = user?.roles?.includes("platform_admin");

  const { data, isLoading, error } = useQuery<Overview>({
    queryKey: ["platform", "overview"],
    queryFn: async () => (await apiClient.get("/platform/overview")).data,
    enabled: isPlatformAdmin,
  });

  if (!isPlatformAdmin) {
    return (
      <div className="max-w-2xl mx-auto mt-20 text-center">
        <ShieldAlert className="h-12 w-12 mx-auto text-destructive mb-4" />
        <h1 className="text-2xl font-bold mb-2">Platform Admin Only</h1>
        <p className="text-muted-foreground">
          You need the <code className="bg-muted px-1.5 py-0.5 rounded">platform_admin</code> role
          to access this page.
        </p>
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

  if (error || !data) {
    return (
      <div className="max-w-2xl mx-auto mt-20 text-center text-destructive">
        Failed to load platform overview. Check API logs.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Platform Dashboard</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Cross-tenant overview. All companies, all users, all data.
        </p>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={<Building2 className="h-5 w-5" />}
          label="Companies"
          value={formatNumber(data.companies.total)}
          sub={`${formatNumber(data.companies.active)} active`}
          tint="#10B981"
        />
        <StatCard
          icon={<TrendingUp className="h-5 w-5" />}
          label="New in 30d"
          value={formatNumber(data.companies.new_last_30d)}
          sub="companies"
          tint="#6366F1"
        />
        <StatCard
          icon={<Users className="h-5 w-5" />}
          label="Users"
          value={formatNumber(data.users.total)}
          sub="across all tenants"
          tint="#F59E0B"
        />
        <StatCard
          icon={<MessageSquare className="h-5 w-5" />}
          label="Messages"
          value={formatNumber(data.data.messages)}
          sub={`${formatNumber(data.data.conversations)} conversations`}
          tint="#EC4899"
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <StatCard
          icon={<Database className="h-5 w-5" />}
          label="Contacts"
          value={formatNumber(data.data.contacts)}
          sub="total across platform"
          tint="#3B82F6"
        />
        <StatCard
          icon={<TrendingUp className="h-5 w-5" />}
          label="Active Subscriptions"
          value={formatNumber(data.subscriptions.active)}
          sub="paid tiers"
          tint="#10B981"
        />
      </div>

      {/* Shortcuts */}
      <div className="rounded-lg border bg-card p-4">
        <h2 className="font-semibold mb-3">Quick Actions</h2>
        <div className="flex flex-wrap gap-2">
          <Link
            href="/platform/companies"
            className="inline-flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium hover:bg-muted/40 transition-colors"
          >
            <Building2 className="h-4 w-4" />
            Browse Companies
          </Link>
          <Link
            href="/platform/users"
            className="inline-flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium hover:bg-muted/40 transition-colors"
          >
            <Users className="h-4 w-4" />
            All Users
          </Link>
        </div>
      </div>

      <p className="text-xs text-muted-foreground">
        Generated {new Date(data.generated_at).toLocaleString()}
      </p>
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  sub,
  tint,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub?: string;
  tint: string;
}) {
  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="flex items-center gap-2 mb-2">
        <div
          className="h-8 w-8 rounded-lg flex items-center justify-center text-white"
          style={{ background: tint }}
        >
          {icon}
        </div>
        <span className="text-sm font-medium text-muted-foreground">{label}</span>
      </div>
      <p className="text-2xl font-bold">{value}</p>
      {sub && <p className="text-xs text-muted-foreground mt-0.5">{sub}</p>}
    </div>
  );
}
