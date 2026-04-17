"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  useLandingPages,
  useCreateLandingPage,
  usePublishLandingPage,
  useDeleteLandingPage,
} from "@/hooks/use-landing-pages";
import { formatRelativeTime } from "@/lib/utils";
import { cn } from "@/lib/utils";

export default function LandingPagesPage() {
  const router = useRouter();
  const { data, isLoading } = useLandingPages();
  const createPage = useCreateLandingPage();
  const publishPage = usePublishLandingPage();
  const deletePage = useDeleteLandingPage();
  const [showCreate, setShowCreate] = useState(false);

  const pages = data?.data ?? [];

  const handleCreate = async (title: string, slug: string) => {
    const page = await createPage.mutateAsync({
      title,
      slug,
      blocks: [
        {
          type: "hero",
          content: { heading: title, subheading: "Welcome to our page", buttonText: "Chat on WhatsApp" },
          settings: { backgroundColor: "#25D366" },
        },
        {
          type: "text",
          content: { body: "Tell your customers about your product or service." },
          settings: {},
        },
        {
          type: "cta",
          content: { heading: "Ready to get started?", buttonText: "Message us on WhatsApp" },
          settings: { backgroundColor: "#f8fafc" },
        },
      ],
      whatsapp_message: "Hi! I visited your page and I'm interested in learning more.",
    });
    setShowCreate(false);
    router.push(`/landing-pages/${page.id}`);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Landing Pages</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Create pages with WhatsApp CTA to capture leads
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          + New Page
        </button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
      ) : pages.length === 0 ? (
        <div className="rounded-lg border bg-card p-12 text-center text-muted-foreground">
          No landing pages yet. Create your first page to start capturing leads.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {pages.map((page) => (
            <div
              key={page.id}
              className="rounded-lg border bg-card p-5 hover:shadow-sm transition-shadow cursor-pointer"
              onClick={() => router.push(`/landing-pages/${page.id}`)}
            >
              <div className="flex items-start justify-between">
                <h3 className="font-medium truncate">{page.title}</h3>
                <span className={cn(
                  "rounded-full px-2 py-0.5 text-[10px] font-medium flex-shrink-0 ml-2",
                  page.status === "published" ? "bg-green-100 text-green-700" :
                  page.status === "archived" ? "bg-gray-100 text-gray-600" :
                  "bg-yellow-100 text-yellow-700"
                )}>
                  {page.status}
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-1">/{page.slug}</p>
              <div className="flex items-center gap-4 mt-3 text-xs text-muted-foreground">
                <span>{page.visit_count} visits</span>
                <span>{page.conversion_count} conversions</span>
                <span>{page.visit_count > 0 ? Math.round(page.conversion_count / page.visit_count * 100) : 0}% rate</span>
              </div>
              <div className="flex items-center justify-between mt-3">
                <span className="text-xs text-muted-foreground">
                  {formatRelativeTime(page.created_at)}
                </span>
                <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
                  {page.status === "draft" && (
                    <button
                      onClick={() => publishPage.mutate(page.id)}
                      className="text-xs text-primary hover:underline"
                    >
                      Publish
                    </button>
                  )}
                  <button
                    onClick={() => { if (confirm("Delete?")) deletePage.mutate(page.id); }}
                    className="text-xs text-muted-foreground hover:text-destructive"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {showCreate && <CreatePageDialog onClose={() => setShowCreate(false)} onCreate={handleCreate} />}
    </div>
  );
}

function CreatePageDialog({
  onClose,
  onCreate,
}: {
  onClose: () => void;
  onCreate: (title: string, slug: string) => void;
}) {
  const [title, setTitle] = useState("");
  const [slug, setSlug] = useState("");

  const autoSlug = (t: string) => {
    setTitle(t);
    setSlug(t.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""));
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md rounded-xl bg-card p-6 shadow-xl">
        <h2 className="text-lg font-semibold mb-4">New Landing Page</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Page Title</label>
            <input
              value={title}
              onChange={(e) => autoSlug(e.target.value)}
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
              placeholder="e.g., Summer Sale 2026"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">URL Slug</label>
            <div className="flex items-center gap-1">
              <span className="text-sm text-muted-foreground">/</span>
              <input
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
                className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
                placeholder="summer-sale-2026"
              />
            </div>
          </div>
          <div className="flex justify-end gap-3">
            <button onClick={onClose} className="rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-accent">Cancel</button>
            <button
              onClick={() => title && slug && onCreate(title, slug)}
              disabled={!title || !slug}
              className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              Create
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
