"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { cn } from "@/lib/utils";

export default function CompliancePage() {
  const { data: status, isLoading } = useQuery({
    queryKey: ["compliance-status"],
    queryFn: async () => (await apiClient.get("/compliance/status")).data,
  });
  const { data: report } = useQuery({
    queryKey: ["compliance-report"],
    queryFn: async () => (await apiClient.get("/compliance/report")).data,
  });
  const { data: auditLogs } = useQuery({
    queryKey: ["audit-logs"],
    queryFn: async () => (await apiClient.get("/compliance/audit-logs?limit=20")).data,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl">
      <h1 className="text-2xl font-bold mb-2">Compliance & Data Residency</h1>
      <p className="text-sm text-muted-foreground mb-6">Monitor data protection and regulatory compliance</p>

      {/* Overall Status */}
      {status && (
        <div className={cn(
          "rounded-lg border p-4 mb-6",
          status.overall_status === "compliant"
            ? "bg-green-50 border-green-200"
            : status.overall_status === "non_compliant"
              ? "bg-red-50 border-red-200"
              : "bg-yellow-50 border-yellow-200"
        )}>
          <div className="flex items-center gap-2">
            <span className={cn(
              "h-3 w-3 rounded-full",
              status.overall_status === "compliant"
                ? "bg-green-500"
                : status.overall_status === "non_compliant"
                  ? "bg-red-500"
                  : "bg-yellow-500"
            )} />
            <span className="font-semibold">
              {status.overall_status === "compliant"
                ? "All Checks Passing"
                : status.overall_status === "non_compliant"
                  ? "Non-Compliant — Action Required"
                  : "Needs Attention"}
            </span>
          </div>
        </div>
      )}

      {/* Compliance Checklist */}
      {status && (
        <div className="rounded-lg border bg-card mb-6">
          <div className="p-4 border-b">
            <h2 className="font-semibold">Compliance Checklist</h2>
          </div>
          <div className="divide-y">
            {Object.values(status.checks).map((check: any) => (
              <div key={check.label} className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <StatusIcon status={check.status} />
                    <div>
                      <p className="text-sm font-medium">{check.label}</p>
                      <p className="text-xs text-muted-foreground">{check.detail}</p>
                    </div>
                  </div>
                  <span className={cn(
                    "rounded-full px-2 py-0.5 text-[10px] font-medium shrink-0",
                    check.status === "pass" ? "bg-green-100 text-green-700" :
                    check.status === "warn" ? "bg-yellow-100 text-yellow-700" :
                    check.status === "fail" ? "bg-red-100 text-red-700" :
                    "bg-blue-100 text-blue-700"
                  )}>
                    {check.status === "pass" ? "Pass"
                      : check.status === "warn" ? "Warning"
                      : check.status === "fail" ? "Fail"
                      : "Info"}
                  </span>
                </div>
                {/* Verify hint — tells the operator where to confirm out-of-band */}
                {check.verify && (
                  <p className="mt-1 ml-9 text-[11px] text-amber-600 dark:text-amber-400">
                    Verify: {check.verify}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Data Residency Map */}
      {report && (
        <div className="rounded-lg border bg-card p-6 mb-6">
          <h2 className="font-semibold mb-4">Data Residency</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-muted-foreground">Provider</p>
              <p className="text-sm font-medium">{report.data_residency.provider}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Region</p>
              <p className="text-sm font-medium">{report.data_residency.region} ({report.data_residency.location})</p>
            </div>
            <div className="col-span-2">
              <p className="text-xs text-muted-foreground mb-1">Compliance Frameworks</p>
              <div className="flex gap-2">
                {report.data_residency.compliance_frameworks.map((f: string) => (
                  <span key={f} className="rounded-full bg-blue-100 text-blue-700 px-2 py-0.5 text-xs">{f}</span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Security Measures */}
      {report && (
        <div className="rounded-lg border bg-card p-6 mb-6">
          <h2 className="font-semibold mb-4">Security Measures</h2>
          <ul className="space-y-2">
            {report.security_measures.map((m: string) => (
              <li key={m} className="flex items-center gap-2 text-sm">
                <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
                {m}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Audit Logs */}
      {auditLogs && auditLogs.data && auditLogs.data.length > 0 && (
        <div className="rounded-lg border bg-card">
          <div className="p-4 border-b">
            <h2 className="font-semibold">Recent Audit Logs</h2>
          </div>
          <div className="divide-y">
            {auditLogs.data.map((log: any) => (
              <div key={log.id} className="flex items-center justify-between p-3">
                <div>
                  <p className="text-sm">{log.description}</p>
                  <p className="text-xs text-muted-foreground">{log.action} {log.user_email ? `by ${log.user_email}` : ""}</p>
                </div>
                <span className="text-xs text-muted-foreground">{new Date(log.created_at).toLocaleString()}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StatusIcon({ status }: { status: string }) {
  if (status === "pass") return <span className="text-green-500 text-lg">&#10003;</span>;
  if (status === "warn") return <span className="text-yellow-500 text-lg">&#9888;</span>;
  if (status === "fail") return <span className="text-red-500 text-lg">&#10007;</span>;
  return <span className="text-blue-500 text-lg">&#9432;</span>;
}
