"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { formatCurrency, formatDate } from "@/lib/utils";
import { cn } from "@/lib/utils";

interface PlanItem {
  id: string;
  name: string;
  display_name: string;
  description: string | null;
  price_monthly: string;
  price_yearly: string;
  max_contacts: number;
  max_conversations_per_month: number;
  max_team_members: number;
  max_automations: number;
  has_ai_features: boolean;
  has_api_access: boolean;
}

interface SubscriptionItem {
  id: string;
  plan_id: string;
  plan: PlanItem | null;
  status: string;
  billing_cycle: string;
  current_period_start: string;
  current_period_end: string;
  cancel_at_period_end: boolean;
}

interface InvoiceItem {
  id: string;
  invoice_number: string;
  status: string;
  total: string;
  currency: string;
  period_start: string;
  period_end: string;
  paid_at: string | null;
  created_at: string;
}

export default function BillingPage() {
  const qc = useQueryClient();
  const { data: plans } = useQuery({
    queryKey: ["plans"],
    queryFn: async () => (await apiClient.get<PlanItem[]>("/payments/plans")).data,
  });
  const { data: subscription } = useQuery({
    queryKey: ["subscription"],
    queryFn: async () => (await apiClient.get<SubscriptionItem | null>("/payments/subscription")).data,
  });
  const { data: invoices } = useQuery({
    queryKey: ["invoices"],
    queryFn: async () => (await apiClient.get<InvoiceItem[]>("/payments/invoices")).data,
  });

  const subscribe = useMutation({
    mutationFn: async (data: { plan_id: string; billing_cycle: string }) => {
      return (await apiClient.post("/payments/subscription", data)).data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["subscription"] });
      qc.invalidateQueries({ queryKey: ["invoices"] });
    },
  });

  const cancel = useMutation({
    mutationFn: async () => {
      return (await apiClient.post("/payments/subscription/cancel", { cancel_at_period_end: true })).data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["subscription"] }),
  });

  const [cycle, setCycle] = useState<"monthly" | "yearly">("monthly");

  return (
    <div className="max-w-4xl">
      <h1 className="text-2xl font-bold mb-2">Billing & Subscription</h1>
      <p className="text-sm text-muted-foreground mb-6">Manage your subscription plan and billing</p>

      {/* Current Subscription */}
      {subscription && (
        <div className="rounded-lg border bg-card p-6 mb-8">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="font-semibold">Current Plan</h2>
              <p className="text-2xl font-bold mt-1">
                {subscription.plan?.display_name ?? "Unknown"}
              </p>
              <div className="flex items-center gap-3 mt-2 text-sm text-muted-foreground">
                <span className={cn(
                  "rounded-full px-2 py-0.5 text-xs font-medium",
                  subscription.status === "active" ? "bg-green-100 text-green-700" :
                  subscription.status === "cancelled" ? "bg-red-100 text-red-700" :
                  "bg-yellow-100 text-yellow-700"
                )}>
                  {subscription.status}
                </span>
                <span>{subscription.billing_cycle}</span>
                <span>Renews {formatDate(subscription.current_period_end)}</span>
              </div>
              {subscription.cancel_at_period_end && (
                <p className="text-sm text-destructive mt-2">Cancels at end of period</p>
              )}
            </div>
            {subscription.status === "active" && !subscription.cancel_at_period_end && (
              <button
                onClick={() => { if (confirm("Cancel subscription?")) cancel.mutate(); }}
                className="text-sm text-muted-foreground hover:text-destructive transition-colors"
              >
                Cancel
              </button>
            )}
          </div>
        </div>
      )}

      {/* Plans */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Plans</h2>
          <div className="flex rounded-lg border p-0.5">
            <button
              onClick={() => setCycle("monthly")}
              className={cn("rounded-md px-3 py-1 text-sm", cycle === "monthly" ? "bg-primary text-primary-foreground" : "")}
            >
              Monthly
            </button>
            <button
              onClick={() => setCycle("yearly")}
              className={cn("rounded-md px-3 py-1 text-sm", cycle === "yearly" ? "bg-primary text-primary-foreground" : "")}
            >
              Yearly
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {plans?.map((plan) => {
            const price = cycle === "yearly" ? plan.price_yearly : plan.price_monthly;
            const isCurrent = subscription?.plan_id === plan.id;

            return (
              <div key={plan.id} className={cn("rounded-lg border bg-card p-5", isCurrent && "ring-2 ring-primary")}>
                <h3 className="font-semibold">{plan.display_name}</h3>
                {plan.description && <p className="text-xs text-muted-foreground mt-1">{plan.description}</p>}
                <p className="text-2xl font-bold mt-3">
                  {formatCurrency(parseFloat(price))}
                  <span className="text-sm font-normal text-muted-foreground">/{cycle === "yearly" ? "yr" : "mo"}</span>
                </p>
                <ul className="mt-4 space-y-2 text-sm">
                  <li>{plan.max_contacts.toLocaleString()} contacts</li>
                  <li>{plan.max_conversations_per_month.toLocaleString()} conversations/mo</li>
                  <li>{plan.max_team_members} team members</li>
                  <li>{plan.max_automations} automations</li>
                  {plan.has_ai_features && <li>AI dialect engine</li>}
                  {plan.has_api_access && <li>API access</li>}
                </ul>
                <button
                  onClick={() => subscribe.mutate({ plan_id: plan.id, billing_cycle: cycle })}
                  disabled={isCurrent || subscribe.isPending}
                  className={cn(
                    "w-full mt-4 rounded-lg px-4 py-2 text-sm font-medium transition-colors",
                    isCurrent
                      ? "bg-muted text-muted-foreground cursor-default"
                      : "bg-primary text-primary-foreground hover:bg-primary/90"
                  )}
                >
                  {isCurrent ? "Current Plan" : "Select Plan"}
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* Invoices */}
      {invoices && invoices.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-4">Invoices</h2>
          <div className="rounded-lg border bg-card overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="px-4 py-3 text-start text-xs font-medium text-muted-foreground uppercase">Invoice</th>
                  <th className="px-4 py-3 text-start text-xs font-medium text-muted-foreground uppercase">Amount</th>
                  <th className="px-4 py-3 text-start text-xs font-medium text-muted-foreground uppercase">Status</th>
                  <th className="px-4 py-3 text-start text-xs font-medium text-muted-foreground uppercase">Date</th>
                </tr>
              </thead>
              <tbody>
                {invoices.map((inv) => (
                  <tr key={inv.id} className="border-b last:border-0">
                    <td className="px-4 py-3 text-sm font-medium">{inv.invoice_number}</td>
                    <td className="px-4 py-3 text-sm">{formatCurrency(parseFloat(inv.total))}</td>
                    <td className="px-4 py-3">
                      <span className={cn(
                        "rounded-full px-2 py-0.5 text-xs font-medium",
                        inv.status === "paid" ? "bg-green-100 text-green-700" :
                        inv.status === "pending" ? "bg-yellow-100 text-yellow-700" :
                        "bg-gray-100 text-gray-600"
                      )}>
                        {inv.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">{formatDate(inv.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
