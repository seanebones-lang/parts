"use client";

import { useCallback, useEffect, useState } from "react";
import { EmptyState, JpPage, Panel, StatusPill } from "@/components/jp/ui";
import { getAutomationResults, type AutomationRun } from "@/lib/automation-api";
import { humanizeActivitySummary } from "@/lib/ops-language";

function activityTone(
  kind: string | undefined,
  requiresHuman: boolean
): "warn" | "success" | "danger" | "neutral" | null {
  if (requiresHuman) return "warn";
  const k = String(kind || "").toLowerCase();
  if (k.includes("fail") || k.includes("error") || k.includes("conflict")) return "danger";
  if (
    k.includes("order_completed") ||
    k.includes("sale") ||
    k.includes("completed") ||
    k.includes("finalized")
  )
    return "success";
  // Ordinary inventory/import/quote events: no badge noise
  return null;
}

function activityBadgeLabel(tone: string, requiresHuman: boolean): string {
  if (requiresHuman || tone === "warn") return "Needs Review";
  if (tone === "danger") return "Failed";
  if (tone === "success") return "Completed";
  return "";
}

export default function ActivityPage() {
  const [runs, setRuns] = useState<AutomationRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [openId, setOpenId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getAutomationResults(100);
      setRuns(res.runs || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load activity");
      setRuns([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <JpPage
      title="Activity"
      description="Operational log of inquiries, inventory moves, quotes, sales, imports, and email processing."
      fullBleed
      actions={
        <button
          type="button"
          onClick={() => void load()}
          className="h-10 rounded-md border border-slate-300 bg-white px-4 text-sm font-semibold text-slate-800 hover:bg-slate-50"
        >
          Refresh
        </button>
      }
    >
      {error ? (
        <div className="mb-3 rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </div>
      ) : null}
      <Panel flush>
        {loading ? (
          <div className="p-6">
            <EmptyState title="Loading activity…" />
          </div>
        ) : runs.length === 0 ? (
          <div className="p-6">
            <EmptyState
              title="No activity yet"
              body="Counter searches, inventory operations, quotes, imports, and email processing will appear here."
            />
          </div>
        ) : (
          <ul className="divide-y divide-slate-100">
            {runs.map((r) => {
              const detail = (r.detail || {}) as Record<string, unknown>;
              const ev = detail.evidence as { query?: string } | undefined;
              const query =
                typeof detail.query === "string"
                  ? detail.query
                  : typeof ev?.query === "string"
                    ? ev.query
                    : null;
              const hum = humanizeActivitySummary(
                r.kind,
                r.summary,
                Boolean(r.requires_human)
              );
              const isOpen = openId === r.id;
              const tone = activityTone(r.kind, Boolean(r.requires_human));
              return (
                <li key={r.id} className="px-5 py-4 hover:bg-slate-50/60">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <div className="text-[15px] font-semibold text-slate-900">
                        {hum.title}
                      </div>
                      <div className="mt-0.5 text-sm text-slate-600">{hum.detail}</div>
                      {query ? (
                        <div className="mt-1 truncate font-mono text-xs text-slate-500">
                          {query}
                        </div>
                      ) : null}
                      <div className="mt-1 text-xs text-slate-400">
                        {r.created_at ? new Date(r.created_at).toLocaleString() : ""}
                      </div>
                      <button
                        type="button"
                        className="mt-1.5 text-xs font-medium text-slate-500 underline-offset-2 hover:underline"
                        onClick={() =>
                          setOpenId(isOpen ? null : r.id != null ? Number(r.id) : null)
                        }
                      >
                        {isOpen ? "Hide technical detail" : "Technical detail"}
                      </button>
                      {isOpen ? (
                        <pre className="mt-2 max-h-64 overflow-auto rounded bg-slate-950 p-3 text-[11px] text-slate-200">
                          {JSON.stringify(
                            {
                              kind: r.kind,
                              status: r.status,
                              summary: r.summary,
                              detail,
                            },
                            null,
                            2
                          )}
                        </pre>
                      ) : null}
                    </div>
                    {tone ? (
                      <StatusPill tone={tone}>
                        {activityBadgeLabel(tone, Boolean(r.requires_human))}
                      </StatusPill>
                    ) : null}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </Panel>
    </JpPage>
  );
}
