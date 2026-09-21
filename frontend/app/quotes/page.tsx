"use client";

import { useCallback, useEffect, useState } from "react";
import { EmptyState, JpPage, Panel, StockBadge } from "@/components/jp/ui";
import {
  isApiUnreachable,
  opsAddQuoteLine,
  opsCancelOrder,
  opsCancelQuote,
  opsCompleteOrder,
  opsConvertQuote,
  opsCreateQuote,
  opsListOrders,
  opsListQuotes,
  opsReserveQuote,
  opsUpdateQuoteLine,
} from "@/lib/dms-api";

type Tab = "quotes" | "orders";

function money(n?: number) {
  if (n == null || !Number.isFinite(n)) return "—";
  return `$${n.toFixed(2)}`;
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

  const load = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      const [q, o] = await Promise.all([opsListQuotes(), opsListOrders()]);
      setQuotes(q.quotes || []);
      setOrders(o.orders || []);
      if (selectedQ?.id) {
        const match = (q.quotes || []).find((x: any) => x.id === selectedQ.id);
        if (match) setSelectedQ(match);
      }
      if (selectedO?.id) {
        const match = (o.orders || []).find((x: any) => x.id === selectedO.id);
        if (match) setSelectedO(match);
      }
    } catch (e) {
      setErr(
        isApiUnreachable(e)
          ? "API unreachable — start the demo stack."
          : e instanceof Error
            ? e.message
            : "Failed to load"
      );
    } finally {
      setLoading(false);
    }
  }, [selectedQ?.id, selectedO?.id]);

  useEffect(() => {
    void load();
  }, [load]);

  // Deep-link: ?add_sku=&location=
  useEffect(() => {
    if (typeof window === "undefined") return;
    const sp = new URLSearchParams(window.location.search);
    const sku = sp.get("add_sku");
    const location = sp.get("location") || "CHI-N";
    const price = sp.get("price_cents");
    if (!sku) return;
    void (async () => {
      setBusy(true);
      setErr(null);
      try {
        const q = (await opsCreateQuote({ customer_label: customer || "Walk-in" })) as any;
        const updated = (await opsAddQuoteLine(q.id, {
          sku,
          location,
          qty: 1,
          unit_price_cents: price ? Number(price) : undefined,
        })) as any;
        setSelectedQ(updated);
        setTab("quotes");
        setMsg(`Added ${sku} to ${updated.quote_number}`);
        await load();
        window.history.replaceState({}, "", "/quotes");
      } catch (e) {
        setErr(e instanceof Error ? e.message : "Could not add to quote");
      } finally {
        setBusy(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
      setErr(e instanceof Error ? e.message : "Action failed");
      return null;
    } finally {
      setBusy(false);
    }
  };

  return (
    <JpPage
      title="Quotes & Orders"
      description="Create quotes, reserve inventory, convert to orders, and complete sales."
      dense
      actions={
        <button
          type="button"
          disabled={busy}
          className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-50"
          onClick={() =>
            void run(async () => {
              const q = await opsCreateQuote({ customer_label: customer || "Walk-in" });
              setSelectedQ(q);
              setTab("quotes");
              return q;
            }, "Quote created")
          }
        >
          New quote
        </button>
      }
    >
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <input
          value={customer}
          onChange={(e) => setCustomer(e.target.value)}
          placeholder="Customer / reference"
          className="h-9 rounded-md border border-slate-300 bg-white px-3 text-sm"
        />
        <div className="flex rounded-md border border-slate-300 bg-white text-sm">
          {(["quotes", "orders"] as Tab[]).map((t) => (
            <button
              key={t}
              type="button"
              className={`px-3 py-1.5 capitalize ${
                tab === t ? "bg-slate-900 text-white" : "text-slate-700"
              }`}
              onClick={() => setTab(t)}
            >
              {t}
            </button>
          ))}
        </div>
        <button
          type="button"
          className="rounded-md border px-3 py-1.5 text-sm"
          onClick={() => void load()}
        >
          Refresh
        </button>
      </div>

      {err ? (
        <div className="mb-3 rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
          {err}
        </div>
      ) : null}
      {msg ? (
        <div className="mb-3 rounded border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900">
          {msg}
        </div>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
        <Panel>
          {loading ? (
            <EmptyState title="Loading…" />
          ) : tab === "quotes" ? (
            quotes.length === 0 ? (
              <EmptyState title="No quotes yet" body="Create a quote or add a part from Parts Search." />
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
                  {quotes.map((q) => (
                    <tr
                      key={q.id}
                      className="cursor-pointer border-b border-slate-50 hover:bg-slate-50"
                      onClick={() => setSelectedQ(q)}
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
                    className="cursor-pointer border-b border-slate-50 hover:bg-slate-50"
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
              <div className="font-mono text-lg font-semibold">{selectedQ.quote_number}</div>
              <div>{selectedQ.customer_label}</div>
              <div className="text-xs text-slate-500">{statusLabel(selectedQ.status)}</div>
              <ul className="space-y-2 border-t pt-2">
                {(selectedQ.lines || []).map((ln: any) => (
                  <li key={ln.id} className="flex justify-between gap-2 text-xs">
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
              <div className="border-t pt-2 font-semibold">
                Total {money(selectedQ.total)}
              </div>
              <div className="flex flex-wrap gap-2">
                {["draft", "open"].includes(selectedQ.status) ? (
                  <button
                    type="button"
                    disabled={busy}
                    className="rounded-md bg-amber-500 px-3 py-1.5 text-xs font-semibold text-amber-950"
                    onClick={() => {
                      if (!confirm("Reserve inventory for this quote?")) return;
                      void run(
                        () => opsReserveQuote(selectedQ.id),
                        "Inventory reserved for quote"
                      ).then((r) => r && setSelectedQ(r));
                    }}
                  >
                    Reserve inventory
                  </button>
                ) : null}
                {selectedQ.status === "reserved" ? (
                  <button
                    type="button"
                    disabled={busy}
                    className="rounded-md bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white"
                    onClick={() => {
                      if (!confirm("Convert this quote to an order?")) return;
                      void run(
                        () => opsConvertQuote(selectedQ.id),
                        "Order created from quote"
                      ).then((r) => {
                        if (r) {
                          setSelectedO(r);
                          setTab("orders");
                        }
                      });
                    }}
                  >
                    Convert to order
                  </button>
                ) : null}
                {!["converted", "cancelled"].includes(selectedQ.status) ? (
                  <button
                    type="button"
                    disabled={busy}
                    className="rounded-md border px-3 py-1.5 text-xs"
                    onClick={() => {
                      if (!confirm("Cancel this quote and release any holds?")) return;
                      void run(
                        () => opsCancelQuote(selectedQ.id),
                        "Quote cancelled"
                      ).then((r) => r && setSelectedQ(r));
                    }}
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
              <ul className="space-y-2 border-t pt-2">
                {(selectedO.lines || []).map((ln: any) => (
                  <li key={ln.id} className="flex justify-between text-xs">
                    <div>
                      <div className="font-mono font-medium">{ln.sku}</div>
                      <div className="text-slate-500">
                        qty {ln.qty} · {ln.location_code}
                      </div>
                    </div>
                    <div className="tabular-nums">{money(ln.line_total)}</div>
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
                      className="rounded-md bg-emerald-700 px-3 py-1.5 text-xs font-semibold text-white"
                      onClick={() => {
                        if (!confirm("Complete this sale and update inventory?")) return;
                        void run(
                          () => opsCompleteOrder(selectedO.id),
                          "Sale completed — inventory updated"
                        ).then((r) => r && setSelectedO(r));
                      }}
                    >
                      Complete sale
                    </button>
                    <button
                      type="button"
                      disabled={busy}
                      className="rounded-md border px-3 py-1.5 text-xs"
                      onClick={() => {
                        if (!confirm("Cancel order and release reservations?")) return;
                        void run(
                          () => opsCancelOrder(selectedO.id),
                          "Order cancelled"
                        ).then((r) => r && setSelectedO(r));
                      }}
                    >
                      Cancel order
                    </button>
                  </>
                ) : null}
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
