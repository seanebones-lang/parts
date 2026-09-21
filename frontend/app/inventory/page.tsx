"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  formatTransmissionLocationLine,
  isTransmissionDemo,
} from "@/lib/demo-vertical";
import {
  formatOpsError,
  getActiveQuoteId,
  isApiUnreachable,
  newIdempotencyKey,
  opsAdjust,
  opsAddQuoteLine,
  opsCreateQuote,
  opsGetQuote,
  opsListEvents,
  opsListReservations,
  opsReceive,
  opsReleaseReservation,
  opsReserve,
  opsStock,
  opsTransfer,
  setActiveQuoteId,
  type OpsStockRow,
} from "@/lib/dms-api";
import { EmptyState, JpPage, Panel, StockBadge, stockLevel } from "@/components/jp/ui";
import InventoryFullPage from "./inventory-full";

type FormKind = "receive" | "adjust" | "transfer" | "reserve" | "release" | null;

type StockRow = OpsStockRow & {
  location?: string;
  title?: string;
  category?: string;
};

function qtyOf(row: StockRow): number {
  const q = row.on_hand ?? row.qty;
  return typeof q === "number" && Number.isFinite(q) ? q : 0;
}

function isTx(row: StockRow): boolean {
  const fam = String(row.transmission_family || "");
  const cat = String(row.category || "").toLowerCase();
  const sku = String(row.sku || "");
  if (fam) return true;
  if (cat.includes("transmission")) return true;
  return /6L|4L|6R|10R|8HP/i.test(sku);
}

function locCode(row: StockRow): string {
  return String(row.location_code || row.location || "CHI-N");
}

function humanEvent(ev: any): { title: string; meta: string; when: string } {
  const t = String(ev.event_type || "").toUpperCase();
  const loc = String(ev.location_code || "");
  const locLabel =
    formatTransmissionLocationLine({ location: loc, location_name: undefined }).title || loc;
  const ohB = Number(ev.on_hand_before ?? 0);
  const ohA = Number(ev.on_hand_after ?? 0);
  const rB = Number(ev.reserved_before ?? 0);
  const rA = Number(ev.reserved_after ?? 0);
  const dOh = ohA - ohB;
  const dR = rA - rB;
  const sign = (n: number) => (n > 0 ? `+${n}` : String(n));
  let title = "Inventory change";
  if (t === "RECEIVE") title = `Received ${sign(dOh)}`;
  else if (t === "ADJUST") title = `Adjusted ${sign(dOh)}`;
  else if (t === "TRANSFER_OUT") title = `Moved out ${Math.abs(dOh)}`;
  else if (t === "TRANSFER_IN") title = `Moved in ${sign(dOh)}`;
  else if (t === "RESERVE") title = `Reserved ${Math.abs(dR)}`;
  else if (t === "RELEASE") title = `Released ${Math.abs(dR)}`;
  else if (t === "SALE") title = `Sold ${Math.abs(dOh)}`;
  const bits = [locLabel];
  if (ev.ref_type === "quote" && ev.ref_id) bits.push(`Quote #${ev.ref_id}`);
  if (ev.ref_type === "order" && ev.ref_id) bits.push(`Order #${ev.ref_id}`);
  if (ev.ref_type === "reservation" && ev.ref_id) bits.push(`Hold #${ev.ref_id}`);
  if (ev.notes) bits.push(String(ev.notes));
  if (ev.reason) bits.push(String(ev.reason).replace(/_/g, " "));
  const when = ev.created_at
    ? new Date(String(ev.created_at).endsWith("Z") ? ev.created_at : `${ev.created_at}Z`).toLocaleString()
    : "";
  return { title, meta: bits.filter(Boolean).join(" · "), when };
}

