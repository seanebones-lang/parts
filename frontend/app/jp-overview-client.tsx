"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  EmptyState,
  JpPage,
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
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [inv, hist, em, auto, st] = await Promise.all([
        listDmsInventory().catch(() => ({ rows: [] as DmsInventoryRow[] })),
        listTransmissionImportHistory(5).catch(() => ({
          imports: [] as TransmissionImportHistoryItem[],
        })),
        getEmailStatus().catch(() => null),
        getAutomationResults(12).catch(() => ({ runs: [] as AutomationRun[] })),
        getDmsStatus().catch(() => null),
      ]);
      setRows((inv.rows || []).filter(isTransmissionRow));
      setImports(hist.imports || []);
      setEmailSt(em);
      setRuns(auto.runs || []);
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
      description="Counter-ready parts intelligence for transmission hard parts."
    >
      <form onSubmit={onSearch} className="mb-5">
        <div className="flex gap-2">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search SKU, OEM, casting number, vehicle, or natural-language request"
            className="h-12 flex-1 rounded-md border border-slate-300 bg-white px-4 text-sm shadow-sm placeholder:text-slate-400 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-900/10"
          />
          <button
            type="submit"
            className="h-12 rounded-md bg-slate-900 px-5 text-sm font-semibold text-white hover:bg-slate-800"
          >
            Search
          </button>
        </div>
        <div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-500">
          {[
            "2011 Tahoe 6L80 pump",
            "24264418",
            "6L80-PUMP-01",
            "6R80 pump",
          ].map((ex) => (
            <button
              key={ex}
              type="button"
              className="rounded border border-slate-200 bg-white px-2 py-1 hover:border-slate-400"
              onClick={() => router.push(`/transmission?q=${encodeURIComponent(ex)}`)}
            >
              {ex}
            </button>
          ))}
        </div>
      </form>

      <div className="mb-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile label="Indexed SKUs" value={loading ? "…" : stats.skus} />
        <StatTile
          label="In stock lines"
          value={loading ? "…" : stats.available}
          hint={`${stats.units} units on hand`}
        />
        <StatTile label="Low stock lines" value={loading ? "…" : stats.low} />
        <StatTile label="Out of stock lines" value={loading ? "…" : stats.out} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel
          title="Email Desk"
          right={
            <Link href="/emails" className="text-xs font-medium text-slate-600 hover:underline">
              Open desk
            </Link>
          }
        >
          {emailSt ? (
            <div className="grid grid-cols-3 gap-3 text-center">
              <div>
                <div className="text-2xl font-semibold tabular-nums">
                  {emailSt.total ?? 0}
                </div>
                <div className="text-[11px] uppercase text-slate-500">Total</div>
              </div>
              <div>
                <div className={`text-2xl font-semibold tabular-nums ${trafficCountClass("yellow")}`}>
                  {emailSt.requires_human ?? emailSt.by_traffic_light?.yellow ?? 0}
                </div>
                <div className="text-[11px] uppercase text-slate-500">Needs review</div>
              </div>
              <div>
                <div className={`text-2xl font-semibold tabular-nums ${trafficCountClass("green")}`}>
                  {emailSt.by_traffic_light?.green ?? 0}
                </div>
                <div className="text-[11px] uppercase text-slate-500">Handled</div>
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
          title="Latest inventory import"
          right={
            <Link
              href="/transmission/import"
              className="text-xs font-medium text-slate-600 hover:underline"
            >
              Data Import
            </Link>
          }
        >
          {latestImport ? (
            <div className="space-y-1 text-sm">
              {(() => {
                const h = humanizeImportHistoryItem(latestImport);
                return (
                  <>
                    <div className="font-medium text-slate-900">{h.title}</div>
                    <div className="text-xs text-slate-500">
                      {latestImport.created_at
                        ? new Date(latestImport.created_at).toLocaleString()
                        : "—"}
                      {latestImport.rollback_status
                        ? ` · Rollback: ${latestImport.rollback_status}`
                        : ""}
                    </div>
                    <div className="text-xs text-slate-600">{h.stats}</div>
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

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Panel
          title="Inventory snapshot"
          right={
            <Link href="/inventory" className="text-xs font-medium text-slate-600 hover:underline">
              Browse
            </Link>
          }
        >
          {rows.length === 0 ? (
            <EmptyState title={loading ? "Loading…" : "No inventory rows"} />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-[11px] uppercase text-slate-500">
                  <tr className="border-b">
                    <th className="py-2 pr-2 font-medium">SKU</th>
                    <th className="py-2 pr-2 font-medium">Location</th>
                    <th className="py-2 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.slice(0, 8).map((r, i) => {
                    const loc = formatTransmissionLocationLine({
                      location: r.location || r.location_code,
                      location_name: r.location_name,
                      bin: (r as { bin?: string }).bin,
                    });
                    return (
                      <tr key={`${r.sku}-${i}`} className="border-b border-slate-50">
                        <td className="py-2 pr-2 font-mono text-xs">{r.sku}</td>
                        <td className="py-2 pr-2 text-xs text-slate-600">{loc.title}</td>
                        <td className="py-2">
                          <StockBadge qty={qtyOf(r)} />
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
          title="Recent activity"
          right={
            <Link href="/activity" className="text-xs font-medium text-slate-600 hover:underline">
              All activity
            </Link>
          }
        >
          {runs.length === 0 ? (
            <EmptyState
              title={loading ? "Loading…" : "No activity yet"}
              body="Searches, imports, and email processing appear here."
            />
          ) : (
            <ul className="space-y-2">
              {runs.slice(0, 8).map((r) => {
                const hum = humanizeActivitySummary(
                  r.kind,
                  r.summary,
                  Boolean(r.requires_human)
                );
                return (
                <li
                  key={r.id}
                  className="flex items-start justify-between gap-2 border-b border-slate-50 pb-2 text-sm last:border-0"
                >
                  <div className="min-w-0">
                    <div className="truncate font-medium text-slate-800">
                      {hum.title}
                    </div>
                    <div className="truncate text-xs text-slate-500">{hum.detail}</div>
                    <div className="text-[11px] text-slate-400">
                      {r.created_at ? new Date(r.created_at).toLocaleString() : ""}
                    </div>
                  </div>
                  {r.requires_human ? (
                    <span className="shrink-0 rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-900">
                      Review
                    </span>
                  ) : null}
                </li>
                );
              })}
            </ul>
          )}
        </Panel>
      </div>

      <p className="mt-6 text-[11px] text-slate-400">
        Pilot evaluation build. Synthetic data is labeled in the header and is not JP production inventory.
      </p>
    </JpPage>
  );
}
