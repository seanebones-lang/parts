"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  formatTransmissionLocationLine,
  isTransmissionDemo,
} from "@/lib/demo-vertical";
import {
  type DmsInventoryRow,
  isApiUnreachable,
  listDmsInventory,
} from "@/lib/dms-api";
import { EmptyState, JpPage, Panel, StockBadge, stockLevel } from "@/components/jp/ui";
import InventoryFullPage from "./inventory-full";

function qtyOf(row: DmsInventoryRow): number {
  const q = row.qty ?? row.quantity ?? row.on_hand;
  return typeof q === "number" && Number.isFinite(q) ? q : 0;
}

function isTx(row: DmsInventoryRow): boolean {
  const fam = String((row as { transmission_family?: string }).transmission_family || "");
  const cat = String(row.category || "").toLowerCase();
  const sku = String(row.sku || "");
  if (fam) return true;
  if (cat.includes("transmission")) return true;
  return /6L|4L|6R|10R|8HP/i.test(sku);
}

function JpInventory() {
  const [rows, setRows] = useState<DmsInventoryRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [family, setFamily] = useState("");
  const [stock, setStock] = useState<"all" | "in" | "low" | "out">("all");
  const [selected, setSelected] = useState<DmsInventoryRow | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const inv = await listDmsInventory();
      setRows((inv.rows || []).filter(isTx));
    } catch (e) {
      setRows([]);
      setError(
        isApiUnreachable(e)
          ? "API unreachable — start the demo stack."
          : e instanceof Error
            ? e.message
            : "Failed to load inventory"
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const families = useMemo(() => {
    const s = new Set<string>();
    for (const r of rows) {
      const f = String((r as { transmission_family?: string }).transmission_family || "");
      if (f) s.add(f);
    }
    return Array.from(s).sort();
  }, [rows]);

  const filtered = useMemo(() => {
    const qq = q.trim().toLowerCase();
    return rows.filter((r) => {
      const fam = String((r as { transmission_family?: string }).transmission_family || "");
      if (family && fam !== family) return false;
      const qty = qtyOf(r);
      const level = stockLevel(qty);
      if (stock !== "all" && level !== stock) return false;
      if (!qq) return true;
      const hay = [
        r.sku,
        r.name,
        r.title,
        fam,
        r.location,
        r.location_code,
        r.location_name,
        (r as { bin?: string }).bin,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return hay.includes(qq);
    });
  }, [rows, q, family, stock]);

  return (
    <JpPage
      title="Inventory"
      description="Transmission hard-parts stock by location. Read-only pilot view."
      dense
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
      <div className="mb-4 flex flex-wrap gap-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Filter SKU, name, location…"
          className="h-9 min-w-[220px] flex-1 rounded-md border border-slate-300 bg-white px-3 text-sm"
        />
        <select
          value={family}
          onChange={(e) => setFamily(e.target.value)}
          className="h-9 rounded-md border border-slate-300 bg-white px-2 text-sm"
        >
          <option value="">All families</option>
          {families.map((f) => (
            <option key={f} value={f}>
              {f}
            </option>
          ))}
        </select>
        <select
          value={stock}
          onChange={(e) => setStock(e.target.value as typeof stock)}
          className="h-9 rounded-md border border-slate-300 bg-white px-2 text-sm"
        >
          <option value="all">All stock</option>
          <option value="in">In stock</option>
          <option value="low">Low stock</option>
          <option value="out">Out of stock</option>
        </select>
      </div>

      {error ? (
        <div className="mb-3 rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </div>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
        <Panel>
          {loading ? (
            <EmptyState title="Loading inventory…" />
          ) : filtered.length === 0 ? (
            <EmptyState title="No matching rows" />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b text-[11px] uppercase text-slate-500">
                    <th className="py-2 pr-2 font-medium">SKU</th>
                    <th className="py-2 pr-2 font-medium">Description</th>
                    <th className="py-2 pr-2 font-medium">Family</th>
                    <th className="py-2 pr-2 font-medium">Location</th>
                    <th className="py-2 pr-2 font-medium">Qty</th>
                    <th className="py-2 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((r, i) => {
                    const loc = formatTransmissionLocationLine({
                      location: r.location || r.location_code,
                      location_name: r.location_name,
                      bin: (r as { bin?: string }).bin,
                    });
                    const fam = String(
                      (r as { transmission_family?: string }).transmission_family || "—"
                    );
                    const active =
                      selected?.sku === r.sku && selected?.location_id === r.location_id;
                    return (
                      <tr
                        key={`${r.sku}-${r.location_id}-${i}`}
                        className={`cursor-pointer border-b border-slate-50 hover:bg-slate-50 ${
                          active ? "bg-slate-100" : ""
                        }`}
                        onClick={() => setSelected(r)}
                      >
                        <td className="py-2 pr-2 font-mono text-xs">{r.sku}</td>
                        <td className="py-2 pr-2 text-xs text-slate-700">
                          {r.name || r.title || "—"}
                        </td>
                        <td className="py-2 pr-2 font-mono text-xs">{fam}</td>
                        <td className="py-2 pr-2 text-xs">{loc.title}</td>
                        <td className="py-2 pr-2 tabular-nums font-medium">{qtyOf(r)}</td>
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

        <Panel title="Detail">
          {!selected ? (
            <EmptyState
              title="Select a row"
              body="Click a line to see location and condition detail."
            />
          ) : (
            <div className="space-y-3 text-sm">
              <div className="font-mono text-lg font-semibold">{selected.sku}</div>
              <div className="text-slate-600">{selected.name || selected.title || "—"}</div>
              <StockBadge qty={qtyOf(selected)} />
              <dl className="space-y-2 text-xs">
                <div>
                  <dt className="uppercase text-slate-500">Family</dt>
                  <dd className="font-mono">
                    {String(
                      (selected as { transmission_family?: string }).transmission_family || "—"
                    )}
                  </dd>
                </div>
                <div>
                  <dt className="uppercase text-slate-500">Location</dt>
                  <dd>
                    {
                      formatTransmissionLocationLine({
                        location: selected.location || selected.location_code,
                        location_name: selected.location_name,
                        bin: (selected as { bin?: string }).bin,
                      }).title
                    }
                  </dd>
                </div>
                <div>
                  <dt className="uppercase text-slate-500">Bin</dt>
                  <dd className="font-mono">{(selected as { bin?: string }).bin || "—"}</dd>
                </div>
                <div>
                  <dt className="uppercase text-slate-500">Condition</dt>
                  <dd className="capitalize">
                    {(selected as { condition?: string }).condition || "—"}
                  </dd>
                </div>
                <div>
                  <dt className="uppercase text-slate-500">Qty</dt>
                  <dd className="text-base font-semibold tabular-nums">{qtyOf(selected)}</dd>
                </div>
              </dl>
            </div>
          )}
        </Panel>
      </div>
    </JpPage>
  );
}

export default function InventoryPage() {
  if (isTransmissionDemo()) return <JpInventory />;
  return <InventoryFullPage />;
}
