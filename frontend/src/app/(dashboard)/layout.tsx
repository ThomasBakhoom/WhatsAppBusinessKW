"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { useAuthStore } from "@/stores/auth-store";
import { useWebSocket, type WSEvent } from "@/hooks/use-websocket";
import { cn } from "@/lib/utils";
import type { MeResponse } from "@/types/api";
import {
  MessageSquare, Users, BarChart3, Megaphone, Zap, Bot,
  FileText, Globe, LineChart, Settings, LogOut, Moon, Sun,
  Search, Bell, Menu, X, ChevronRight,
} from "lucide-react";

const NAV_ITEMS = [
  { href: "/inbox", label: "Inbox", icon: MessageSquare },
  { href: "/contacts", label: "Contacts", icon: Users },
  { href: "/pipeline", label: "Pipeline", icon: BarChart3 },
  { href: "/campaigns", label: "Campaigns", icon: Megaphone },
  { href: "/automations", label: "Automations", icon: Zap },
  { href: "/chatbots", label: "Chatbots", icon: Bot },
  { href: "/templates", label: "Templates", icon: FileText },
  { href: "/landing-pages", label: "Landing Pages", icon: Globe },
  { href: "/analytics", label: "Analytics", icon: LineChart },
  { href: "/settings", label: "Settings", icon: Settings },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, isLoading, setAuth, clearAuth } = useAuthStore();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [darkMode, setDarkMode] = useState(false);

  // ── Real-time updates via WebSocket ──────────────────────────────────
  // Invalidate React Query caches when the backend broadcasts an event so
  // the relevant page re-fetches automatically. This replaces polling.
  const queryClient = useQueryClient();
  const handleWSEvent = useCallback(
    (event: WSEvent) => {
      const convId = (event.data as Record<string, unknown>)?.conversation_id as string | undefined;
      switch (event.type) {
        case "message.new":
        case "message.status":
          queryClient.invalidateQueries({ queryKey: ["conversations"] });
          queryClient.invalidateQueries({ queryKey: ["messages"] });
          // Refresh the specific conversation detail if the inbox has it open
          if (convId) queryClient.invalidateQueries({ queryKey: ["conversation", convId] });
          break;
        case "conversation.updated":
          queryClient.invalidateQueries({ queryKey: ["conversations"] });
          if (convId) queryClient.invalidateQueries({ queryKey: ["conversation", convId] });
          break;
        case "contact.updated":
          queryClient.invalidateQueries({ queryKey: ["contacts"] });
          break;
        default:
          break;
      }
    },
    [queryClient],
  );
  useWebSocket({ onEvent: handleWSEvent });

  useEffect(() => {
    const saved = localStorage.getItem("theme");
    if (saved === "dark" || (!saved && window.matchMedia("(prefers-color-scheme: dark)").matches)) {
      setDarkMode(true);
      document.documentElement.classList.add("dark");
    }
  }, []);

  const toggleDarkMode = () => {
    const next = !darkMode;
    setDarkMode(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("theme", next ? "dark" : "light");
  };

  useEffect(() => {
    async function checkAuth() {
      const token = localStorage.getItem("access_token");
      if (!token) { clearAuth(); router.push("/login"); return; }
      try {
        const res = await apiClient.get<MeResponse>("/auth/me");
        const { user, company } = res.data;
        setAuth(
          { id: user.id, email: user.email, username: user.username, firstName: user.first_name, lastName: user.last_name, avatarUrl: user.avatar_url, roles: user.roles, companyId: user.company_id },
          { id: company.id, name: company.name, slug: company.slug, logoUrl: company.logo_url }
        );
      } catch { clearAuth(); router.push("/login"); }
    }
    checkAuth();
  }, []);

  useEffect(() => { setSidebarOpen(false); }, [pathname]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center" style={{ background: "#FAFBFC" }}>
        <div className="flex flex-col items-center gap-4">
          <div className="h-12 w-12 rounded-2xl flex items-center justify-center" style={{ background: "linear-gradient(135deg, #10B981, #059669)" }}>
            <span className="text-white font-bold">KW</span>
          </div>
          <div className="h-1.5 w-32 rounded-full bg-gray-100 overflow-hidden">
            <div className="h-full rounded-full animate-pulse" style={{ background: "linear-gradient(90deg, #10B981, #06B6D4)", width: "60%" }} />
          </div>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) return null;

  const user = useAuthStore.getState().user;
  const company = useAuthStore.getState().company;

  return (
    <div className="flex min-h-screen" style={{ background: "#F8FAFC" }}>
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 lg:hidden" style={{ background: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)" }} onClick={() => setSidebarOpen(false)} />
      )}

      {/* ── Sidebar ────────────────────────────────────────────── */}
      <aside
        className={cn(
          "fixed inset-y-0 start-0 z-50 w-[260px] flex flex-col transition-transform duration-300 ease-out lg:static lg:translate-x-0",
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        )}
        style={{ background: "linear-gradient(180deg, #0F172A 0%, #1E293B 100%)" }}
      >
        {/* Logo */}
        <div className="flex items-center justify-between h-16 px-5" style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
          <div className="flex items-center gap-2.5">
            <div className="h-9 w-9 rounded-xl flex items-center justify-center" style={{ background: "linear-gradient(135deg, #10B981, #059669)", boxShadow: "0 4px 12px rgba(16,185,129,0.3)" }}>
              <span className="text-white font-bold text-sm">KW</span>
            </div>
            <div className="flex flex-col">
              <span className="text-white text-sm font-semibold leading-none">{company?.name || "Growth Engine"}</span>
              <span className="text-[10px] mt-0.5" style={{ color: "#475569" }}>Enterprise CRM</span>
            </div>
          </div>
          <button onClick={() => setSidebarOpen(false)} className="lg:hidden" style={{ color: "#94A3B8" }}>
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
          {NAV_ITEMS.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className="relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-[13px] font-medium transition-all duration-200"
                style={{
                  color: isActive ? "#ffffff" : "#94A3B8",
                  background: isActive ? "rgba(255,255,255,0.08)" : "transparent",
                }}
                onMouseEnter={(e) => { if (!isActive) e.currentTarget.style.background = "rgba(255,255,255,0.04)"; e.currentTarget.style.color = "#ffffff"; }}
                onMouseLeave={(e) => { if (!isActive) { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = "#94A3B8"; } }}
              >
                {/* Active indicator bar */}
                {isActive && (
                  <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-full" style={{ background: "#10B981", boxShadow: "0 0 8px rgba(16,185,129,0.4)" }} />
                )}
                <Icon className="h-[18px] w-[18px] flex-shrink-0" style={{ color: isActive ? "#10B981" : "#64748B" }} />
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* Sidebar Footer */}
        <div className="px-3 py-3 space-y-1" style={{ borderTop: "1px solid rgba(255,255,255,0.06)" }}>
          <button
            onClick={toggleDarkMode}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-[13px] transition-all"
            style={{ color: "#94A3B8" }}
            onMouseEnter={(e) => { e.currentTarget.style.color = "#ffffff"; e.currentTarget.style.background = "rgba(255,255,255,0.04)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.color = "#94A3B8"; e.currentTarget.style.background = "transparent"; }}
          >
            {darkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            {darkMode ? "Light Mode" : "Dark Mode"}
          </button>
          <button
            onClick={() => { clearAuth(); router.push("/login"); }}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-[13px] transition-all"
            style={{ color: "#94A3B8" }}
            onMouseEnter={(e) => { e.currentTarget.style.color = "#EF4444"; e.currentTarget.style.background = "rgba(255,255,255,0.04)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.color = "#94A3B8"; e.currentTarget.style.background = "transparent"; }}
          >
            <LogOut className="h-4 w-4" />
            Sign Out
          </button>

          {/* User info */}
          <div className="flex items-center gap-3 px-3 py-3 mt-2 rounded-lg" style={{ background: "rgba(255,255,255,0.03)" }}>
            <div className="relative">
              <div className="h-9 w-9 rounded-full flex items-center justify-center text-[11px] font-bold text-white" style={{ background: "linear-gradient(135deg, #10B981, #059669)", boxShadow: "0 2px 8px rgba(16,185,129,0.2)" }}>
                {(user?.firstName?.[0] || "")}{(user?.lastName?.[0] || "")}
              </div>
              <div className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2" style={{ background: "#10B981", borderColor: "#1E293B" }} />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-white truncate">{user?.firstName} {user?.lastName}</p>
              <p className="text-[10px] truncate" style={{ color: "#64748B" }}>{user?.email}</p>
            </div>
          </div>
        </div>
      </aside>

      {/* ── Main Content ───────────────────────────────────────── */}
      <main className="flex-1 min-w-0 flex flex-col">
        {/* Top Header */}
        <header className="sticky top-0 z-30 flex items-center justify-between h-16 px-4 lg:px-6" style={{ borderBottom: "1px solid #E2E8F0", background: "rgba(248,250,252,0.85)", backdropFilter: "blur(16px)", WebkitBackdropFilter: "blur(16px)" }}>
          <div className="flex items-center gap-4">
            <button onClick={() => setSidebarOpen(true)} className="lg:hidden rounded-lg p-2 hover:bg-gray-100 transition-colors">
              <Menu className="h-5 w-5" style={{ color: "#64748B" }} />
            </button>

            {/* Breadcrumb */}
            <div className="hidden sm:flex items-center gap-1.5 text-sm">
              <span style={{ color: "#94A3B8" }}>Dashboard</span>
              <ChevronRight className="h-3.5 w-3.5" style={{ color: "#CBD5E1" }} />
              <span className="font-medium capitalize" style={{ color: "#0F172A" }}>{pathname.split("/").filter(Boolean)[0] || "Home"}</span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Search */}
            <div className="hidden md:flex items-center gap-2 rounded-xl px-3.5 py-2 text-sm w-64" style={{ background: "#F1F5F9", color: "#94A3B8" }}>
              <Search className="h-4 w-4" />
              <span className="text-[13px]">Search...</span>
              <kbd className="ml-auto text-[10px] rounded px-1.5 py-0.5 font-mono" style={{ background: "#ffffff", border: "1px solid #E2E8F0", color: "#94A3B8" }}>/</kbd>
            </div>

            {/* Notifications */}
            <button className="relative rounded-xl p-2.5 transition-colors hover:bg-gray-100">
              <Bell className="h-5 w-5" style={{ color: "#64748B" }} />
              <div className="absolute top-2 right-2 h-2 w-2 rounded-full" style={{ background: "#10B981" }} />
            </button>

            {/* User avatar */}
            <div className="h-9 w-9 rounded-full flex items-center justify-center text-[11px] font-bold text-white" style={{ background: "linear-gradient(135deg, #10B981, #059669)" }}>
              {(user?.firstName?.[0] || "")}{(user?.lastName?.[0] || "")}
            </div>
          </div>
        </header>

        {/* Page Content */}
        <div className="flex-1 p-4 lg:p-6">
          {children}
        </div>
      </main>
    </div>
  );
}
