"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import {
  ArrowLeft, MessageSquare, CheckCircle2, XCircle, AlertCircle,
  Eye, EyeOff, ExternalLink,
} from "lucide-react";

type WhatsAppConfig = {
  connected: boolean;
  phone_number_id: string | null;
  business_account_id: string | null;
  has_token: boolean;
};

type VerifyResponse = {
  ok: boolean;
  phone_number_id: string;
  display_phone_number: string | null;
  verified_name: string | null;
  quality_rating: string | null;
  error: string | null;
};

export default function WhatsAppConnectPage() {
  const qc = useQueryClient();

  const { data: config, isLoading } = useQuery<WhatsAppConfig>({
    queryKey: ["channels", "whatsapp"],
    queryFn: async () => (await apiClient.get("/channels/whatsapp")).data,
  });

  const [phoneNumberId, setPhoneNumberId] = useState("");
  const [businessAccountId, setBusinessAccountId] = useState("");
  const [accessToken, setAccessToken] = useState("");
  const [showToken, setShowToken] = useState(false);
  const [saveMessage, setSaveMessage] = useState<
    { kind: "ok" | "error"; text: string } | null
  >(null);
  const [verifyResult, setVerifyResult] = useState<VerifyResponse | null>(null);

  const save = useMutation({
    mutationFn: async () =>
      apiClient.patch("/channels/whatsapp", {
        phone_number_id: phoneNumberId,
        business_account_id: businessAccountId || null,
        access_token: accessToken,
      }),
    onSuccess: () => {
      setSaveMessage({ kind: "ok", text: "Credentials saved. Click 'Verify connection' to confirm Meta accepts them." });
      setAccessToken("");
      qc.invalidateQueries({ queryKey: ["channels", "whatsapp"] });
    },
    onError: (err: unknown) => {
      // @ts-expect-error axios error shape
      const msg = err?.response?.data?.detail || err?.response?.data?.title || "Save failed";
      setSaveMessage({ kind: "error", text: String(msg) });
    },
  });

  const verify = useMutation({
    mutationFn: async () => (await apiClient.post("/channels/whatsapp/verify")).data as VerifyResponse,
    onSuccess: (data) => setVerifyResult(data),
    onError: (err: unknown) => {
      setVerifyResult({
        ok: false,
        phone_number_id: "",
        display_phone_number: null,
        verified_name: null,
        quality_rating: null,
        // @ts-expect-error axios error shape
        error: err?.response?.data?.detail || "Verify failed",
      });
    },
  });

  const disconnect = useMutation({
    mutationFn: async () => apiClient.delete("/channels/whatsapp"),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["channels", "whatsapp"] });
      setVerifyResult(null);
      setSaveMessage(null);
    },
  });

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaveMessage(null);
    setVerifyResult(null);
    if (!phoneNumberId.trim() || !accessToken.trim()) {
      setSaveMessage({ kind: "error", text: "Phone Number ID and Access Token are required." });
      return;
    }
    save.mutate();
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="max-w-2xl space-y-6">
      <Link
        href="/settings"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" /> Settings
      </Link>

      {/* Header */}
      <div className="flex items-start gap-3">
        <div className="h-12 w-12 rounded-xl bg-green-500 flex items-center justify-center text-white">
          <MessageSquare className="h-6 w-6" />
        </div>
        <div>
          <h1 className="text-2xl font-bold">Connect WhatsApp</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Paste your Meta Business credentials to enable real-time WhatsApp messaging.
          </p>
        </div>
      </div>

      {/* Current status */}
      <div className="rounded-lg border bg-card p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium">Connection status</p>
            {config?.connected ? (
              <p className="text-xs text-green-600 mt-1">
                <CheckCircle2 className="h-3 w-3 inline mr-1" />
                Connected — Phone Number ID: <code className="bg-muted px-1 rounded">{config.phone_number_id}</code>
              </p>
            ) : (
              <p className="text-xs text-muted-foreground mt-1">
                <XCircle className="h-3 w-3 inline mr-1" />
                Not connected
              </p>
            )}
          </div>
          {config?.connected && (
            <button
              onClick={() => {
                if (confirm("Disconnect WhatsApp? Incoming messages will be ignored.")) {
                  disconnect.mutate();
                }
              }}
              disabled={disconnect.isPending}
              className="text-xs text-destructive hover:underline disabled:opacity-50"
            >
              Disconnect
            </button>
          )}
        </div>
      </div>

      {/* Step-by-step instructions */}
      <details className="rounded-lg border bg-muted/20 p-4 group">
        <summary className="cursor-pointer text-sm font-medium">
          How to get these credentials from Meta (click to expand)
        </summary>
        <ol className="mt-3 space-y-2 text-sm text-muted-foreground list-decimal list-inside">
          <li>
            Open{" "}
            <a href="https://business.facebook.com" target="_blank" rel="noopener" className="text-primary inline-flex items-center gap-1">
              Meta Business Suite <ExternalLink className="h-3 w-3" />
            </a>
          </li>
          <li>Go to <strong>WhatsApp → Getting Started</strong></li>
          <li>Copy the <strong>Phone Number ID</strong> (a long number under your WhatsApp number)</li>
          <li>Copy the <strong>WhatsApp Business Account ID</strong> (optional but recommended)</li>
          <li>
            Go to <strong>Business Settings → System Users → Add</strong>, create a system user, assign your
            WhatsApp asset, then generate a <strong>Permanent Access Token</strong> with these permissions:
            <ul className="ml-5 mt-1 list-disc">
              <li><code>whatsapp_business_management</code></li>
              <li><code>whatsapp_business_messaging</code></li>
            </ul>
          </li>
          <li>Paste all three values below and click Save</li>
          <li>
            After saving, set the webhook in Meta to:{" "}
            <code className="break-all bg-muted px-1 rounded">
              {typeof window !== "undefined" ? window.location.origin.replace(/^https?:\/\//, "https://") : ""}
              /v1/webhooks/whatsapp
            </code>
          </li>
        </ol>
      </details>

      {/* Form */}
      <form onSubmit={handleSubmit} className="rounded-lg border bg-card p-6 space-y-4">
        {saveMessage && (
          <div
            className={
              saveMessage.kind === "ok"
                ? "rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-700"
                : "rounded-lg border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive"
            }
          >
            {saveMessage.text}
          </div>
        )}

        <div className="space-y-1.5">
          <label htmlFor="pnid" className="text-sm font-medium">
            Phone Number ID <span className="text-destructive">*</span>
          </label>
          <input
            id="pnid"
            type="text"
            value={phoneNumberId}
            onChange={(e) => setPhoneNumberId(e.target.value)}
            placeholder={config?.phone_number_id || "123456789012345"}
            required
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono"
          />
          <p className="text-xs text-muted-foreground">
            15-16 digit number from Meta Business Suite. This is used to identify your WhatsApp channel in incoming webhooks.
          </p>
        </div>

        <div className="space-y-1.5">
          <label htmlFor="waba" className="text-sm font-medium">
            WhatsApp Business Account ID <span className="text-muted-foreground">(optional)</span>
          </label>
          <input
            id="waba"
            type="text"
            value={businessAccountId}
            onChange={(e) => setBusinessAccountId(e.target.value)}
            placeholder={config?.business_account_id || "123456789012345"}
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono"
          />
        </div>

        <div className="space-y-1.5">
          <label htmlFor="token" className="text-sm font-medium">
            Access Token <span className="text-destructive">*</span>
          </label>
          <div className="relative">
            <input
              id="token"
              type={showToken ? "text" : "password"}
              value={accessToken}
              onChange={(e) => setAccessToken(e.target.value)}
              placeholder={config?.has_token ? "•••••••••••••••••• (token is set — paste to replace)" : "EAA..."}
              className="flex h-10 w-full rounded-md border border-input bg-background pl-3 pr-10 py-2 text-sm font-mono"
            />
            <button
              type="button"
              onClick={() => setShowToken(!showToken)}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              {showToken ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
          <p className="text-xs text-muted-foreground">
            Stored encrypted. Never returned by the API. Leave blank to keep the current token.
          </p>
        </div>

        <div className="flex gap-2 pt-2">
          <button
            type="submit"
            disabled={save.isPending}
            className="inline-flex items-center justify-center rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow hover:bg-primary/90 disabled:opacity-50"
          >
            {save.isPending ? "Saving..." : "Save credentials"}
          </button>
          {config?.connected && (
            <button
              type="button"
              onClick={() => verify.mutate()}
              disabled={verify.isPending}
              className="inline-flex items-center justify-center rounded-lg border px-4 py-2 text-sm font-medium hover:bg-muted/40 disabled:opacity-50"
            >
              {verify.isPending ? "Verifying..." : "Verify connection"}
            </button>
          )}
        </div>
      </form>

      {/* Verify result */}
      {verifyResult && (
        <div
          className={
            "rounded-lg border p-4 " +
            (verifyResult.ok
              ? "border-green-200 bg-green-50"
              : "border-destructive/40 bg-destructive/10")
          }
        >
          {verifyResult.ok ? (
            <>
              <div className="flex items-center gap-2 text-green-700 font-medium mb-2">
                <CheckCircle2 className="h-5 w-5" />
                Verified by Meta
              </div>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-xs text-muted-foreground">Phone number</p>
                  <p className="font-medium">{verifyResult.display_phone_number || "—"}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Verified name</p>
                  <p className="font-medium">{verifyResult.verified_name || "—"}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Quality rating</p>
                  <p className="font-medium">{verifyResult.quality_rating || "—"}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Phone Number ID</p>
                  <p className="font-medium font-mono text-xs">{verifyResult.phone_number_id}</p>
                </div>
              </div>
            </>
          ) : (
            <>
              <div className="flex items-center gap-2 text-destructive font-medium mb-2">
                <AlertCircle className="h-5 w-5" />
                Verification failed
              </div>
              <p className="text-sm">{verifyResult.error}</p>
            </>
          )}
        </div>
      )}
    </div>
  );
}
