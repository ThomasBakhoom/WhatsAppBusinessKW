"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { useAuthStore } from "@/stores/auth-store";
import { Search, ShieldAlert, Building2, CheckCircle2, XCircle } from "lucide-react";

type Company = {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
  created_at: string;
  whatsapp_connected: boolean;
};

type CompaniesResponse = {
  data: Company[];
  meta: { total: number; limit: number; offset: number; has_more: boolean };
};

export default function PlatformCompaniesPage() {
  const { user } = useAuthStore();
  const isPlatformAdmin = user?.roles?.includes("platform_admin");
  const [search, setSearch] = useState("");
  const [activeFilter, setActiveFilter] = useState<"all" | "active" | "suspended">("all");

  const { data, isLoading } = useQuery<CompaniesResponse>({
    queryKey: ["platform", "companies", search, activeFilter],
    queryFn: async () => {
      const params = new URLSearchParams({ limit: "100" });
      if (search) params.set("search", search);
      if (activeFilter === "active") params.set("is_active", "true");
      if (activeFilter === "suspended") params.set("is_active", "false");
      return (await apiClient.get(`/platform/companies?${params}`)).data;
    },
    enabled: isPlatformAdmin,
  });

  if (!isPlatformAdmin) {
    return (
      <div className="max-w-2xl mx-auto mt-20 text-center">
        <ShieldAlert className="h-12 w-12 mx-auto text-destructive mb-4" />
        <h1 className="text-2xl font-bold">Platform Admin Only</h1>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">All Companies</h1>
        <p className="text-sm text-muted-foreground mt-1">
          {data?.meta.total ?? 0} companies on the platform
        </p>
      </div>

      {/* Controls */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-[240px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search name or slug..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full h-10 rounded-lg border border-input bg-background pl-10 pr-3 py-2 text-sm"
          />
        </div>
        <div className="flex gap-1.5 rounded-lg bg-muted/40 p-1">
          {(["all", "active", "suspended"] as const).map((s) => (
            <button
              key={s}
              onClick={() => setActiveFilter(s)}
              className={
                "rounded px-3 py-1.5 text-xs font-medium transition-colors capitalize " +
                (activeFilter === s
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground")
              }
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="rounded-lg border bg-card overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center">
            <div className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          </div>
        ) : !data || data.data.length === 0 ? (
          <div className="p-12 text-center text-muted-foreground text-sm">
            No companies found.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-muted/30 text-xs uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="text-left p-3 font-medium">Company</th>
                <th className="text-left p-3 font-medium">Status</th>
                <th className="text-left p-3 font-medium">WhatsApp</th>
                <th className="text-left p-3 font-medium">Created</th>
                <th className="text-right p-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {data.data.map((c) => (
                <tr key={c.id} className="hover:bg-muted/20 transition-colors">
                  <td className="p-3">
                    <div className="flex items-center gap-2">
                      <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center">
                        <Building2 className="h-4 w-4 text-primary" />
                      </div>
                      <div>
                        <p className="font-medium">{c.name}</p>
                        <p className="text-xs text-muted-foreground">{c.slug}</p>
                      </div>
                    </div>
                  </td>
                  <td className="p-3">
                    {c.is_active ? (
                      <span className="inline-flex items-center gap-1 rounded-full bg-green-100 text-green-700 px-2 py-0.5 text-xs">
                        <CheckCircle2 className="h-3 w-3" /> Active
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 rounded-full bg-red-100 text-red-700 px-2 py-0.5 text-xs">
                        <XCircle className="h-3 w-3" /> Suspended
                      </span>
                    )}
                  </td>
                  <td className="p-3">
                    {c.whatsapp_connected ? (
                      <span className="text-xs text-green-600">Connected</span>
                    ) : (
                      <span className="text-xs text-muted-foreground">Not set</span>
                    )}
                  </td>
                  <td className="p-3 text-xs text-muted-foreground">
                    {new Date(c.created_at).toLocaleDateString()}
                  </td>
                  <td className="p-3 text-right">
                    <Link
                      href={`/platform/companies/${c.id}`}
                      className="text-primary hover:underline text-xs font-medium"
                    >
                      View →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
