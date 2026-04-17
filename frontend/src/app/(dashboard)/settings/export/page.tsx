"use client";

import { useState } from "react";
import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

const EXPORTS = [
  { key: "contacts", title: "Contacts", description: "Export all contacts with tags, status, lead score", icon: "👥" },
  { key: "conversations", title: "Conversations", description: "Export conversation summaries with status and last message", icon: "💬" },
  { key: "deals", title: "Deals", description: "Export all pipeline deals with value and status", icon: "📊" },
];

export default function ExportPage() {
  const [downloading, setDownloading] = useState<string | null>(null);

  const handleExport = async (key: string) => {
    setDownloading(key);
    try {
      const res = await apiClient.get(`/export/${key}`, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = `${key}_export.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      alert("Export failed");
    }
    setDownloading(null);
  };

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold mb-2">Data Export</h1>
      <p className="text-sm text-muted-foreground mb-6">Download your data as CSV files</p>

      <div className="space-y-3">
        {EXPORTS.map((exp) => (
          <Card key={exp.key}>
            <CardContent className="p-5 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <span className="text-3xl">{exp.icon}</span>
                <div>
                  <h3 className="font-medium">{exp.title}</h3>
                  <p className="text-sm text-muted-foreground">{exp.description}</p>
                </div>
              </div>
              <Button variant="outline" onClick={() => handleExport(exp.key)} disabled={downloading === exp.key}>
                {downloading === exp.key ? "Downloading..." : "Export CSV"}
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
