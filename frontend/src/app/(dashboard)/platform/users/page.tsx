"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { useAuthStore } from "@/stores/auth-store";
import { Search, ShieldAlert, User as UserIcon } from "lucide-react";

type UserRow = {
  id: string;
  email: string;
  username: string;
  full_name: string;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
  company: { id: string; name: string; slug: string };
};

type UsersResponse = {
  data: UserRow[];
  meta: { total: number; limit: number; offset: number; has_more: boolean };
};

export default function PlatformUsersPage() {
  const { user } = useAuthStore();
  const isPlatformAdmin = user?.roles?.includes("platform_admin");
  const [search, setSearch] = useState("");

  const { data, isLoading } = useQuery<UsersResponse>({
    queryKey: ["platform", "users", search],
    queryFn: async () => {
      const params = new URLSearchParams({ limit: "100" });
      if (search) params.set("search", search);
      return (await apiClient.get(`/platform/users?${params}`)).data;
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
        <h1 className="text-2xl font-bold">All Users</h1>
        <p className="text-sm text-muted-foreground mt-1">
          {data?.meta.total ?? 0} users across all tenants
        </p>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <input
          type="text"
          placeholder="Search email, username, or name..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full h-10 rounded-lg border border-input bg-background pl-10 pr-3 py-2 text-sm"
        />
      </div>

      <div className="rounded-lg border bg-card overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center">
            <div className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          </div>
        ) : !data || data.data.length === 0 ? (
          <div className="p-12 text-center text-muted-foreground text-sm">
            No users found.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-muted/30 text-xs uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="text-left p-3 font-medium">User</th>
                <th className="text-left p-3 font-medium">Company</th>
                <th className="text-left p-3 font-medium">Status</th>
                <th className="text-left p-3 font-medium">Last Login</th>
                <th className="text-left p-3 font-medium">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {data.data.map((u) => (
                <tr key={u.id} className="hover:bg-muted/20 transition-colors">
                  <td className="p-3">
                    <div className="flex items-center gap-2">
                      <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                        <UserIcon className="h-4 w-4 text-primary" />
                      </div>
                      <div>
                        <p className="font-medium">{u.full_name || u.username}</p>
                        <p className="text-xs text-muted-foreground">{u.email}</p>
                      </div>
                    </div>
                  </td>
                  <td className="p-3">
                    <Link
                      href={`/platform/companies/${u.company.id}`}
                      className="text-primary hover:underline text-xs"
                    >
                      {u.company.name}
                    </Link>
                  </td>
                  <td className="p-3">
                    {u.is_active ? (
                      <span className="rounded-full bg-green-100 text-green-700 px-2 py-0.5 text-xs">
                        Active
                      </span>
                    ) : (
                      <span className="rounded-full bg-gray-100 text-gray-600 px-2 py-0.5 text-xs">
                        Inactive
                      </span>
                    )}
                  </td>
                  <td className="p-3 text-xs text-muted-foreground">
                    {u.last_login_at
                      ? new Date(u.last_login_at).toLocaleString()
                      : "Never"}
                  </td>
                  <td className="p-3 text-xs text-muted-foreground">
                    {new Date(u.created_at).toLocaleDateString()}
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
