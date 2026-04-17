"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiClient } from "@/lib/api-client";
import { useAuthStore } from "@/stores/auth-store";
import type { RegisterResponse } from "@/types/api";
import { Building2, User, Mail, AtSign, Lock, ArrowRight, Sparkles } from "lucide-react";

export default function RegisterPage() {
  const router = useRouter();
  const { setAuth } = useAuthStore();
  const [form, setForm] = useState({ company_name: "", first_name: "", last_name: "", email: "", username: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function u(field: string, value: string) { setForm((p) => ({ ...p, [field]: value })); }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await apiClient.post<RegisterResponse>("/auth/register", form);
      const { user, tokens } = res.data;
      localStorage.setItem("access_token", tokens.access_token);
      localStorage.setItem("refresh_token", tokens.refresh_token);
      setAuth(
        { id: user.id, email: user.email, username: user.username, firstName: user.first_name, lastName: user.last_name, avatarUrl: user.avatar_url, roles: user.roles, companyId: user.company_id },
        { id: user.company_id, name: form.company_name, slug: "", logoUrl: null }
      );
      router.push("/inbox");
    } catch (err: any) {
      setError(err.response?.data?.title || "Registration failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  const inputClass = "flex h-11 w-full rounded-xl border border-gray-200 bg-white pl-10 pr-3 py-2 text-sm placeholder:text-gray-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/30 focus-visible:border-emerald-500 transition-all";

  return (
    <main className="flex min-h-screen">
      {/* Left - Gradient branding */}
      <div className="hidden lg:flex lg:w-[45%] relative items-center justify-center overflow-hidden"
        style={{ background: "linear-gradient(135deg, #0F172A 0%, #1E293B 50%, #0F172A 100%)" }}>
        <div className="absolute top-20 left-10 w-72 h-72 rounded-full blur-3xl" style={{ background: "rgba(16,185,129,0.12)" }} />
        <div className="absolute bottom-20 right-10 w-64 h-64 rounded-full blur-3xl" style={{ background: "rgba(99,102,241,0.1)" }} />

        <div className="relative z-10 text-center px-12">
          <div className="inline-flex items-center justify-center h-16 w-16 rounded-2xl mb-8"
            style={{ background: "linear-gradient(135deg, #10B981, #059669)", boxShadow: "0 8px 24px rgba(16,185,129,0.3)" }}>
            <Sparkles className="h-8 w-8 text-white" />
          </div>
          <h2 className="text-3xl font-bold text-white mb-4">Start Growing<br />Your Business</h2>
          <p className="text-lg max-w-sm" style={{ color: "#94A3B8" }}>
            Enterprise WhatsApp CRM with Kuwaiti dialect AI, K-Net payments, and shipping integration
          </p>

          <div className="mt-12 flex flex-col gap-4 max-w-xs mx-auto text-left">
            {[
              "Kuwaiti dialect AI with 133+ markers",
              "K-Net, Visa & Mastercard via Tap",
              "Aramex shipping with WhatsApp tracking",
              "CITRA-compliant GCC data residency",
            ].map((f) => (
              <div key={f} className="flex items-center gap-3">
                <div className="h-5 w-5 rounded-full flex items-center justify-center flex-shrink-0" style={{ background: "rgba(16,185,129,0.15)" }}>
                  <div className="h-1.5 w-1.5 rounded-full" style={{ background: "#10B981" }} />
                </div>
                <span className="text-sm" style={{ color: "#CBD5E1" }}>{f}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right - Form */}
      <div className="flex-1 flex items-center justify-center p-6 lg:p-12" style={{ background: "#FAFBFC" }}>
        <div className="w-full max-w-[440px]">
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-2.5 mb-8">
            <div className="h-9 w-9 rounded-xl flex items-center justify-center" style={{ background: "linear-gradient(135deg, #10B981, #059669)", boxShadow: "0 4px 12px rgba(16,185,129,0.2)" }}>
              <span className="text-white font-bold text-sm">KW</span>
            </div>
            <span className="font-semibold text-lg" style={{ color: "#0F172A" }}>Growth Engine</span>
          </div>

          <div className="mb-8">
            <h1 className="text-2xl font-bold tracking-tight" style={{ color: "#0F172A" }}>Create your account</h1>
            <p className="mt-2 text-sm" style={{ color: "#64748B" }}>Start your free trial - no credit card required</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="rounded-xl p-3.5 text-sm flex items-center gap-2" style={{ background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.15)", color: "#EF4444" }}>
                <div className="h-1.5 w-1.5 rounded-full flex-shrink-0" style={{ background: "#EF4444" }} />
                {error}
              </div>
            )}

            <div className="space-y-1.5">
              <label className="text-sm font-medium" style={{ color: "#0F172A" }}>Company Name</label>
              <div className="relative">
                <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4" style={{ color: "#94A3B8" }} />
                <input type="text" value={form.company_name} onChange={(e) => u("company_name", e.target.value)} required className={inputClass} placeholder="Your Company" />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-sm font-medium" style={{ color: "#0F172A" }}>First Name</label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4" style={{ color: "#94A3B8" }} />
                  <input type="text" value={form.first_name} onChange={(e) => u("first_name", e.target.value)} required className={inputClass} />
                </div>
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium" style={{ color: "#0F172A" }}>Last Name</label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4" style={{ color: "#94A3B8" }} />
                  <input type="text" value={form.last_name} onChange={(e) => u("last_name", e.target.value)} required className={inputClass} />
                </div>
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium" style={{ color: "#0F172A" }}>Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4" style={{ color: "#94A3B8" }} />
                <input type="email" value={form.email} onChange={(e) => u("email", e.target.value)} required className={inputClass} placeholder="you@company.com" />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium" style={{ color: "#0F172A" }}>Username</label>
              <div className="relative">
                <AtSign className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4" style={{ color: "#94A3B8" }} />
                <input type="text" value={form.username} onChange={(e) => u("username", e.target.value)} required className={inputClass} />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium" style={{ color: "#0F172A" }}>Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4" style={{ color: "#94A3B8" }} />
                <input type="password" value={form.password} onChange={(e) => u("password", e.target.value)} required minLength={8} className={inputClass} placeholder="Minimum 8 characters" />
              </div>
            </div>

            <button type="submit" disabled={loading}
              className="flex w-full items-center justify-center gap-2 rounded-xl h-11 text-sm font-semibold text-white disabled:opacity-50 transition-all hover:scale-[1.01] active:scale-[0.99]"
              style={{ background: "linear-gradient(135deg, #10B981, #059669)", boxShadow: "0 4px 14px rgba(16,185,129,0.25)" }}>
              {loading ? (
                <div className="h-4 w-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
              ) : (
                <>Create Account <ArrowRight className="h-4 w-4" /></>
              )}
            </button>

            <p className="text-center text-xs" style={{ color: "#94A3B8" }}>
              By creating an account, you agree to our Terms of Service
            </p>
          </form>

          <p className="text-center text-sm mt-8" style={{ color: "#64748B" }}>
            Already have an account?{" "}
            <Link href="/login" className="font-medium transition-colors" style={{ color: "#10B981" }}>
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </main>
  );
}
