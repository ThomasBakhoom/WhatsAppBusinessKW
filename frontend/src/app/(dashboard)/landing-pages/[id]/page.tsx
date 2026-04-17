"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  useLandingPage,
  useUpdateLandingPage,
  usePublishLandingPage,
} from "@/hooks/use-landing-pages";
import type { BlockContent } from "@/hooks/use-landing-pages";
import { cn } from "@/lib/utils";

const BLOCK_TYPES = [
  { type: "hero", label: "Hero Section" },
  { type: "text", label: "Text Block" },
  { type: "image", label: "Image" },
  { type: "features", label: "Features Grid" },
  { type: "cta", label: "Call to Action" },
  { type: "testimonial", label: "Testimonial" },
  { type: "faq", label: "FAQ" },
  { type: "divider", label: "Divider" },
];

export default function LandingPageEditor() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { data: page, isLoading } = useLandingPage(id);
  const updatePage = useUpdateLandingPage();
  const publishPage = usePublishLandingPage();

  const [editingBlock, setEditingBlock] = useState<number | null>(null);
  const [whatsappNumber, setWhatsappNumber] = useState("");
  const [whatsappMessage, setWhatsappMessage] = useState("");

  if (isLoading || !page) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  const blocks = page.blocks as BlockContent[];

  const addBlock = async (type: string) => {
    const newBlock: BlockContent = {
      type,
      content: type === "hero" ? { heading: "New Section", subheading: "", buttonText: "Learn More" }
        : type === "cta" ? { heading: "Get Started", buttonText: "Chat on WhatsApp" }
        : { body: "Edit this content..." },
      settings: {},
    };
    await updatePage.mutateAsync({
      id,
      data: { blocks: [...blocks, newBlock] },
    });
  };

  const updateBlock = async (index: number, content: Record<string, unknown>) => {
    const updated = [...blocks];
    updated[index] = { ...updated[index], content: { ...updated[index].content, ...content } };
    await updatePage.mutateAsync({ id, data: { blocks: updated } });
    setEditingBlock(null);
  };

  const removeBlock = async (index: number) => {
    const updated = blocks.filter((_, i) => i !== index);
    await updatePage.mutateAsync({ id, data: { blocks: updated } });
  };

  const moveBlock = async (index: number, direction: "up" | "down") => {
    const newIndex = direction === "up" ? index - 1 : index + 1;
    if (newIndex < 0 || newIndex >= blocks.length) return;
    const updated = [...blocks];
    [updated[index], updated[newIndex]] = [updated[newIndex], updated[index]];
    await updatePage.mutateAsync({ id, data: { blocks: updated } });
  };

  const handlePublish = async () => {
    if (whatsappNumber) {
      await updatePage.mutateAsync({
        id,
        data: { whatsapp_number: whatsappNumber, whatsapp_message: whatsappMessage },
      });
    }
    await publishPage.mutateAsync(id);
  };

  return (
    <div className="max-w-4xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <button onClick={() => router.push("/landing-pages")} className="text-sm text-muted-foreground hover:text-foreground mb-2 block">
            &larr; Back
          </button>
          <h1 className="text-2xl font-bold">{page.title}</h1>
          <p className="text-sm text-muted-foreground">/{page.slug}</p>
        </div>
        <div className="flex gap-2">
          <span className={cn(
            "rounded-full px-3 py-1 text-xs font-medium self-center",
            page.status === "published" ? "bg-green-100 text-green-700" : "bg-yellow-100 text-yellow-700"
          )}>
            {page.status}
          </span>
          {page.status === "draft" && (
            <button
              onClick={handlePublish}
              className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
              Publish
            </button>
          )}
        </div>
      </div>

      {/* WhatsApp Settings */}
      <div className="rounded-lg border bg-card p-4 mb-6">
        <h3 className="text-sm font-medium mb-3">WhatsApp CTA Settings</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-muted-foreground mb-1">WhatsApp Number</label>
            <input
              value={whatsappNumber || page.whatsapp_number || ""}
              onChange={(e) => setWhatsappNumber(e.target.value)}
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
              placeholder="+965XXXXXXXX"
            />
          </div>
          <div>
            <label className="block text-xs text-muted-foreground mb-1">Pre-filled Message</label>
            <input
              value={whatsappMessage || page.whatsapp_message || ""}
              onChange={(e) => setWhatsappMessage(e.target.value)}
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
              placeholder="Hi! I'm interested in..."
            />
          </div>
        </div>
      </div>

      {/* Block Editor */}
      <div className="space-y-3 mb-6">
        {blocks.map((block, index) => (
          <div key={index} className="rounded-lg border bg-card">
            <div className="flex items-center justify-between px-4 py-2 border-b bg-muted/30">
              <span className="text-xs font-medium uppercase text-muted-foreground">
                {BLOCK_TYPES.find((b) => b.type === block.type)?.label ?? block.type}
              </span>
              <div className="flex items-center gap-1">
                <button onClick={() => moveBlock(index, "up")} disabled={index === 0} className="text-xs px-1 text-muted-foreground hover:text-foreground disabled:opacity-30">&uarr;</button>
                <button onClick={() => moveBlock(index, "down")} disabled={index === blocks.length - 1} className="text-xs px-1 text-muted-foreground hover:text-foreground disabled:opacity-30">&darr;</button>
                <button onClick={() => setEditingBlock(editingBlock === index ? null : index)} className="text-xs px-2 text-muted-foreground hover:text-foreground">Edit</button>
                <button onClick={() => removeBlock(index)} className="text-xs px-2 text-muted-foreground hover:text-destructive">Remove</button>
              </div>
            </div>

            {/* Block Preview */}
            <div className="p-4">
              <BlockPreview block={block} />
            </div>

            {/* Block Editor */}
            {editingBlock === index && (
              <BlockEditor
                block={block}
                onSave={(content) => updateBlock(index, content)}
                onCancel={() => setEditingBlock(null)}
              />
            )}
          </div>
        ))}
      </div>

      {/* Add Block */}
      <div className="rounded-lg border border-dashed p-4">
        <p className="text-sm text-muted-foreground mb-3 text-center">Add a block</p>
        <div className="flex flex-wrap justify-center gap-2">
          {BLOCK_TYPES.map((bt) => (
            <button
              key={bt.type}
              onClick={() => addBlock(bt.type)}
              className="rounded-lg border px-3 py-1.5 text-xs hover:bg-accent transition-colors"
            >
              + {bt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Stats */}
      {page.status === "published" && (
        <div className="mt-6 grid grid-cols-3 gap-4">
          <div className="rounded-lg border bg-card p-4 text-center">
            <p className="text-2xl font-bold">{page.visit_count}</p>
            <p className="text-xs text-muted-foreground">Visits</p>
          </div>
          <div className="rounded-lg border bg-card p-4 text-center">
            <p className="text-2xl font-bold">{page.conversion_count}</p>
            <p className="text-xs text-muted-foreground">Conversions</p>
          </div>
          <div className="rounded-lg border bg-card p-4 text-center">
            <p className="text-2xl font-bold">
              {page.visit_count > 0 ? Math.round(page.conversion_count / page.visit_count * 100) : 0}%
            </p>
            <p className="text-xs text-muted-foreground">Rate</p>
          </div>
        </div>
      )}
    </div>
  );
}

function BlockPreview({ block }: { block: BlockContent }) {
  const c = block.content as Record<string, string>;

  switch (block.type) {
    case "hero":
      return (
        <div className="text-center py-4">
          <h2 className="text-xl font-bold">{c.heading || "Hero Heading"}</h2>
          {c.subheading && <p className="text-muted-foreground mt-1">{c.subheading}</p>}
          {c.buttonText && <span className="inline-block mt-2 bg-primary text-primary-foreground rounded-lg px-4 py-1 text-sm">{c.buttonText}</span>}
        </div>
      );
    case "cta":
      return (
        <div className="text-center py-4 bg-muted/30 rounded-lg">
          <h3 className="font-semibold">{c.heading || "Call to Action"}</h3>
          <span className="inline-block mt-2 bg-primary text-primary-foreground rounded-lg px-4 py-1 text-sm">{c.buttonText || "Contact Us"}</span>
        </div>
      );
    case "text":
      return <p className="text-sm">{c.body || "Text content..."}</p>;
    case "image":
      return <div className="bg-muted rounded-lg h-32 flex items-center justify-center text-sm text-muted-foreground">{c.url ? "Image" : "No image set"}</div>;
    case "divider":
      return <hr className="border-border" />;
    default:
      return <p className="text-sm text-muted-foreground">[{block.type} block]</p>;
  }
}

function BlockEditor({
  block,
  onSave,
  onCancel,
}: {
  block: BlockContent;
  onSave: (content: Record<string, unknown>) => void;
  onCancel: () => void;
}) {
  const [content, setContent] = useState(block.content as Record<string, string>);

  const fields = block.type === "hero" ? ["heading", "subheading", "buttonText"]
    : block.type === "cta" ? ["heading", "buttonText"]
    : block.type === "text" ? ["body"]
    : block.type === "image" ? ["url", "alt"]
    : ["body"];

  return (
    <div className="border-t p-4 bg-muted/20 space-y-3">
      {fields.map((field) => (
        <div key={field}>
          <label className="block text-xs font-medium mb-1 capitalize">{field.replace(/([A-Z])/g, " $1")}</label>
          {field === "body" ? (
            <textarea
              value={content[field] || ""}
              onChange={(e) => setContent({ ...content, [field]: e.target.value })}
              rows={3}
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
            />
          ) : (
            <input
              value={content[field] || ""}
              onChange={(e) => setContent({ ...content, [field]: e.target.value })}
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
            />
          )}
        </div>
      ))}
      <div className="flex justify-end gap-2">
        <button onClick={onCancel} className="rounded-lg border px-3 py-1 text-xs hover:bg-accent">Cancel</button>
        <button onClick={() => onSave(content)} className="rounded-lg bg-primary px-3 py-1 text-xs text-primary-foreground">Save</button>
      </div>
    </div>
  );
}
