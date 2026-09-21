"use client";

import { useCallback, useEffect, useState } from "react";
import { EmptyState, JpPage, Panel } from "@/components/jp/ui";
import {
  formatOpsError,
  getActiveQuoteId,
  isApiUnreachable,
  newIdempotencyKey,
  opsAddQuoteLine,
  opsCancelOrder,
  opsCancelQuote,
  opsCompleteOrder,
  opsConvertQuote,
  opsCreateQuote,
  opsGetQuote,
  opsListOrders,
  opsListQuotes,
  opsRemoveQuoteLine,
  opsReserveQuote,
  opsUpdateQuoteLine,
  setActiveQuoteId,
} from "@/lib/dms-api";

type Tab = "quotes" | "orders";

function money(n?: number) {
  if (n == null || !Number.isFinite(n)) return "—";
  return `$${n.toFixed(2)}`;
}

function centsFromDollars(raw: string): number | null {
  const t = raw.trim().replace(/[$,]/g, "");
  if (!t) return null;
  const n = Number(t);
  if (!Number.isFinite(n) || n < 0) return null;
  return Math.round(n * 100);
}

function statusLabel(s?: string) {
  const m: Record<string, string> = {
    draft: "Draft",
    open: "Open",
    reserved: "Reserved",
    converted: "Converted",
    cancelled: "Cancelled",
    completed: "Completed",
  };
  return m[String(s || "")] || s || "—";
}

function isEditableQuote(status?: string) {
  return ["draft", "open"].includes(String(status || ""));
}

