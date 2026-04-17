import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen">
      {/* ── Hero Section ─────────────────────────────────────────── */}
      <section className="relative min-h-screen flex items-center justify-center overflow-hidden mesh-gradient">
        {/* Floating orbs */}
        <div className="absolute top-20 left-10 w-72 h-72 bg-emerald-500/10 rounded-full blur-3xl animate-float" />
        <div className="absolute bottom-20 right-10 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl animate-float" style={{ animationDelay: "1.5s" }} />

        {/* Nav */}
        <nav className="absolute top-0 left-0 right-0 z-20 flex items-center justify-between px-6 lg:px-12 py-5">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg gradient-primary flex items-center justify-center">
              <span className="text-white font-bold text-sm">KW</span>
            </div>
            <span className="text-white font-semibold text-lg hidden sm:inline">Growth Engine</span>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/login" className="text-slate-300 hover:text-white text-sm font-medium transition-colors">
              Sign In
            </Link>
            <Link href="/register" className="rounded-lg gradient-primary px-5 py-2 text-sm font-medium text-white shadow-lg shadow-emerald-500/20 hover:shadow-emerald-500/30 transition-all hover:scale-[1.02]">
              Get Started Free
            </Link>
          </div>
        </nav>

        {/* Hero Content */}
        <div className="relative z-10 text-center max-w-4xl mx-auto px-6 animate-fade-in">
          <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-1.5 text-sm text-slate-300 mb-8 backdrop-blur-sm">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse-soft" />
            Built for Kuwait &middot; Enterprise Ready
          </div>

          <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold text-white leading-[1.1] mb-6 tracking-tight">
            The WhatsApp CRM<br />
            <span className="gradient-text">Kuwait Deserves</span>
          </h1>

          <p className="text-lg sm:text-xl text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed">
            Enterprise-grade WhatsApp automation with Kuwaiti dialect AI,
            K-Net payments, Aramex shipping, and real-time analytics.
            All in one platform.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-16">
            <Link href="/register" className="rounded-xl gradient-primary px-8 py-3.5 text-base font-semibold text-white shadow-lg shadow-emerald-500/25 hover:shadow-emerald-500/40 transition-all hover:scale-[1.02] w-full sm:w-auto">
              Start Free Trial
            </Link>
            <Link href="/login" className="rounded-xl border border-white/15 bg-white/5 backdrop-blur-sm px-8 py-3.5 text-base font-semibold text-white hover:bg-white/10 transition-all w-full sm:w-auto">
              View Live Demo
            </Link>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-6 max-w-2xl mx-auto stagger-children">
            {[
              { value: "145", label: "API Endpoints" },
              { value: "42", label: "Database Tables" },
              { value: "31", label: "Modules" },
              { value: "133", label: "Dialect Markers" },
            ].map((s) => (
              <div key={s.label} className="text-center">
                <div className="text-2xl sm:text-3xl font-bold text-white">{s.value}</div>
                <div className="text-xs sm:text-sm text-slate-500 mt-1">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Features Section ─────────────────────────────────────── */}
      <section className="py-24 px-6 lg:px-12 bg-background">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">Everything you need to grow</h2>
            <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
              A complete enterprise platform built specifically for the Kuwait market
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 stagger-children">
            {[
              { icon: "💬", title: "WhatsApp Inbox", desc: "Shared team inbox with real-time messaging, delivery tracking, and WebSocket updates" },
              { icon: "🤖", title: "Kuwaiti AI Engine", desc: "133+ dialect markers, code-switching detection, intent classification, and auto-responses" },
              { icon: "⚡", title: "Smart Automations", desc: "Visual rule builder with 8 action types, condition engine, and Celery async execution" },
              { icon: "📊", title: "Sales Pipeline", desc: "Kanban board with drag-drop deals, activity tracking, and KWD 3-decimal values" },
              { icon: "💳", title: "K-Net Payments", desc: "Native Tap Payments integration for K-Net debit, Visa, Mastercard, and Apple Pay" },
              { icon: "🚚", title: "Aramex Shipping", desc: "Carrier integration with real-time tracking and automatic WhatsApp status notifications" },
              { icon: "🌐", title: "Landing Pages", desc: "Block-based page builder with WhatsApp CTA and conversion analytics" },
              { icon: "📣", title: "Broadcast Campaigns", desc: "Bulk WhatsApp messaging with audience targeting, scheduling, and delivery stats" },
              { icon: "🔒", title: "GCC Compliance", desc: "AWS Bahrain hosting, CITRA data classification, audit logging, and encryption" },
            ].map((f) => (
              <div key={f.title} className="group rounded-2xl border border-border bg-card p-6 hover:shadow-elevated hover:border-primary/20 transition-all duration-300 hover:-translate-y-0.5">
                <div className="text-3xl mb-4">{f.icon}</div>
                <h3 className="font-semibold text-lg mb-2 group-hover:text-primary transition-colors">{f.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA Section ──────────────────────────────────────────── */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto text-center rounded-3xl gradient-primary p-12 shadow-2xl shadow-emerald-500/20">
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">Ready to transform your business?</h2>
          <p className="text-emerald-100 text-lg mb-8 max-w-xl mx-auto">
            Join Kuwait businesses already using the most advanced WhatsApp CRM platform
          </p>
          <Link href="/register" className="inline-flex rounded-xl bg-white px-8 py-3.5 text-base font-semibold text-emerald-700 shadow-lg hover:shadow-xl transition-all hover:scale-[1.02]">
            Start Your Free Trial
          </Link>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────────── */}
      <footer className="border-t py-8 px-6">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="h-6 w-6 rounded gradient-primary flex items-center justify-center">
              <span className="text-white font-bold text-[10px]">KW</span>
            </div>
            <span className="text-sm text-muted-foreground">Kuwait WhatsApp Growth Engine &copy; 2026</span>
          </div>
          <div className="flex items-center gap-6 text-sm text-muted-foreground">
            <span>app.kwgrowth.com</span>
            <span>AWS me-south-1</span>
          </div>
        </div>
      </footer>
    </main>
  );
}
