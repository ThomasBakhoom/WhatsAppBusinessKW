"use client";

import { useState } from "react";
import { apiClient } from "@/lib/api-client";

export default function SecuritySettingsPage() {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [message, setMessage] = useState<
    { kind: "error" | "ok"; text: string } | null
  >(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setMessage(null);

    if (next.length < 8) {
      setMessage({ kind: "error", text: "New password must be at least 8 characters." });
      return;
    }
    if (next !== confirm) {
      setMessage({ kind: "error", text: "New passwords do not match." });
      return;
    }
    if (next === current) {
      setMessage({ kind: "error", text: "New password must differ from current password." });
      return;
    }

    setLoading(true);
    try {
      await apiClient.post("/auth/change-password", {
        current_password: current,
        new_password: next,
      });
      setMessage({ kind: "ok", text: "Password updated." });
      setCurrent("");
      setNext("");
      setConfirm("");
    } catch (err: unknown) {
      const fallback = "Could not change password.";
      // @ts-expect-error axios error shape
      const title = err?.response?.data?.title as string | undefined;
      // @ts-expect-error axios error shape
      const status = err?.response?.status as number | undefined;
      // 401 here usually means the current password was wrong.
      const text =
        status === 401 && !title
          ? "Current password is incorrect."
          : title || fallback;
      setMessage({ kind: "error", text });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-xl">
      <h1 className="text-2xl font-bold mb-2">Security</h1>
      <p className="text-sm text-muted-foreground mb-6">
        Update the password used to sign in to your account.
      </p>

      <form onSubmit={handleSubmit} className="rounded-lg border bg-card p-6 space-y-4">
        {message && (
          <div
            className={
              message.kind === "error"
                ? "rounded-lg border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive"
                : "rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-700"
            }
          >
            {message.text}
          </div>
        )}

        <div className="space-y-2">
          <label htmlFor="current" className="text-sm font-medium">Current password</label>
          <input
            id="current"
            type="password"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
            required
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            autoComplete="current-password"
          />
        </div>

        <div className="space-y-2">
          <label htmlFor="next" className="text-sm font-medium">New password</label>
          <input
            id="next"
            type="password"
            value={next}
            onChange={(e) => setNext(e.target.value)}
            required
            minLength={8}
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            autoComplete="new-password"
          />
        </div>

        <div className="space-y-2">
          <label htmlFor="confirm" className="text-sm font-medium">Confirm new password</label>
          <input
            id="confirm"
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            required
            minLength={8}
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            autoComplete="new-password"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="flex items-center justify-center rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow hover:bg-primary/90 disabled:opacity-50 transition-colors"
        >
          {loading ? "Updating..." : "Update password"}
        </button>
      </form>
    </div>
  );
}
