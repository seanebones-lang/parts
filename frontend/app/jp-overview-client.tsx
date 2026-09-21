"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  EmptyState,
  JpPage,
  MetricGroup,
  Panel,
  StatTile,
  StockBadge,
} from "@/components/jp/ui";
import {
  formatTransmissionLocationLine,
} from "@/lib/demo-vertical";
import {
  getDmsStatus,
  listDmsInventory,
  listTransmissionImportHistory,
  opsOverview,
  type DmsInventoryRow,
  type TransmissionImportHistoryItem,
} from "@/lib/dms-api";
import { getEmailStatus, type EmailStatus } from "@/lib/email-api";
import { getAutomationResults, type AutomationRun } from "@/lib/automation-api";
import {
  humanizeActivitySummary,
  humanizeImportHistoryItem,
  trafficCountClass,
} from "@/lib/ops-language";

function qtyOf(row: DmsInventoryRow): number {
  const q = row.qty ?? row.quantity ?? row.on_hand;
  return typeof q === "number" && Number.isFinite(q) ? q : 0;
}

function isTransmissionRow(row: DmsInventoryRow): boolean {
  const fam = String((row as { transmission_family?: string }).transmission_family || "");
  const cat = String(row.category || "").toLowerCase();
  const sku = String(row.sku || "").toUpperCase();
  if (fam) return true;
  if (cat.includes("transmission")) return true;
  return /^(6L|4L|6R|10R|8HP)/i.test(sku);
}

