"use client";

import { useState, useEffect } from "react";
import {
  usePipelines,
  useKanbanBoard,
  useCreatePipeline,
  useCreateDeal,
  useMoveDeal,
} from "@/hooks/use-pipelines";
import type { DealItem, KanbanColumn } from "@/hooks/use-pipelines";
import { formatCurrency } from "@/lib/utils";
import { cn } from "@/lib/utils";

export default function PipelinePage() {
  const { data: pipelines, isLoading: loadingPipelines } = usePipelines();
  const [selectedPipeline, setSelectedPipeline] = useState<string | null>(null);
  const [showCreatePipeline, setShowCreatePipeline] = useState(false);
  const [showCreateDeal, setShowCreateDeal] = useState(false);
  const [dragDeal, setDragDeal] = useState<DealItem | null>(null);

  const createPipeline = useCreatePipeline();
  const createDeal = useCreateDeal();
  const moveDeal = useMoveDeal();

  // Auto-select first pipeline
  useEffect(() => {
    if (!selectedPipeline && pipelines && pipelines.length > 0) {
      setSelectedPipeline(pipelines[0].id);
    }
  }, [pipelines, selectedPipeline]);

  const { data: board, isLoading: loadingBoard } = useKanbanBoard(selectedPipeline);

  const handleCreatePipeline = async () => {
    await createPipeline.mutateAsync({
      name: "Sales Pipeline",
      stages: [
        { name: "New Lead", color: "#6366f1", sort_order: 0 },
        { name: "Contacted", color: "#8b5cf6", sort_order: 1 },
        { name: "Qualified", color: "#06b6d4", sort_order: 2 },
        { name: "Proposal", color: "#f97316", sort_order: 3 },
        { name: "Negotiation", color: "#eab308", sort_order: 4 },
        { name: "Won", color: "#22c55e", sort_order: 5, is_won: true },
        { name: "Lost", color: "#ef4444", sort_order: 6, is_lost: true },
      ],
    });
    setShowCreatePipeline(false);
  };

  const handleDrop = (stageId: string, position: number) => {
    if (!dragDeal || !selectedPipeline) return;
    if (dragDeal.stage_id === stageId) return;

    moveDeal.mutate({
      deal_id: dragDeal.id,
      stage_id: stageId,
      position,
      pipeline_id: selectedPipeline,
    });
    setDragDeal(null);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold">Pipeline</h1>
          {pipelines && pipelines.length > 1 && (
            <select
              value={selectedPipeline ?? ""}
              onChange={(e) => setSelectedPipeline(e.target.value)}
              className="rounded-lg border border-input bg-background px-3 py-1 text-sm"
            >
              {pipelines.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          )}
        </div>
        <div className="flex gap-2">
          {selectedPipeline && (
            <button
              onClick={() => setShowCreateDeal(true)}
              className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              + New Deal
            </button>
          )}
          {(!pipelines || pipelines.length === 0) && (
            <button
              onClick={handleCreatePipeline}
              disabled={createPipeline.isPending}
              className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              {createPipeline.isPending ? "Creating..." : "Create Sales Pipeline"}
            </button>
          )}
        </div>
      </div>

      {loadingPipelines || loadingBoard ? (
        <div className="flex items-center justify-center py-24">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
      ) : !board ? (
        <div className="rounded-lg border bg-card p-12 text-center text-muted-foreground">
          No pipeline yet. Create one to start tracking deals.
        </div>
      ) : (
        <div className="flex gap-4 overflow-x-auto pb-4" style={{ minHeight: "calc(100vh - 12rem)" }}>
          {board.columns.map((col) => (
            <KanbanColumnView
              key={col.stage.id}
              column={col}
              onDragStart={setDragDeal}
              onDrop={(pos) => handleDrop(col.stage.id, pos)}
              isDragTarget={dragDeal !== null && dragDeal.stage_id !== col.stage.id}
            />
          ))}
        </div>
      )}

      {showCreateDeal && selectedPipeline && board && (
        <CreateDealDialog
          pipelineId={selectedPipeline}
          stages={board.columns.map((c) => c.stage)}
          onClose={() => setShowCreateDeal(false)}
        />
      )}
    </div>
  );
}

function KanbanColumnView({
  column,
  onDragStart,
  onDrop,
  isDragTarget,
}: {
  column: KanbanColumn;
  onDragStart: (deal: DealItem) => void;
  onDrop: (position: number) => void;
  isDragTarget: boolean;
}) {
  return (
    <div
      className={cn(
        "w-72 flex-shrink-0 rounded-lg border bg-muted/30 flex flex-col",
        isDragTarget && "ring-2 ring-primary ring-dashed"
      )}
      onDragOver={(e) => { e.preventDefault(); }}
      onDrop={(e) => { e.preventDefault(); onDrop(0); }}
    >
      {/* Column header */}
      <div className="p-3 border-b">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full" style={{ backgroundColor: column.stage.color }} />
            <span className="text-sm font-medium">{column.stage.name}</span>
            <span className="text-xs text-muted-foreground bg-muted rounded-full px-2 py-0.5">
              {column.deal_count}
            </span>
          </div>
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          {formatCurrency(parseFloat(column.total_value))}
        </p>
      </div>

      {/* Deals */}
      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {column.deals.map((deal) => (
          <DealCard
            key={deal.id}
            deal={deal}
            onDragStart={() => onDragStart(deal)}
          />
        ))}
      </div>
    </div>
  );
}

function DealCard({
  deal,
  onDragStart,
}: {
  deal: DealItem;
  onDragStart: () => void;
}) {
  return (
    <div
      draggable
      onDragStart={onDragStart}
      className="rounded-lg border bg-card p-3 cursor-grab active:cursor-grabbing hover:shadow-sm transition-shadow"
    >
      <h4 className="text-sm font-medium truncate">{deal.title}</h4>
      <p className="text-xs text-muted-foreground mt-1">
        {formatCurrency(parseFloat(deal.value))}
      </p>
      {deal.description && (
        <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
          {deal.description}
        </p>
      )}
      <div className="flex items-center gap-2 mt-2">
        <span className={cn(
          "text-[10px] rounded px-1.5 py-0.5",
          deal.status === "won" ? "bg-green-100 text-green-700" :
          deal.status === "lost" ? "bg-red-100 text-red-700" :
          "bg-blue-100 text-blue-700"
        )}>
          {deal.status}
        </span>
      </div>
    </div>
  );
}

function CreateDealDialog({
  pipelineId,
  stages,
  onClose,
}: {
  pipelineId: string;
  stages: { id: string; name: string }[];
  onClose: () => void;
}) {
  const createDeal = useCreateDeal();
  const [form, setForm] = useState({
    title: "",
    value: "0.000",
    stage_id: stages[0]?.id ?? "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await createDeal.mutateAsync({
      pipeline_id: pipelineId,
      stage_id: form.stage_id || undefined,
      title: form.title,
      value: parseFloat(form.value),
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md rounded-xl bg-card p-6 shadow-xl">
        <h2 className="text-lg font-semibold mb-4">New Deal</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Title</label>
            <input
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Value (KWD)</label>
            <input
              type="number"
              step="0.001"
              value={form.value}
              onChange={(e) => setForm({ ...form, value: e.target.value })}
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Stage</label>
            <select
              value={form.stage_id}
              onChange={(e) => setForm({ ...form, stage_id: e.target.value })}
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
            >
              {stages.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>
          <div className="flex justify-end gap-3">
            <button type="button" onClick={onClose} className="rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-accent">Cancel</button>
            <button type="submit" disabled={createDeal.isPending} className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
              {createDeal.isPending ? "Creating..." : "Create"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
