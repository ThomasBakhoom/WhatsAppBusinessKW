"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiClient } from "@/lib/api-client";
import { useAuthStore } from "@/stores/auth-store";
import type { TokenResponse, MeResponse } from "@/types/api";
import { Mail, Lock, ArrowRight, MessageSquare } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const { setAuth } = useAuthStore();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const loginRes = await apiClient.post<TokenResponse>("/auth/login", { email, password });
      localStorage.setItem("access_token", loginRes.data.access_token);
      localStorage.setItem("refresh_token", loginRes.data.refresh_token);
      const meRes = await apiClient.get<MeResponse>("/auth/me");
      const { user, company } = meRes.data;
      setAuth(
        { id: user.id, email: user.email, username: user.username, firstName: user.first_name, lastName: user.last_name, avatarUrl: user.avatar_url, roles: user.roles, companyId: user.company_id },
        { id: company.id, name: company.name, slug: company.slug, logoUrl: company.logo_url }
      );
      router.push("/inbox");
    } catch (err: any) {
      setError(err.response?.data?.title || "Login failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen">
      {/* Left side - gradient illustration */}
      <div className="hidden lg:flex lg:w-1/2 mesh-gradient relative items-center justify-center">
        <div className="absolute top-20 left-10 w-72 h-72 bg-emerald-500/10 rounded-full blur-3xl animate-float" />
        <div className="absolute bottom-20 right-10 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl animate-float" style={{ animationDelay: "2s" }} />

        <div className="relative z-10 text-center px-12 animate-fade-in">
          <div className="inline-flex items-center justify-center h-16 w-16 rounded-2xl gradient-primary shadow-2xl shadow-emerald-500/30 mb-8">
            <MessageSquare className="h-8 w-8 text-white" />
          </div>
          <h2 className="text-3xl font-bold text-white mb-4">Kuwait WhatsApp<br />Growth Engine</h2>
          <p className="text-slate-400 text-lg max-w-sm">
            The enterprise CRM platform built for Kuwait with AI-powered dialect understanding
          </p>

          <div className="mt-12 grid grid-cols-3 gap-6 max-w-xs mx-auto">
            {[
              { n: "145", l: "APIs" },
              { n: "42", l: "Tables" },
              { n: "31", l: "Modules" },
            ].map((s) => (
              <div key={s.l} className="text-center">
                <div className="text-xl font-bold text-white">{s.n}</div>
                <div className="text-[11px] text-slate-500">{s.l}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right side - form */}
      <div className="flex-1 flex items-center justify-center p-6 lg:p-12 bg-background">
        <div className="w-full max-w-[400px] animate-slide-up">
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-2.5 mb-10">
            <div className="h-9 w-9 rounded-xl gradient-primary flex items-center justify-center shadow-lg shadow-emerald-500/20">
              <span className="text-white font-bold text-sm">KW</span>
            </div>
            <span className="font-semibold text-lg">Growth Engine</span>
          </div>

          <div className="mb-8">
            <h1 className="text-2xl font-bold tracking-tight">Welcome back</h1>
            <p className="mt-2 text-sm text-muted-foreground">Sign in to your account to continue</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            {error && (
              <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-3.5 text-sm text-destructive flex items-center gap-2 animate-scale-in">
                <div className="h-1.5 w-1.5 rounded-full bg-destructive flex-shrink-0" />
                {error}
              </div>
            )}

            <div className="space-y-1.5">
              <label htmlFor="email" className="text-sm font-medium">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <input
                  id="email" type="email" value={email}
                  onChange={(e) => setEmail(e.target.value)} required
                  className="flex h-11 w-full rounded-xl border border-input bg-background pl-10 pr-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:border-primary transition-all"
                  placeholder="you@company.com"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label htmlFor="password" className="text-sm font-medium">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <input
                  id="password" type="password" value={password}
                  onChange={(e) => setPassword(e.target.value)} required
                  className="flex h-11 w-full rounded-xl border border-input bg-background pl-10 pr-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:border-primary transition-all"
                  placeholder="Enter your password"
                />
              </div>
            </div>

            <div className="flex items-center justify-between">
              <Link href="/forgot-password" className="text-sm text-primary hover:text-primary/80 transition-colors">
                Forgot password?
              </Link>
            </div>

            <button
              type="submit" disabled={loading}
              className="flex w-full items-center justify-center gap-2 rounded-xl gradient-primary h-11 text-sm font-semibold text-white shadow-lg shadow-emerald-500/20 hover:shadow-emerald-500/30 disabled:opacity-50 transition-all hover:scale-[1.01] active:scale-[0.99]"
            >
              {loading ? (
                <div className="h-4 w-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
              ) : (
                <>Sign In <ArrowRight className="h-4 w-4" /></>
              )}
            </button>
          </form>

          <p className="text-center text-sm text-muted-foreground mt-8">
            Don&apos;t have an account?{" "}
            <Link href="/register" className="text-primary font-medium hover:text-primary/80 transition-colors">
              Get started free
            </Link>
          </p>
        </div>
      </div>
    </main>
  );
}
