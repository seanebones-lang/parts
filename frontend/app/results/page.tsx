"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  AlertCircle,
  Bot,
  CheckCircle2,
  Loader2,
  RefreshCw,
} from "lucide-react";
import {
  type AutomationAlert,
  type AutomationResults,
  type AutomationRun,
  ApiError,
  getAutomationResults,
  isApiUnreachable,
  resolveAutomationAlert,
} from "@/lib/automation-api";

function sevVariant(sev?: string): "default" | "secondary" | "destructive" | "outline" {
  if (sev === "red") return "destructive";
  if (sev === "yellow") return "secondary";
  return "outline";
}

export default function AutomationResultsPage() {
  const [data, setData] = useState<AutomationResults | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await getAutomationResults(50);
      setData(r);
    } catch (e) {
      setData(null);
      if (isApiUnreachable(e) || (e instanceof ApiError && e.status === 404)) {
        setError(
          e instanceof ApiError && e.status === 404
            ? "Automation API not loaded. Run ./scripts/demo_up.sh"
            : "API unreachable. Run ./scripts/demo_up.sh"
        );
      } else {
        setError(e instanceof Error ? e.message : "Failed to load results");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function onResolve(id?: number) {
    if (!id) return;
    setBusy(id);
    try {
      await resolveAutomationAlert(id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Resolve failed");
    } finally {
      setBusy(null);
    }
  }

  const runs: AutomationRun[] = data?.runs || [];
  const alerts: AutomationAlert[] = data?.alerts || [];
  const integ = data?.integrations || {};

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="rounded-lg border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-950">
        <strong>Automation results</strong> — daily/always view of AI workflow runs,
        missing-field alerts, and human-in-the-loop items. White-label Parts desk —
        no invented CRM/accounting links without credentials.
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Bot className="h-6 w-6" />
            Automation Results
          </h1>
          <p className="text-sm text-muted-foreground">
            Email process ledger · HIL alerts · email→order bridge
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            <span className="ml-1">Refresh</span>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link href="/emails">Email Desk</Link>
          </Button>
        </div>
      </div>

      {error && (
        <div className="flex gap-2 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-950">
          <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total runs</CardDescription>
            <CardTitle className="text-3xl">{data?.total_runs ?? "—"}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Open alerts</CardDescription>
            <CardTitle className="text-3xl">{data?.open_alerts ?? "—"}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Recent HIL</CardDescription>
            <CardTitle className="text-3xl">
              {data?.recent_requires_human ?? "—"}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Integrations</CardDescription>
            <CardContent className="p-0 pt-1 text-xs space-y-1">
              <div>DMS: {String(integ.dms ?? true)}</div>
              <div>CRM: {String(integ.crm ?? false)} (credentials)</div>
              <div>Accounting: {String(integ.accounting ?? false)} (credentials)</div>
            </CardContent>
          </CardHeader>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Open alerts</CardTitle>
            <CardDescription>
              Missing fields, pipeline errors, red grades — human review
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {loading && !data ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" /> Loading…
              </div>
            ) : alerts.length === 0 ? (
              <p className="text-sm text-muted-foreground flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                No open alerts
              </p>
            ) : (
              alerts.map((a) => (
                <div
                  key={a.id}
                  className="flex flex-wrap items-start justify-between gap-2 rounded border p-3 text-sm"
                >
                  <div className="space-y-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant={sevVariant(a.severity)}>{a.severity || "?"}</Badge>
                      <span className="font-medium">{a.code}</span>
                      {a.run_id != null && (
                        <span className="text-xs text-muted-foreground">run #{a.run_id}</span>
                      )}
                    </div>
                    <p className="text-muted-foreground break-words">{a.message}</p>
                    {!!a.fields?.length && (
                      <p className="text-xs">Fields: {a.fields.join(", ")}</p>
                    )}
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={busy === a.id}
                    onClick={() => void onResolve(a.id)}
                  >
                    {busy === a.id ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      "Resolve"
                    )}
                  </Button>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent runs</CardTitle>
            <CardDescription>Recorded automation activity (newest first)</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 max-h-[28rem] overflow-auto">
            {runs.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No runs yet. Process email desk traffic or seed emails — each process
                writes a run.
              </p>
            ) : (
              runs.map((r) => (
                <div key={r.id} className="rounded border px-3 py-2 text-sm space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="outline">{r.kind}</Badge>
                    <Badge
                      variant={
                        r.status === "error" || r.status === "escalated"
                          ? "destructive"
                          : r.requires_human
                            ? "secondary"
                            : "default"
                      }
                    >
                      {r.status}
                    </Badge>
                    {r.requires_human && <Badge variant="secondary">HIL</Badge>}
                    <span className="text-xs text-muted-foreground ml-auto">
                      {r.created_at}
                    </span>
                  </div>
                  <p className="text-muted-foreground break-words">{r.summary}</p>
                  {r.source_ref && (
                    <p className="text-xs font-mono text-muted-foreground">{r.source_ref}</p>
                  )}
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
