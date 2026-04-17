"use client";

import { useRouter } from "next/navigation";

const SETTINGS_SECTIONS = [
  { href: "/settings/security", title: "Security", description: "Change your password" },
  { href: "/settings/team", title: "Team Members", description: "Invite and manage your team" },
  { href: "/settings/channels", title: "Channels", description: "WhatsApp, Instagram, Facebook, Web Chat" },
  { href: "/settings/tags", title: "Tags", description: "Manage contact tags and colors" },
  { href: "/settings/billing", title: "Billing & Subscription", description: "Plans, invoices, and payments" },
  { href: "/settings/compliance", title: "Compliance & Data", description: "Data residency, audit logs, GDPR" },
  { href: "/settings/export", title: "Data Export", description: "Export contacts, conversations, and deals" },
];

export default function SettingsPage() {
  const router = useRouter();

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold mb-2">Settings</h1>
      <p className="text-sm text-muted-foreground mb-6">Manage your account and company settings</p>

      <div className="space-y-3">
        {SETTINGS_SECTIONS.map((section) => (
          <button
            key={section.href}
            onClick={() => router.push(section.href)}
            className="w-full text-start rounded-lg border bg-card p-4 hover:bg-muted/30 transition-colors"
          >
            <h3 className="font-medium">{section.title}</h3>
            <p className="text-sm text-muted-foreground mt-1">{section.description}</p>
          </button>
        ))}
      </div>
    </div>
  );
}
