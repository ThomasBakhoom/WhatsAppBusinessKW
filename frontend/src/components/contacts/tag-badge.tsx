import type { TagResponse } from "@/types/api";

export function TagBadge({ tag }: { tag: TagResponse }) {
  return (
    <span
      className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium text-white"
      style={{ backgroundColor: tag.color }}
    >
      {tag.name}
    </span>
  );
}
