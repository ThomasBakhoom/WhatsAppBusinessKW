"use client";

import { useState, useRef } from "react";
import { useImportContacts } from "@/hooks/use-contacts";

interface Props {
  open: boolean;
  onClose: () => void;
}

export function ImportDialog({ open, onClose }: Props) {
  const importContacts = useImportContacts();
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<string | null>(null);

  if (!open) return null;

  const handleImport = async () => {
    if (!file) return;

    try {
      const res = await importContacts.mutateAsync(file);
      setResult(`Import started! Task ID: ${res.task_id}`);
      setFile(null);
      if (fileRef.current) fileRef.current.value = "";
    } catch (err: any) {
      setResult(err.response?.data?.title || "Import failed");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md rounded-xl bg-card p-6 shadow-xl">
        <h2 className="text-lg font-semibold mb-4">Import Contacts</h2>

        <p className="text-sm text-muted-foreground mb-4">
          Upload a CSV file with columns: phone, first_name, last_name, email, notes.
          The phone column is required.
        </p>

        <div className="mb-4">
          <input
            ref={fileRef}
            type="file"
            accept=".csv"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="w-full text-sm file:mr-4 file:rounded-lg file:border-0 file:bg-primary file:px-4 file:py-2 file:text-sm file:font-medium file:text-primary-foreground hover:file:bg-primary/90"
          />
        </div>

        {result && (
          <div className="mb-4 rounded-lg bg-blue-50 p-3 text-sm text-blue-700">
            {result}
          </div>
        )}

        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={() => {
              setFile(null);
              setResult(null);
              onClose();
            }}
            className="rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-accent transition-colors"
          >
            Close
          </button>
          <button
            type="button"
            onClick={handleImport}
            disabled={!file || importContacts.isPending}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            {importContacts.isPending ? "Importing..." : "Import"}
          </button>
        </div>
      </div>
    </div>
  );
}