export default function JpOverviewPage() {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [rows, setRows] = useState<DmsInventoryRow[]>([]);
  const [imports, setImports] = useState<TransmissionImportHistoryItem[]>([]);
  const [emailSt, setEmailSt] = useState<EmailStatus | null>(null);
  const [runs, setRuns] = useState<AutomationRun[]>([]);
  const [catalogCount, setCatalogCount] = useState<number | null>(null);
  const [opsStats, setOpsStats] = useState<{
    open_quotes?: number;
    reserved_units?: number;
    open_orders?: number;
    completed_orders?: number;
  } | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [inv, hist, em, auto, st, ops] = await Promise.all([
        listDmsInventory().catch(() => ({ rows: [] as DmsInventoryRow[] })),
        listTransmissionImportHistory(5).catch(() => ({
          imports: [] as TransmissionImportHistoryItem[],
        })),
        getEmailStatus().catch(() => null),
        getAutomationResults(12).catch(() => ({ runs: [] as AutomationRun[] })),
        getDmsStatus().catch(() => null),
        opsOverview().catch(() => null),
      ]);
      setRows((inv.rows || []).filter(isTransmissionRow));
      setImports(hist.imports || []);
      setEmailSt(em);
      setRuns(auto.runs || []);
      setOpsStats(ops);
      const cc =
        st?.catalog_count ??
        (typeof st?.catalog_count === "number" ? st.catalog_count : null);
      setCatalogCount(typeof cc === "number" ? cc : null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const stats = useMemo(() => {
    const skus = new Set(rows.map((r) => r.sku).filter(Boolean));
    let available = 0;
    let low = 0;
    let out = 0;
    for (const r of rows) {
      const qn = qtyOf(r);
      if (qn <= 0) out += 1;
      else if (qn === 1) low += 1;
      else available += 1;
    }
    return {
      skus: skus.size || catalogCount || 0,
      available,
      low,
      out,
      units: rows.reduce((a, r) => a + qtyOf(r), 0),
    };
  }, [rows, catalogCount]);

  const onSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const t = q.trim();
    if (!t) return;
    router.push(`/transmission?q=${encodeURIComponent(t)}`);
  };

  const latestImport = imports[0];

  return (
    <JpPage
      title="Overview"
      description="JP Transmission Parts Intelligence — start a counter search, then work inventory, quotes, email, and import from one place."
      fullBleed
    >
      <form onSubmit={onSearch} className="mb-6">
        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
          <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
            Counter search
          </div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="SKU, OEM, casting number, vehicle, or what the customer asked for"
              className="h-12 flex-1 rounded-md border border-slate-300 bg-white px-4 text-[15px] shadow-sm placeholder:text-slate-400 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-900/10"
            />
            <button
              type="submit"
              className="h-12 rounded-md bg-slate-900 px-6 text-[15px] font-semibold text-white hover:bg-slate-800"
            >
              Search
            </button>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {[
              "2011 Tahoe 6L80 pump",
              "24264418",
              "6L80-PUMP-01",
              "6R80 pump",
            ].map((ex) => (
              <button
                key={ex}
                type="button"
                className="rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:border-slate-400 hover:bg-white"
                onClick={() => router.push(`/transmission?q=${encodeURIComponent(ex)}`)}
              >
                {ex}
              </button>
            ))}
          </div>
        </div>
      </form>

      <MetricGroup label="Inventory">
        <StatTile label="Indexed SKUs" value={loading ? "…" : stats.skus} tone="neutral" />
        <StatTile
          label="In Stock"
          value={loading ? "…" : stats.available}
          hint={`${stats.units} units on hand`}
          tone="success"
        />
        <StatTile label="Low Stock" value={loading ? "…" : stats.low} tone="warn" />
        <StatTile label="Out of Stock" value={loading ? "…" : stats.out} tone="danger" />
      </MetricGroup>

      <MetricGroup label="Operations">
        <StatTile label="Open Quotes" value={loading ? "…" : opsStats?.open_quotes ?? 0} />
        <StatTile label="Reserved Units" value={loading ? "…" : opsStats?.reserved_units ?? 0} tone="warn" />
        <StatTile label="Open Orders" value={loading ? "…" : opsStats?.open_orders ?? 0} />
        <StatTile
          label="Completed Orders"
          value={loading ? "…" : opsStats?.completed_orders ?? 0}
          tone="success"
        />
      </MetricGroup>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel
          title="Email Desk"
          right={
            <Link href="/emails" className="text-xs font-semibold text-slate-600 hover:underline">
              Open desk →
            </Link>
          }
        >
          {emailSt ? (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <div>
                <div className="text-[28px] font-semibold tabular-nums leading-none text-slate-900">
                  {emailSt.total ?? 0}
                </div>
                <div className="mt-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Total
                </div>
              </div>
              <div>
                <div className={`text-[28px] font-semibold tabular-nums leading-none ${trafficCountClass("yellow")}`}>
                  {emailSt.requires_human ?? emailSt.by_traffic_light?.yellow ?? 0}
                </div>
                <div className="mt-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Needs Review
                </div>
              </div>
              <div>
                <div className={`text-[28px] font-semibold tabular-nums leading-none ${trafficCountClass("green")}`}>
                  {emailSt.by_traffic_light?.green ?? 0}
                </div>
                <div className="mt-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Handled
                </div>
              </div>
              <div>
                <div className={`text-[28px] font-semibold tabular-nums leading-none ${trafficCountClass("red")}`}>
                  {emailSt.by_traffic_light?.red ?? 0}
                </div>
                <div className="mt-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Urgent
                </div>
              </div>
            </div>
          ) : (
            <EmptyState
              title="Email desk unavailable"
              body="Start the API stack to load mailbox status."
            />
          )}
        </Panel>

        <Panel
          title="Latest Inventory Import"
          right={
            <Link
              href="/transmission/import"
              className="text-xs font-semibold text-slate-600 hover:underline"
            >
              Data Import →
            </Link>
          }
        >
          {latestImport ? (
            <div className="space-y-1.5 text-sm">
              {(() => {
                const h = humanizeImportHistoryItem(latestImport);
                return (
                  <>
                    <div className="text-base font-semibold text-slate-900">{h.title}</div>
                    <div className="text-sm text-slate-600">{h.stats}</div>
                    <div className="text-xs text-slate-500">
                      {latestImport.created_at
                        ? new Date(latestImport.created_at).toLocaleString()
                        : "—"}
                      {latestImport.rollback_status
                        ? ` · Rollback: ${latestImport.rollback_status}`
                        : ""}
                    </div>
                  </>
                );
              })()}
            </div>
          ) : (
            <EmptyState
              title="No imports yet"
              body="Use Data Import to preview and load a pilot CSV."
            />
          )}
        </Panel>
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-5">
        <Panel
          className="xl:col-span-3"
          title="Inventory Snapshot"
          right={
            <Link href="/inventory" className="text-xs font-semibold text-slate-600 hover:underline">
              Browse inventory →
            </Link>
          }
          flush
        >
          {rows.length === 0 ? (
            <div className="p-5">
              <EmptyState title={loading ? "Loading…" : "No inventory rows"} />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                  <tr className="border-b border-slate-200">
                    <th className="px-4 py-2.5 font-semibold">SKU</th>
                    <th className="px-4 py-2.5 font-semibold">Location</th>
                    <th className="px-4 py-2.5 font-semibold text-right">On Hand</th>
                    <th className="px-4 py-2.5 font-semibold">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.slice(0, 10).map((r, i) => {
                    const loc = formatTransmissionLocationLine({
                      location: r.location || r.location_code,
                      location_name: r.location_name,
                      bin: (r as { bin?: string }).bin,
                    });
                    const qn = qtyOf(r);
                    return (
                      <tr
                        key={`${r.sku}-${i}`}
                        className="border-b border-slate-100 hover:bg-slate-50/80"
                      >
                        <td className="px-4 py-2.5 font-mono text-[13px] font-medium text-slate-900">
                          {r.sku}
                        </td>
                        <td className="px-4 py-2.5 text-[13px] text-slate-700">{loc.title}</td>
                        <td className="px-4 py-2.5 text-right tabular-nums text-[13px] font-medium">
                          {qn}
                        </td>
                        <td className="px-4 py-2.5">
                          <StockBadge qty={qn} />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Panel>

        <Panel
          className="xl:col-span-2"
          title="Recent Activity"
          right={
            <Link href="/activity" className="text-xs font-semibold text-slate-600 hover:underline">
              All activity →
            </Link>
          }
        >
          {runs.length === 0 ? (
            <EmptyState
              title={loading ? "Loading…" : "No activity yet"}
              body="Searches, imports, and email processing appear here."
            />
          ) : (
            <ul className="space-y-3">
              {runs.slice(0, 8).map((r) => {
                const hum = humanizeActivitySummary(
                  r.kind,
                  r.summary,
                  Boolean(r.requires_human)
                );
                return (
                <li
                  key={r.id}
                  className="flex items-start justify-between gap-2 border-b border-slate-100 pb-3 text-sm last:border-0 last:pb-0"
                >
                  <div className="min-w-0">
                    <div className="truncate text-[14px] font-semibold text-slate-900">
                      {hum.title}
                    </div>
                    <div className="truncate text-[13px] text-slate-600">{hum.detail}</div>
                    <div className="mt-0.5 text-xs text-slate-400">
                      {r.created_at ? new Date(r.created_at).toLocaleString() : ""}
                    </div>
                  </div>
                  {r.requires_human ? (
                    <span className="shrink-0 rounded bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-900">
                      Needs Review
                    </span>
                  ) : null}
                </li>
                );
              })}
            </ul>
          )}
        </Panel>
      </div>

      <p className="mt-6 text-xs text-slate-400">
        Pilot evaluation build. Synthetic data is labeled in the header and is not JP production inventory.
      </p>
    </JpPage>
  );
}
