"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { formatCurrency } from "@/lib/utils";
import { Users, MessageSquare, TrendingUp, DollarSign, Trophy, BarChart3, ArrowUpRight, ArrowDownRight } from "lucide-react";

export default function AnalyticsPage() {
  const [days, setDays] = useState(30);

  const { data: dashboard, isLoading } = useQuery({
    queryKey: ["analytics-dashboard", days],
    queryFn: async () => (await apiClient.get(`/analytics/dashboard?days=${days}`)).data,
  });
  const { data: pipelineStats } = useQuery({
    queryKey: ["analytics-pipeline"],
    queryFn: async () => (await apiClient.get("/analytics/pipeline")).data,
  });
  const { data: teamStats } = useQuery({
    queryKey: ["analytics-team", days],
    queryFn: async () => (await apiClient.get(`/analytics/team?days=${days}`)).data,
  });
  const { data: lpStats } = useQuery({
    queryKey: ["analytics-lp"],
    queryFn: async () => (await apiClient.get("/analytics/landing-pages")).data,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="h-8 w-8 rounded-full border-2 border-t-transparent animate-spin" style={{ borderColor: "#10B981", borderTopColor: "transparent" }} />
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold tracking-tight" style={{ color: "#0F172A" }}>Analytics</h1>
          <p className="text-sm mt-1" style={{ color: "#64748B" }}>Track your business performance</p>
        </div>
        <div className="flex items-center rounded-xl p-1" style={{ background: "#F1F5F9" }}>
          {[7, 30, 90].map((d) => (
            <button key={d} onClick={() => setDays(d)}
              className="rounded-lg px-4 py-1.5 text-sm font-medium transition-all"
              style={{
                background: days === d ? "#ffffff" : "transparent",
                color: days === d ? "#0F172A" : "#64748B",
                boxShadow: days === d ? "0 1px 3px rgba(0,0,0,0.08)" : "none",
              }}>
              {d}d
            </button>
          ))}
        </div>
      </div>

      {/* KPI Cards */}
      {dashboard && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <KPICard icon={Users} label="Total Contacts" value={dashboard.contacts.total} sub={`+${dashboard.contacts.new} new`}
            gradient="linear-gradient(135deg, #10B981, #059669)" iconBg="rgba(16,185,129,0.1)" iconColor="#10B981" />
          <KPICard icon={MessageSquare} label="Open Conversations" value={dashboard.conversations.open} sub={`${dashboard.conversations.total} total`}
            gradient="linear-gradient(135deg, #6366F1, #4F46E5)" iconBg="rgba(99,102,241,0.1)" iconColor="#6366F1" />
          <KPICard icon={TrendingUp} label="Messages (Period)" value={dashboard.messages.inbound + dashboard.messages.outbound}
            sub={`${dashboard.messages.inbound} in / ${dashboard.messages.outbound} out`}
            gradient="linear-gradient(135deg, #06B6D4, #0891B2)" iconBg="rgba(6,182,212,0.1)" iconColor="#06B6D4" />
          <KPICard icon={DollarSign} label="Revenue (Won)" value={formatCurrency(dashboard.deals.revenue)} sub={`${dashboard.deals.won} deals won`}
            gradient="linear-gradient(135deg, #F59E0B, #D97706)" iconBg="rgba(245,158,11,0.1)" iconColor="#F59E0B" />
        </div>
      )}

      {/* Pipeline Stats */}
      {pipelineStats && pipelineStats.stages.length > 0 && (
        <div className="rounded-2xl bg-white p-6 mb-6" style={{ border: "1px solid #E2E8F0", boxShadow: "0 1px 3px rgba(0,0,0,0.04)" }}>
          <div className="flex items-center justify-between mb-6">
            <h2 className="font-semibold text-lg" style={{ color: "#0F172A" }}>Pipeline Overview</h2>
            <div className="flex items-center gap-6">
              <div className="text-center">
                <div className="flex items-center gap-1">
                  <Trophy className="h-4 w-4" style={{ color: "#F59E0B" }} />
                  <span className="text-2xl font-bold" style={{ color: "#0F172A" }}>{pipelineStats.win_rate}%</span>
                </div>
                <p className="text-xs" style={{ color: "#94A3B8" }}>Win Rate</p>
              </div>
              <div className="text-center">
                <span className="text-2xl font-bold" style={{ color: "#0F172A" }}>{formatCurrency(pipelineStats.avg_deal_value)}</span>
                <p className="text-xs" style={{ color: "#94A3B8" }}>Avg Deal</p>
              </div>
            </div>
          </div>

          <div className="flex gap-3">
            {pipelineStats.stages.map((s: any) => {
              const maxDeals = Math.max(...pipelineStats.stages.map((st: any) => st.deal_count), 1);
              const height = Math.max((s.deal_count / maxDeals) * 100, 8);
              return (
                <div key={s.name} className="flex-1 text-center group">
                  <div className="h-24 flex items-end justify-center mb-2">
                    <div className="w-full max-w-[40px] rounded-t-lg transition-all duration-500 group-hover:opacity-80"
                      style={{ height: `${height}%`, background: s.color }} />
                  </div>
                  <p className="text-[11px] font-medium truncate" style={{ color: "#334155" }}>{s.name}</p>
                  <p className="text-[10px]" style={{ color: "#94A3B8" }}>{s.deal_count} deals</p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Team Performance */}
      {teamStats && teamStats.length > 0 && (
        <div className="rounded-2xl bg-white p-6 mb-6" style={{ border: "1px solid #E2E8F0", boxShadow: "0 1px 3px rgba(0,0,0,0.04)" }}>
          <h2 className="font-semibold text-lg mb-4" style={{ color: "#0F172A" }}>Team Performance</h2>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr style={{ borderBottom: "1px solid #F1F5F9" }}>
                  <th className="text-left text-xs font-medium py-3 px-2" style={{ color: "#94A3B8" }}>Agent</th>
                  <th className="text-center text-xs font-medium py-3 px-2" style={{ color: "#94A3B8" }}>Messages</th>
                  <th className="text-center text-xs font-medium py-3 px-2" style={{ color: "#94A3B8" }}>Conversations</th>
                  <th className="text-center text-xs font-medium py-3 px-2" style={{ color: "#94A3B8" }}>Deals Won</th>
                  <th className="text-right text-xs font-medium py-3 px-2" style={{ color: "#94A3B8" }}>Revenue</th>
                </tr>
              </thead>
              <tbody>
                {teamStats.map((agent: any) => (
                  <tr key={agent.user_id} className="group" style={{ borderBottom: "1px solid #F8FAFC" }}>
                    <td className="py-3 px-2">
                      <div className="flex items-center gap-3">
                        <div className="relative">
                          <div className="h-8 w-8 rounded-full flex items-center justify-center text-[11px] font-bold text-white"
                            style={{ background: "linear-gradient(135deg, #10B981, #059669)" }}>
                            {(agent.name || agent.email || "?")[0]}
                          </div>
                          <div className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-white"
                            style={{ background: agent.is_online ? "#10B981" : "#CBD5E1" }} />
                        </div>
                        <span className="text-sm font-medium" style={{ color: "#0F172A" }}>{agent.name || agent.email}</span>
                      </div>
                    </td>
                    <td className="text-center text-sm py-3 px-2" style={{ color: "#334155" }}>{agent.messages_sent}</td>
                    <td className="text-center text-sm py-3 px-2" style={{ color: "#334155" }}>{agent.conversations_assigned}</td>
                    <td className="text-center text-sm py-3 px-2" style={{ color: "#334155" }}>{agent.deals_won}</td>
                    <td className="text-right text-sm font-semibold py-3 px-2" style={{ color: "#0F172A" }}>{formatCurrency(agent.revenue)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Landing Pages */}
      {lpStats && lpStats.length > 0 && (
        <div className="rounded-2xl bg-white p-6" style={{ border: "1px solid #E2E8F0", boxShadow: "0 1px 3px rgba(0,0,0,0.04)" }}>
          <h2 className="font-semibold text-lg mb-4" style={{ color: "#0F172A" }}>Landing Pages</h2>
          <div className="space-y-3">
            {lpStats.map((lp: any) => (
              <div key={lp.id} className="flex items-center justify-between py-2 rounded-lg px-3 hover:bg-gray-50 transition-colors">
                <div>
                  <p className="text-sm font-medium" style={{ color: "#0F172A" }}>{lp.title}</p>
                  <p className="text-xs" style={{ color: "#94A3B8" }}>/{lp.slug}</p>
                </div>
                <div className="flex items-center gap-8 text-sm">
                  <span style={{ color: "#64748B" }}>{lp.visits} visits</span>
                  <span style={{ color: "#64748B" }}>{lp.conversions} conversions</span>
                  <span className="font-semibold" style={{ color: lp.rate > 5 ? "#10B981" : "#64748B" }}>{lp.rate}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function KPICard({ icon: Icon, label, value, sub, gradient, iconBg, iconColor }: {
  icon: any; label: string; value: string | number; sub: string;
  gradient: string; iconBg: string; iconColor: string;
}) {
  return (
    <div className="rounded-2xl bg-white p-5 transition-all hover:-translate-y-0.5"
      style={{ border: "1px solid #E2E8F0", boxShadow: "0 1px 3px rgba(0,0,0,0.04)" }}>
      <div className="flex items-start justify-between mb-4">
        <div className="h-10 w-10 rounded-xl flex items-center justify-center" style={{ background: iconBg }}>
          <Icon className="h-5 w-5" style={{ color: iconColor }} />
        </div>
        <div className="flex items-center gap-1 text-xs font-medium" style={{ color: "#10B981" }}>
          <ArrowUpRight className="h-3 w-3" />
          <span>12%</span>
        </div>
      </div>
      <div className="text-2xl font-bold" style={{ color: "#0F172A" }}>{value}</div>
      <p className="text-xs mt-1" style={{ color: "#94A3B8" }}>{label}</p>
      <p className="text-[11px] mt-0.5" style={{ color: "#64748B" }}>{sub}</p>
      <div className="mt-3 h-1 rounded-full overflow-hidden" style={{ background: "#F1F5F9" }}>
        <div className="h-full rounded-full" style={{ background: gradient, width: "65%" }} />
      </div>
    </div>
  );
}