function JpInventory() {
  const [rows, setRows] = useState<StockRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [family, setFamily] = useState("");
  const [stock, setStock] = useState<"all" | "in" | "low" | "out">("all");
  const [selected, setSelected] = useState<StockRow | null>(null);
  const [form, setForm] = useState<FormKind>(null);
  const [busy, setBusy] = useState(false);
  const [formErr, setFormErr] = useState<string | null>(null);
  const [events, setEvents] = useState<any[]>([]);
  const [reservations, setReservations] = useState<any[]>([]);
  const [releaseId, setReleaseId] = useState<number | null>(null);
  const [qty, setQty] = useState("1");
  const [delta, setDelta] = useState("1");
  const [reason, setReason] = useState("physical_count");
  const [notes, setNotes] = useState("");
  const [reference, setReference] = useState("");
  const [toLoc, setToLoc] = useState("OHARE");
  const [customer, setCustomer] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const inv = await opsStock();
      const next = ((inv.rows || []) as StockRow[]).filter(isTx).map((r) => ({
        ...r,
        qty: r.on_hand ?? r.qty,
        location: r.location_code,
      }));
      setRows(next);
      if (selected?.sku) {
        const match = next.find(
          (r) => r.sku === selected.sku && String(r.location_id) === String(selected.location_id)
        );
        if (match) setSelected(match);
      }
    } catch (e) {
      setRows([]);
      setError(
        isApiUnreachable(e)
          ? "API unreachable — start the demo stack."
          : formatOpsError(e, "Failed to load inventory")
      );
    } finally {
      setLoading(false);
    }
  }, [selected?.sku, selected?.location_id]);

  const loadDetail = useCallback(async (row: StockRow | null) => {
    if (!row?.sku) {
      setEvents([]);
      setReservations([]);
      return;
    }
    try {
      const [ev, res] = await Promise.all([
        opsListEvents(String(row.sku), 10),
        opsListReservations({
          sku: String(row.sku),
          location: locCode(row),
          status: "active",
          limit: 20,
        }),
      ]);
      setEvents(ev.events || []);
      setReservations(res.reservations || []);
    } catch {
      setEvents([]);
      setReservations([]);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    void loadDetail(selected);
  }, [selected, loadDetail]);

  const families = useMemo(() => {
    const s = new Set<string>();
    for (const r of rows) {
      const f = String(r.transmission_family || "");
      if (f) s.add(f);
    }
    return Array.from(s).sort();
  }, [rows]);

  const locations = useMemo(() => {
    const s = new Set<string>();
    for (const r of rows) {
      const c = locCode(r);
      if (c) s.add(c);
    }
    s.add("CHI-N");
    s.add("OHARE");
    return Array.from(s).sort();
  }, [rows]);

  const filtered = useMemo(() => {
    const qq = q.trim().toLowerCase();
    return rows.filter((r) => {
      const fam = String(r.transmission_family || "");
      if (family && fam !== family) return false;
      const avail =
        typeof r.available === "number"
          ? r.available
          : Math.max(0, qtyOf(r) - Number(r.reserved || 0));
      const level = stockLevel(avail);
      if (stock !== "all" && level !== stock) return false;
      if (!qq) return true;
      const hay = [r.sku, r.name, r.title, fam, r.location, r.location_code, r.location_name, r.bin]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return hay.includes(qq);
    });
  }, [rows, q, family, stock]);

  const openForm = (kind: FormKind, resId?: number) => {
    setForm(kind);
    setFormErr(null);
    setMsg(null);
    setQty("1");
    setDelta("1");
    setReason("physical_count");
    setNotes("");
    setReference("");
    setToLoc(locations.find((c) => c !== (selected ? locCode(selected) : "")) || "OHARE");
    setCustomer("");
    setReleaseId(resId ?? null);
  };

  const closeForm = () => {
    setForm(null);
    setFormErr(null);
    setBusy(false);
    setReleaseId(null);
  };

  const submitForm = async () => {
    if (!selected || !form) return;
    setBusy(true);
    setFormErr(null);
    setMsg(null);
    const key = newIdempotencyKey(form);
    const sku = String(selected.sku);
    const location = locCode(selected);
    try {
      if (form === "receive") {
        const n = Number(qty);
        if (!Number.isFinite(n) || n <= 0) throw new Error("Enter a positive quantity.");
        await opsReceive({
          sku,
          location,
          qty: n,
          reference: reference.trim(),
          notes: notes.trim(),
          idempotency_key: key,
        });
        setMsg(`Received ${n} unit${n === 1 ? "" : "s"} of ${sku}.`);
      } else if (form === "adjust") {
        const n = Number(delta);
        if (!Number.isFinite(n) || n === 0) throw new Error("Enter a non-zero adjustment.");
        await opsAdjust({
          sku,
          location,
          delta: n,
          reason,
          notes: notes.trim(),
          idempotency_key: key,
        });
        setMsg(`Stock adjusted ${n > 0 ? "+" : ""}${n} for ${sku}.`);
      } else if (form === "transfer") {
        const n = Number(qty);
        if (!Number.isFinite(n) || n <= 0) throw new Error("Enter a positive quantity.");
        if (!toLoc || toLoc === location) throw new Error("Choose a different destination location.");
        await opsTransfer({
          sku,
          from_location: location,
          to_location: toLoc,
          qty: n,
          notes: notes.trim(),
          idempotency_key: key,
        });
        setMsg(
          `Moved ${n} of ${sku} to ${formatTransmissionLocationLine({ location: toLoc }).title}.`
        );
      } else if (form === "reserve") {
        const n = Number(qty);
        if (!Number.isFinite(n) || n <= 0) throw new Error("Enter a positive quantity.");
        const avail =
          typeof selected.available === "number"
            ? selected.available
            : Math.max(0, qtyOf(selected) - Number(selected.reserved || 0));
        if (n > avail) {
          throw new Error(`Only ${avail} units are available. You attempted to reserve ${n}.`);
        }
        await opsReserve({
          sku,
          location,
          qty: n,
          notes: [customer.trim() && `Customer: ${customer.trim()}`, notes.trim()]
            .filter(Boolean)
            .join(" · "),
          idempotency_key: key,
        });
        setMsg(`Reserved ${n} of ${sku}.`);
      } else if (form === "release") {
        if (!releaseId) throw new Error("No reservation selected.");
        await opsReleaseReservation(releaseId, { idempotency_key: key, notes: notes.trim() });
        setMsg("Reservation released.");
      }
      closeForm();
      await load();
      if (selected) await loadDetail(selected);
    } catch (e) {
      setFormErr(formatOpsError(e));
    } finally {
      setBusy(false);
    }
  };

  const addToQuote = async () => {
    if (!selected?.sku) return;
    setBusy(true);
    setError(null);
    setMsg(null);
    try {
      let qid = getActiveQuoteId();
      let created = false;
      if (qid) {
        try {
          const qq = (await opsGetQuote(qid)) as any;
          if (!["draft", "open"].includes(String(qq.status || ""))) {
            qid = null;
          }
        } catch {
          qid = null;
        }
      }
      if (!qid) {
        const qq = (await opsCreateQuote({ customer_label: "Walk-in" })) as any;
        qid = Number(qq.id);
        created = true;
        setActiveQuoteId(qid);
      }
      await opsAddQuoteLine(qid!, {
        sku: String(selected.sku),
        location: locCode(selected),
        qty: 1,
      });
      setActiveQuoteId(qid!);
      setMsg(
        created
          ? `Created quote and added ${selected.sku}.`
          : `Added ${selected.sku} to the active quote.`
      );
      window.location.href = `/quotes?focus=${qid}`;
    } catch (e) {
      setError(formatOpsError(e, "Could not add to quote"));
    } finally {
      setBusy(false);
    }
  };

  const onHand = selected ? (selected.on_hand ?? qtyOf(selected)) : 0;
  const reserved = selected ? Number(selected.reserved || 0) : 0;
  const available =
    selected && typeof selected.available === "number"
      ? selected.available
      : Math.max(0, onHand - reserved);

  return (
    <JpPage
      title="Inventory"
      description="Warehouse and counter stock by location — receive, adjust, move, reserve, and release."
      fullBleed
      actions={
        <button
          type="button"
          onClick={() => void load()}
          className="h-10 rounded-md border border-slate-300 bg-white px-4 text-sm font-semibold text-slate-800"
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
          className="h-10 min-w-[240px] flex-1 rounded-md border border-slate-300 bg-white px-3 text-sm"
        />
        <select
          value={family}
          onChange={(e) => setFamily(e.target.value)}
          className="h-10 rounded-md border border-slate-300 bg-white px-2 text-sm"
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
          className="h-10 rounded-md border border-slate-300 bg-white px-2 text-sm"
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
      {msg ? (
        <div className="mb-3 rounded border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900">
          {msg}
        </div>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.4fr)_minmax(360px,0.85fr)]">
        <Panel flush title="Stock lines">
          {loading ? (
            <div className="p-5"><EmptyState title="Loading inventory…" /></div>
          ) : filtered.length === 0 ? (
            <div className="p-5"><EmptyState title="No matching rows" body="Adjust filters or receive stock for a SKU." /></div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[900px] text-left text-sm">
                <thead className="bg-slate-50">
                  <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                    <th className="px-4 py-2.5 font-semibold">SKU</th>
                    <th className="px-4 py-2.5 font-semibold">Description</th>
                    <th className="px-4 py-2.5 font-semibold">Family</th>
                    <th className="px-4 py-2.5 font-semibold">Location</th>
                    <th className="px-4 py-2.5 text-right font-semibold">On Hand</th>
                    <th className="px-4 py-2.5 text-right font-semibold">Reserved</th>
                    <th className="px-4 py-2.5 text-right font-semibold">Available</th>
                    <th className="px-4 py-2.5 font-semibold">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((r, i) => {
                    const loc = formatTransmissionLocationLine({
                      location: r.location || r.location_code,
                      location_name: r.location_name,
                      bin: r.bin,
                    });
                    const fam = String(r.transmission_family || "—");
                    const active =
                      selected?.sku === r.sku && String(selected?.location_id) === String(r.location_id);
                    const avail =
                      typeof r.available === "number"
                        ? r.available
                        : Math.max(0, qtyOf(r) - Number(r.reserved || 0));
                    return (
                      <tr
                        key={`${r.sku}-${r.location_id}-${i}`}
                        className={`cursor-pointer border-b border-slate-100 hover:bg-slate-50 ${
                          active ? "bg-slate-100 ring-1 ring-inset ring-slate-300" : ""
                        }`}
                        onClick={() => setSelected(r)}
                      >
                        <td className="px-4 py-2.5 font-mono text-[13px] font-medium text-slate-900">{r.sku}</td>
                        <td className="px-4 py-2.5 text-[13px] text-slate-700">{r.name || r.title || "—"}</td>
                        <td className="px-4 py-2.5 font-mono text-[13px]">{fam}</td>
                        <td className="px-4 py-2.5 text-[13px]">{loc.title}</td>
                        <td className="px-4 py-2.5 text-right tabular-nums text-[13px] font-medium">{r.on_hand ?? qtyOf(r)}</td>
                        <td className="px-4 py-2.5 text-right tabular-nums text-[13px]">{r.reserved ?? 0}</td>
                        <td className="px-4 py-2.5 text-right tabular-nums text-[13px] font-semibold">{avail}</td>
                        <td className="px-4 py-2.5">
                          <StockBadge qty={avail} />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Panel>

        <div className="space-y-4">
          <Panel title="Detail">
            {!selected ? (
              <EmptyState title="Select an inventory line" body="Click a row to view stock details and actions for that location." />
            ) : (
              <div className="space-y-4 text-sm">
                <div>
                  <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Part</div>
                  <div className="mt-1 font-mono text-xl font-semibold text-slate-900">{selected.sku}</div>
                  <div className="mt-1 text-[15px] text-slate-600">{selected.name || selected.title || "—"}</div>
                  {selected.transmission_family ? (
                    <div className="mt-1 text-xs text-slate-500">Family · {String(selected.transmission_family)}{selected.condition ? ` · ${String(selected.condition)}` : ""}</div>
                  ) : null}
                </div>
                <StockBadge qty={available} />
                <div>
                  <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Stock</div>
                  <dl className="grid grid-cols-3 gap-2 text-center">
                    <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
                      <dt className="text-xs font-semibold uppercase text-slate-500">On Hand</dt>
                      <dd className="mt-1 text-2xl font-semibold tabular-nums">{onHand}</dd>
                    </div>
                    <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
                      <dt className="text-xs font-semibold uppercase text-slate-500">Reserved</dt>
                      <dd className="mt-1 text-2xl font-semibold tabular-nums">{reserved}</dd>
                    </div>
                    <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
                      <dt className="text-xs font-semibold uppercase text-slate-500">Available</dt>
                      <dd className="mt-1 text-2xl font-semibold tabular-nums text-emerald-800">{available}</dd>
                    </div>
                  </dl>
                </div>
                <div>
                  <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Location</div>
                  <div className="mt-1 text-[15px] font-medium text-slate-800">
                    {
                      formatTransmissionLocationLine({
                        location: selected.location || selected.location_code,
                        location_name: selected.location_name,
                        bin: selected.bin,
                      }).title
                    }
                  </div>
                  <div className="text-xs text-slate-500">
                    {selected.bin ? `Bin ${selected.bin}` : "No bin"}
                    {selected.condition ? ` · ${String(selected.condition)}` : ""}
                  </div>
                </div>

                <div>
                  <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Actions</div>
                  <div className="flex flex-wrap gap-2 border-t border-slate-100 pt-3">
                  <button type="button" disabled={busy} className="h-10 rounded-md bg-slate-900 px-3 text-sm font-semibold text-white disabled:opacity-50" onClick={() => openForm("receive")}>Receive</button>
                  <button type="button" disabled={busy} className="h-10 rounded-md border border-slate-300 px-3 text-sm font-semibold disabled:opacity-50" onClick={() => openForm("adjust")}>Adjust</button>
                  <button type="button" disabled={busy} className="h-10 rounded-md border border-slate-300 px-3 text-sm font-semibold disabled:opacity-50" onClick={() => openForm("transfer")}>Move</button>
                  <button type="button" disabled={busy || available <= 0} className="h-10 rounded-md border border-amber-300 bg-amber-50 px-3 text-sm font-semibold text-amber-950 disabled:opacity-50" onClick={() => openForm("reserve")}>Reserve</button>
                  <button type="button" disabled={busy} className="h-10 rounded-md border border-slate-300 px-3 text-sm font-semibold disabled:opacity-50" onClick={() => void addToQuote()}>Add to Quote</button>
                  </div>
                </div>

                {form ? (
                  <div className="mt-2 space-y-2 rounded-md border border-slate-200 bg-white p-3">
                    <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      {form === "receive" && "Receive stock"}
                      {form === "adjust" && "Adjust stock"}
                      {form === "transfer" && "Transfer stock"}
                      {form === "reserve" && "Reserve inventory"}
                      {form === "release" && "Release reservation"}
                    </div>
                    <div className="text-xs text-slate-600">
                      {selected.sku} · {formatTransmissionLocationLine({ location: locCode(selected) }).title}
                    </div>
                    <div className="grid grid-cols-3 gap-1 text-center text-[11px]">
                      <div className="rounded bg-slate-50 p-1">On hand {onHand}</div>
                      <div className="rounded bg-slate-50 p-1">Reserved {reserved}</div>
                      <div className="rounded bg-slate-50 p-1">Available {available}</div>
                    </div>
                    {form === "receive" || form === "transfer" || form === "reserve" ? (
                      <label className="block text-xs">Quantity
                        <input type="number" min={1} value={qty} onChange={(e) => setQty(e.target.value)} className="mt-1 h-9 w-full rounded-md border px-2 text-sm" />
                      </label>
                    ) : null}
                    {form === "adjust" ? (
                      <>
                        <label className="block text-xs">Change by (use negative to reduce)
                          <input type="number" value={delta} onChange={(e) => setDelta(e.target.value)} className="mt-1 h-9 w-full rounded-md border px-2 text-sm" />
                        </label>
                        <label className="block text-xs">Reason
                          <select value={reason} onChange={(e) => setReason(e.target.value)} className="mt-1 h-9 w-full rounded-md border px-2 text-sm">
                            <option value="physical_count">Physical count correction</option>
                            <option value="damaged">Damaged</option>
                            <option value="scrapped">Scrapped</option>
                            <option value="found">Found inventory</option>
                            <option value="data_correction">Data correction</option>
                            <option value="other">Other</option>
                          </select>
                        </label>
                      </>
                    ) : null}
                    {form === "transfer" ? (
                      <label className="block text-xs">Destination
                        <select value={toLoc} onChange={(e) => setToLoc(e.target.value)} className="mt-1 h-9 w-full rounded-md border px-2 text-sm">
                          {locations.filter((c) => c !== locCode(selected)).map((c) => (
                            <option key={c} value={c}>{formatTransmissionLocationLine({ location: c }).title} ({c})</option>
                          ))}
                        </select>
                      </label>
                    ) : null}
                    {form === "reserve" ? (
                      <label className="block text-xs">Customer / reference (optional)
                        <input value={customer} onChange={(e) => setCustomer(e.target.value)} className="mt-1 h-9 w-full rounded-md border px-2 text-sm" placeholder="Shop name or ticket #" />
                      </label>
                    ) : null}
                    {form === "receive" ? (
                      <label className="block text-xs">Reference (PO / packing slip)
                        <input value={reference} onChange={(e) => setReference(e.target.value)} className="mt-1 h-9 w-full rounded-md border px-2 text-sm" />
                      </label>
                    ) : null}
                    {form !== "release" ? (
                      <label className="block text-xs">Note (optional)
                        <input value={notes} onChange={(e) => setNotes(e.target.value)} className="mt-1 h-9 w-full rounded-md border px-2 text-sm" />
                      </label>
                    ) : (
                      <p className="text-xs text-slate-600">Release hold #{releaseId}? Available quantity will increase immediately.</p>
                    )}
                    {formErr ? (
                      <div className="rounded border border-red-200 bg-red-50 px-2 py-1.5 text-xs text-red-800">{formErr}</div>
                    ) : null}
                    <div className="flex gap-2 pt-1">
                      <button type="button" disabled={busy} onClick={() => void submitForm()} className="rounded-md bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50">{busy ? "Working…" : "Confirm"}</button>
                      <button type="button" disabled={busy} onClick={closeForm} className="rounded-md border px-3 py-1.5 text-xs">Cancel</button>
                    </div>
                  </div>
                ) : null}

                {reservations.length > 0 ? (
                  <div className="border-t pt-3">
                    <div className="mb-2 text-[11px] font-semibold uppercase text-slate-500">Active reservations</div>
                    <ul className="space-y-2">
                      {reservations.map((r) => (
                        <li key={r.id} className="flex items-start justify-between gap-2 rounded border bg-amber-50/60 px-2 py-1.5 text-xs">
                          <div>
                            <div className="font-medium">Hold #{r.id} · qty {r.qty}</div>
                            <div className="text-slate-600">
                              {[r.quote_number && `Quote ${r.quote_number}`, r.order_number && `Order ${r.order_number}`, r.notes].filter(Boolean).join(" · ") || "Direct hold"}
                            </div>
                            <div className="text-[10px] text-slate-500">
                              {r.created_at ? new Date(String(r.created_at).endsWith("Z") ? r.created_at : `${r.created_at}Z`).toLocaleString() : ""}
                            </div>
                          </div>
                          <button type="button" disabled={busy} className="shrink-0 rounded border border-amber-400 bg-white px-2 py-1 text-[11px] font-medium" onClick={() => openForm("release", Number(r.id))}>Release</button>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </div>
            )}
          </Panel>

          {selected ? (
            <Panel title="Recent movement">
              {events.length === 0 ? (
                <EmptyState title="No events yet" body="Receive, move, reserve, or sell to build history." />
              ) : (
                <ul className="space-y-2 text-xs">
                  {events.map((ev) => {
                    const h = humanEvent(ev);
                    return (
                      <li key={ev.id} className="rounded border border-slate-100 bg-slate-50 px-2 py-1.5">
                        <div className="font-medium text-slate-900">{h.title}</div>
                        <div className="text-slate-600">{h.meta}</div>
                        <div className="text-[10px] text-slate-500">{h.when}</div>
                      </li>
                    );
                  })}
                </ul>
              )}
            </Panel>
          ) : null}
        </div>
      </div>
    </JpPage>
  );
}

export default function InventoryPage() {
  if (isTransmissionDemo()) return <JpInventory />;
  return <InventoryFullPage />;
}
