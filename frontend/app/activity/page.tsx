"use client";

import { useCallback, useEffect, useState } from "react";
import { EmptyState, JpPage, Panel } from "@/components/jp/ui";
import { getAutomationResults, type AutomationRun } from "@/lib/automation-api";
import { humanizeActivitySummary } from "@/lib/ops-language";

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
      description="Operational log of inquiries, imports, email processing, and related events."
      actions={
        <button
          type="button"
          onClick={() => void load()}
          className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium"
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
      <Panel>
        {loading ? (
          <EmptyState title="Loading activity…" />
        ) : runs.length === 0 ? (
          <EmptyState
            title="No activity yet"
            body="Counter searches, imports, and email processing will appear here."
          />
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
              return (
                <li key={r.id} className="py-3">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <div className="text-sm font-medium text-slate-900">{hum.title}</div>
                      <div className="mt-0.5 text-sm text-slate-600">{hum.detail}</div>
                      {query ? (
                        <div className="mt-0.5 truncate font-mono text-xs text-slate-500">
                          {query}
                        </div>
                      ) : null}
                      <div className="mt-0.5 text-[11px] text-slate-400">
                        {r.created_at ? new Date(r.created_at).toLocaleString() : ""}
                      </div>
                      <button
                        type="button"
                        className="mt-1 text-[11px] font-medium text-slate-500 hover:underline"
                        onClick={() =>
                          setOpenId(isOpen ? null : r.id != null ? Number(r.id) : null)
                        }
                      >
                        {isOpen ? "Hide technical detail" : "Technical detail"}
                      </button>
                      {isOpen ? (
                        <pre className="mt-1 overflow-x-auto rounded bg-slate-950 p-2 text-[10px] text-slate-200">
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
                    {r.requires_human ? (
                      <span className="rounded bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-950">
                        Needs review
                      </span>
                    ) : (
                      <span className="rounded bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-900">
                        Recorded
                      </span>
                    )}
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