export default function QuotesOrdersPage() {
  const [tab, setTab] = useState<Tab>("quotes");
  const [quotes, setQuotes] = useState<any[]>([]);
  const [orders, setOrders] = useState<any[]>([]);
  const [selectedQ, setSelectedQ] = useState<any | null>(null);
  const [selectedO, setSelectedO] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [customer, setCustomer] = useState("Lake Front Transmissions");
  const [msg, setMsg] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<{
    title: string;
    body: string;
    action: () => Promise<void>;
  } | null>(null);
  const [addSku, setAddSku] = useState("");
  const [addLoc, setAddLoc] = useState("CHI-N");
  const [lineEdits, setLineEdits] = useState<Record<number, { qty: string; price: string }>>({});

  const load = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      const [q, o] = await Promise.all([opsListQuotes(), opsListOrders()]);
      setQuotes(q.quotes || []);
      setOrders(o.orders || []);
      if (selectedQ?.id) {
        const match = (q.quotes || []).find((x: any) => x.id === selectedQ.id);
        if (match) {
          setSelectedQ(match);
          setActiveQuoteId(Number(match.id));
        }
      }
      if (selectedO?.id) {
        const match = (o.orders || []).find((x: any) => x.id === selectedO.id);
        if (match) setSelectedO(match);
      }
    } catch (e) {
      setErr(
        isApiUnreachable(e)
          ? "API unreachable — start the demo stack."
          : formatOpsError(e, "Failed to load")
      );
    } finally {
      setLoading(false);
    }
  }, [selectedQ?.id, selectedO?.id]);

  useEffect(() => {
    void load();
  }, [load]);

  // Deep-link: add_sku to active/existing quote; focus=id
  useEffect(() => {
    if (typeof window === "undefined") return;
    const sp = new URLSearchParams(window.location.search);
    const sku = sp.get("add_sku");
    const location = sp.get("location") || "CHI-N";
    const price = sp.get("price_cents");
    const focus = sp.get("focus");
    const forceNew = sp.get("new") === "1";

    void (async () => {
      setBusy(true);
      setErr(null);
      try {
        if (focus) {
          const id = Number(focus);
          if (Number.isFinite(id)) {
            const q = await opsGetQuote(id);
            setSelectedQ(q);
            setActiveQuoteId(id);
            setTab("quotes");
          }
        }
        if (sku) {
          let qid: number | null = forceNew ? null : getActiveQuoteId();
          if (!qid && !forceNew) {
            const fromFocus = focus ? Number(focus) : null;
            if (fromFocus && Number.isFinite(fromFocus)) qid = fromFocus;
          }
          if (qid) {
            try {
              const existing = (await opsGetQuote(qid)) as any;
              if (!isEditableQuote(existing.status)) qid = null;
            } catch {
              qid = null;
            }
          }
          let updated: any;
          if (!qid) {
            const q = (await opsCreateQuote({
              customer_label: customer || "Walk-in",
            })) as any;
            qid = Number(q.id);
            updated = await opsAddQuoteLine(qid, {
              sku,
              location,
              qty: 1,
              unit_price_cents: price ? Number(price) : undefined,
            });
            setMsg(`Created ${updated.quote_number} and added ${sku}`);
          } else {
            updated = await opsAddQuoteLine(qid, {
              sku,
              location,
              qty: 1,
              unit_price_cents: price ? Number(price) : undefined,
            });
            setMsg(`Added ${sku} to ${updated.quote_number}`);
          }
          setSelectedQ(updated);
          setActiveQuoteId(Number(updated.id));
          setTab("quotes");
          await load();
        }
        if (sku || focus) window.history.replaceState({}, "", "/quotes");
      } catch (e) {
        setErr(formatOpsError(e, "Could not open quote"));
      } finally {
        setBusy(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!selectedQ?.lines) {
      setLineEdits({});
      return;
    }
    const next: Record<number, { qty: string; price: string }> = {};
    for (const ln of selectedQ.lines) {
      next[ln.id] = {
        qty: String(ln.qty ?? 1),
        price:
          ln.unit_price != null
            ? Number(ln.unit_price).toFixed(2)
            : ((Number(ln.unit_price_cents || 0) || 0) / 100).toFixed(2),
      };
    }
    setLineEdits(next);
  }, [selectedQ?.id, selectedQ?.status, selectedQ?.lines?.length]);

  const run = async (fn: () => Promise<unknown>, ok?: string) => {
    setBusy(true);
    setErr(null);
    setMsg(null);
    try {
      const res = await fn();
      if (ok) setMsg(ok);
      await load();
      return res;
    } catch (e) {
      setErr(formatOpsError(e, "Action failed"));
      return null;
    } finally {
      setBusy(false);
      setConfirm(null);
    }
  };

  const saveLine = async (lineId: number) => {
    if (!selectedQ || !isEditableQuote(selectedQ.status)) return;
    const ed = lineEdits[lineId];
    if (!ed) return;
    const qty = Number(ed.qty);
    if (!Number.isFinite(qty) || qty < 1) {
      setErr("Quantity must be at least 1.");
      return;
    }
    const cents = centsFromDollars(ed.price);
    if (cents == null) {
      setErr("Enter a valid unit price (for example 245.00).");
      return;
    }
    await run(async () => {
      const q = await opsUpdateQuoteLine(selectedQ.id, lineId, {
        qty,
        unit_price_cents: cents,
      });
      setSelectedQ(q);
      return q;
    }, "Line updated");
  };

  const removeLine = async (lineId: number) => {
    if (!selectedQ || !isEditableQuote(selectedQ.status)) return;
    setConfirm({
      title: "Remove line",
      body: "Remove this part from the quote?",
      action: async () => {
        await run(async () => {
          const q = await opsRemoveQuoteLine(selectedQ.id, lineId);
          setSelectedQ(q);
          return q;
        }, "Line removed");
      },
    });
  };

  const addPartToSelected = async () => {
    if (!selectedQ || !isEditableQuote(selectedQ.status)) {
      setErr("Select an open quote before adding parts, or create a new quote.");
      return;
    }
    const sku = addSku.trim();
    if (!sku) {
      setErr("Enter a SKU to add.");
      return;
    }
    await run(async () => {
      const q = (await opsAddQuoteLine(selectedQ.id, {
        sku,
        location: addLoc || "CHI-N",
        qty: 1,
      })) as any;
      setSelectedQ(q);
      setActiveQuoteId(Number(q.id));
      setAddSku("");
      return q;
    }, `Added ${sku}`);
  };

  return (
    <JpPage
      title="Quotes & Orders"
      description="Create multi-line quotes, reserve inventory, convert to orders, and complete sales."
      fullBleed
      actions={
        <button
          type="button"
          disabled={busy}
          className="h-10 rounded-md bg-slate-900 px-4 text-sm font-semibold text-white disabled:opacity-50"
          onClick={() =>
            void run(async () => {
              const q = await opsCreateQuote({ customer_label: customer || "Walk-in" });
              setSelectedQ(q);
              setActiveQuoteId(Number((q as any).id));
              setTab("quotes");
              return q;
            }, "Quote created")
          }
        >
          New Quote
        </button>
      }
    >
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <input
          value={customer}
          onChange={(e) => setCustomer(e.target.value)}
          placeholder="Customer / reference"
          className="h-10 rounded-md border border-slate-300 bg-white px-3 text-sm"
        />
        <div className="flex rounded-md border border-slate-300 bg-white text-sm font-medium">
          {(["quotes", "orders"] as Tab[]).map((t) => (
            <button
              key={t}
              type="button"
              className={`px-4 py-2 capitalize ${
                tab === t ? "bg-slate-900 text-white" : "text-slate-700 hover:bg-slate-50"
              }`}
              onClick={() => setTab(t)}
            >
              {t}
            </button>
          ))}
        </div>
        <button type="button" className="h-10 rounded-md border border-slate-300 px-4 text-sm font-semibold" onClick={() => void load()}>
          Refresh
        </button>
      </div>

      {err ? (
        <div className="mb-3 rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{err}</div>
      ) : null}
      {msg ? (
        <div className="mb-3 rounded border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900">
          {msg}
        </div>
      ) : null}

      {confirm ? (
        <div className="mb-3 rounded-lg border border-slate-300 bg-white p-4 text-sm shadow-sm">
          <div className="text-base font-semibold">{confirm.title}</div>
          <p className="mt-1 text-slate-600">{confirm.body}</p>
          <div className="mt-3 flex gap-2">
            <button
              type="button"
              disabled={busy}
              className="h-10 rounded-md bg-slate-900 px-4 text-sm font-semibold text-white disabled:opacity-50"
              onClick={() => void confirm.action()}
            >
              {busy ? "Working…" : "Confirm"}
            </button>
            <button
              type="button"
              disabled={busy}
              className="h-10 rounded-md border border-slate-300 px-4 text-sm font-medium"
              onClick={() => setConfirm(null)}
            >
              Cancel
            </button>
          </div>
        </div>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(420px,1.1fr)]">
        <Panel flush title={tab === "quotes" ? "Quotes" : "Orders"}>
          {loading ? (
            <div className="p-5"><EmptyState title="Loading…" /></div>
          ) : tab === "quotes" ? (
            quotes.length === 0 ? (
              <div className="p-5"><EmptyState title="No quotes yet" body="Create a quote or add a part from Parts Search." /></div>
            ) : (
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead>
                  <tr className="border-b text-[11px] uppercase text-slate-500">
                    <th className="py-2">Number</th>
                    <th className="py-2">Customer</th>
                    <th className="py-2">Status</th>
                    <th className="py-2">Items</th>
                    <th className="py-2">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {quotes.map((q) => (
                    <tr
                      key={q.id}
                      className={`cursor-pointer border-b border-slate-50 hover:bg-slate-50 ${
                        selectedQ?.id === q.id ? "bg-slate-100" : ""
                      }`}
                      onClick={() => {
                        setSelectedQ(q);
                        if (isEditableQuote(q.status)) setActiveQuoteId(Number(q.id));
                      }}
                    >
                      <td className="py-2 font-mono text-xs">{q.quote_number}</td>
                      <td className="py-2">{q.customer_label}</td>
                      <td className="py-2">{statusLabel(q.status)}</td>
                      <td className="py-2">{(q.lines || []).length}</td>
                      <td className="py-2 tabular-nums">{money(q.total)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )
          ) : orders.length === 0 ? (
            <EmptyState title="No orders yet" body="Convert a reserved quote to create an order." />
          ) : (
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b text-[11px] uppercase text-slate-500">
                  <th className="py-2">Number</th>
                  <th className="py-2">Customer</th>
                  <th className="py-2">Status</th>
                  <th className="py-2">Items</th>
                  <th className="py-2">Total</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((o) => (
                  <tr
                    key={o.id}
                    className={`cursor-pointer border-b border-slate-50 hover:bg-slate-50 ${
                      selectedO?.id === o.id ? "bg-slate-100" : ""
                    }`}
                    onClick={() => setSelectedO(o)}
                  >
                    <td className="py-2 font-mono text-xs">{o.order_number || o.id}</td>
                    <td className="py-2">{o.customer_label || o.customer_name}</td>
                    <td className="py-2">{statusLabel(o.status)}</td>
                    <td className="py-2">{(o.lines || []).length}</td>
                    <td className="py-2 tabular-nums">{money(o.total)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Panel>

        <Panel title="Detail">
          {tab === "quotes" && selectedQ ? (
            <div className="space-y-3 text-sm">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="font-mono text-lg font-semibold">{selectedQ.quote_number}</div>
                  <div>{selectedQ.customer_label}</div>
                  <div className="text-xs text-slate-500">{statusLabel(selectedQ.status)}</div>
                </div>
                {isEditableQuote(selectedQ.status) ? (
                  <span className="rounded bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold uppercase text-emerald-800">
                    Editable
                  </span>
                ) : (
                  <span className="rounded bg-slate-100 px-2 py-0.5 text-[10px] font-semibold uppercase text-slate-600">
                    Read-only
                  </span>
                )}
              </div>

              {selectedQ.status === "reserved" ? (
                <div className="rounded border border-amber-200 bg-amber-50 px-2 py-1.5 text-xs text-amber-950">
                  Inventory is on hold. Cancel the quote (or convert to order) before changing lines.
                </div>
              ) : null}

              <ul className="space-y-3 border-t pt-2">
                {(selectedQ.lines || []).map((ln: any) => {
                  const ed = lineEdits[ln.id] || {
                    qty: String(ln.qty),
                    price: String(ln.unit_price ?? 0),
                  };
                  return (
                    <li key={ln.id} className="rounded border border-slate-100 bg-slate-50 p-2 text-xs">
                      <div className="font-mono font-medium">{ln.sku}</div>
                      <div className="text-slate-500">{ln.location_code}</div>
                      {isEditableQuote(selectedQ.status) ? (
                        <div className="mt-2 grid grid-cols-[1fr_1fr_auto] gap-2">
                          <label>
                            Qty
                            <input
                              type="number"
                              min={1}
                              value={ed.qty}
                              onChange={(e) =>
                                setLineEdits((prev) => ({
                                  ...prev,
                                  [ln.id]: { ...ed, qty: e.target.value },
                                }))
                              }
                              className="mt-0.5 h-8 w-full rounded border px-2"
                            />
                          </label>
                          <label>
                            Unit $
                            <input
                              value={ed.price}
                              onChange={(e) =>
                                setLineEdits((prev) => ({
                                  ...prev,
                                  [ln.id]: { ...ed, price: e.target.value },
                                }))
                              }
                              className="mt-0.5 h-8 w-full rounded border px-2"
                            />
                          </label>
                          <div className="flex flex-col justify-end gap-1">
                            <button
                              type="button"
                              disabled={busy}
                              className="rounded bg-slate-900 px-2 py-1 text-[11px] font-semibold text-white disabled:opacity-50"
                              onClick={() => void saveLine(ln.id)}
                            >
                              Save
                            </button>
                            <button
                              type="button"
                              disabled={busy}
                              className="rounded border px-2 py-1 text-[11px] disabled:opacity-50"
                              onClick={() => void removeLine(ln.id)}
                            >
                              Remove
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div className="mt-1 flex justify-between">
                          <span>
                            qty {ln.qty} · {money(ln.unit_price)}
                          </span>
                          <span className="font-medium tabular-nums">{money(ln.line_total)}</span>
                        </div>
                      )}
                    </li>
                  );
                })}
              </ul>

              {isEditableQuote(selectedQ.status) ? (
                <div className="rounded border border-dashed border-slate-300 p-2">
                  <div className="mb-1 text-[11px] font-semibold uppercase text-slate-500">
                    Add another part
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <input
                      value={addSku}
                      onChange={(e) => setAddSku(e.target.value)}
                      placeholder="SKU"
                      className="h-8 min-w-[120px] flex-1 rounded border px-2 text-xs font-mono"
                    />
                    <select
                      value={addLoc}
                      onChange={(e) => setAddLoc(e.target.value)}
                      className="h-8 rounded border px-2 text-xs"
                    >
                      <option value="CHI-N">Main Warehouse</option>
                      <option value="OHARE">Front Counter</option>
                    </select>
                    <button
                      type="button"
                      disabled={busy}
                      className="rounded bg-slate-800 px-2 py-1 text-xs font-semibold text-white disabled:opacity-50"
                      onClick={() => void addPartToSelected()}
                    >
                      Add
                    </button>
                  </div>
                  <p className="mt-1 text-[10px] text-slate-500">
                    Or use Parts Search → Add to quote (uses this active quote).
                  </p>
                </div>
              ) : null}

              <div className="border-t pt-2 font-semibold">Total {money(selectedQ.total)}</div>
              <div className="flex flex-wrap gap-2">
                {isEditableQuote(selectedQ.status) ? (
                  <button
                    type="button"
                    disabled={busy}
                    className="rounded-md bg-amber-500 px-3 py-1.5 text-xs font-semibold text-amber-950 disabled:opacity-50"
                    onClick={() =>
                      setConfirm({
                        title: "Reserve inventory",
                        body: "Hold available stock for every line on this quote?",
                        action: async () => {
                          const key = newIdempotencyKey("quote-reserve");
                          await run(async () => {
                            const r = await opsReserveQuote(selectedQ.id, {
                              idempotency_key: key,
                            });
                            setSelectedQ(r);
                            return r;
                          }, "Inventory reserved for quote");
                        },
                      })
                    }
                  >
                    Reserve inventory
                  </button>
                ) : null}
                {selectedQ.status === "reserved" ? (
                  <button
                    type="button"
                    disabled={busy}
                    className="rounded-md bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
                    onClick={() =>
                      setConfirm({
                        title: "Convert to order",
                        body: "Create an open order from this reserved quote?",
                        action: async () => {
                          const key = newIdempotencyKey("quote-convert");
                          await run(async () => {
                            const r = await opsConvertQuote(selectedQ.id, {
                              idempotency_key: key,
                            });
                            setSelectedO(r);
                            setTab("orders");
                            return r;
                          }, "Order created from quote");
                        },
                      })
                    }
                  >
                    Convert to order
                  </button>
                ) : null}
                {!["converted", "cancelled"].includes(selectedQ.status) ? (
                  <button
                    type="button"
                    disabled={busy}
                    className="rounded-md border px-3 py-1.5 text-xs disabled:opacity-50"
                    onClick={() =>
                      setConfirm({
                        title: "Cancel quote",
                        body: "Cancel this quote and release any inventory holds?",
                        action: async () => {
                          const key = newIdempotencyKey("quote-cancel");
                          await run(async () => {
                            const r = await opsCancelQuote(selectedQ.id, {
                              idempotency_key: key,
                            });
                            setSelectedQ(r);
                            return r;
                          }, "Quote cancelled");
                        },
                      })
                    }
                  >
                    Cancel quote
                  </button>
                ) : null}
              </div>
            </div>
          ) : tab === "orders" && selectedO ? (
            <div className="space-y-3 text-sm">
              <div className="font-mono text-lg font-semibold">
                {selectedO.order_number || `Order #${selectedO.id}`}
              </div>
              <div>{selectedO.customer_label || selectedO.customer_name}</div>
              <div className="text-xs text-slate-500">{statusLabel(selectedO.status)}</div>
              {selectedO.quote_id ? (
                <div className="text-xs text-slate-600">Linked quote id {selectedO.quote_id}</div>
              ) : null}
              <ul className="space-y-2 border-t pt-2">
                {(selectedO.lines || []).map((ln: any) => (
                  <li key={ln.id} className="flex justify-between text-xs">
                    <div>
                      <div className="font-mono font-medium">{ln.sku}</div>
                      <div className="text-slate-500">
                        qty {ln.qty} · {ln.location_code} · {money(ln.unit_price)}
                      </div>
                    </div>
                    <div className="tabular-nums font-medium">{money(ln.line_total)}</div>
                  </li>
                ))}
              </ul>
              <div className="border-t pt-2 font-semibold">Total {money(selectedO.total)}</div>
              <div className="flex flex-wrap gap-2">
                {selectedO.status === "open" ? (
                  <>
                    <button
                      type="button"
                      disabled={busy}
                      className="rounded-md bg-emerald-700 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
                      onClick={() =>
                        setConfirm({
                          title: "Complete sale",
                          body: "Finalize this sale and reduce on-hand inventory?",
                          action: async () => {
                            const key = newIdempotencyKey("order-complete");
                            await run(async () => {
                              const r = await opsCompleteOrder(selectedO.id, {
                                idempotency_key: key,
                              });
                              setSelectedO(r);
                              return r;
                            }, "Sale completed — inventory updated");
                          },
                        })
                      }
                    >
                      Complete sale
                    </button>
                    <button
                      type="button"
                      disabled={busy}
                      className="rounded-md border px-3 py-1.5 text-xs disabled:opacity-50"
                      onClick={() =>
                        setConfirm({
                          title: "Cancel order",
                          body: "Cancel this open order and release reservations?",
                          action: async () => {
                            const key = newIdempotencyKey("order-cancel");
                            await run(async () => {
                              const r = await opsCancelOrder(selectedO.id, {
                                idempotency_key: key,
                              });
                              setSelectedO(r);
                              return r;
                            }, "Order cancelled");
                          },
                        })
                      }
                    >
                      Cancel order
                    </button>
                  </>
                ) : (
                  <div className="text-xs text-slate-500">
                    {selectedO.status === "completed"
                      ? "Sale complete — inventory already updated. No reverse from this screen."
                      : "This order is closed."}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <EmptyState title="Select a row" body="Choose a quote or order to manage it." />
          )}
        </Panel>
      </div>
    </JpPage>
  );
}
