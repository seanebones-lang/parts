"use client";

import { useCallback, useEffect, useState } from "react";
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
  ClipboardList,
  Loader2,
  Plus,
  RefreshCw,
} from "lucide-react";
import {
  type DmsCustomer,
  type DmsOrder,
  ApiError,
  createDmsInvoice,
  dmsInvoicePdfUrl,
  isApiUnreachable,
  listDmsCustomers,
  listDmsOrders,
  createDmsOrder,
  setDmsOrderStatus,
} from "@/lib/dms-api";

function formatMoney(n?: number): string {
  if (n === undefined || n === null || !Number.isFinite(n)) return "—";
  return `$${n.toFixed(2)}`;
}

function orderTotal(o: DmsOrder): number | undefined {
  if (o.total !== undefined && o.total !== null && Number.isFinite(Number(o.total))) {
    return Number(o.total);
  }
  const lines = o.lines?.length ? o.lines : o.items ?? [];
  if (!lines.length) return undefined;
  let sum = 0;
  let any = false;
  for (const l of lines) {
    const price = Number((l as { unit_price?: number }).unit_price ?? 0);
    const q = Number(l.qty ?? l.quantity ?? 0);
    if (Number.isFinite(price) && Number.isFinite(q)) {
      sum += price * q;
      any = true;
    }
  }
  return any ? sum : undefined;
}

function formatWhen(s?: string): string {
  if (!s) return "—";
  try {
    const d = new Date(s);
    if (Number.isNaN(d.getTime())) return s;
    return d.toLocaleString();
  } catch {
    return s;
  }
}

export default function OrdersPage() {
  const [orders, setOrders] = useState<DmsOrder[]>([]);
  const [customers, setCustomers] = useState<DmsCustomer[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [unreachable, setUnreachable] = useState(false);
  const [flash, setFlash] = useState<string | null>(null);

  const [customerId, setCustomerId] = useState("");
  const [locationCode, setLocationCode] = useState("L1");
  const [sku, setSku] = useState("");
  const [qty, setQty] = useState("1");
  const [notes, setNotes] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setUnreachable(false);
    try {
      const [ord, cust] = await Promise.all([
        listDmsOrders(),
        listDmsCustomers().catch(() => ({ customers: [] as DmsCustomer[] })),
      ]);
      setOrders(ord.orders);
      setCustomers(cust.customers);
      if (cust.customers.length && !customerId) {
        const id = cust.customers[0].id;
        if (id != null) setCustomerId(String(id));
      }
    } catch (e) {
      setOrders([]);
      if (isApiUnreachable(e) || (e instanceof ApiError && e.status === 404)) {
        setUnreachable(true);
        setError(
          e instanceof ApiError && e.status === 404
            ? "DMS API not loaded yet (404). Run ./scripts/demo_up.sh after DMS backend is enabled."
            : "API unreachable. Run ./scripts/demo_up.sh"
        );
      } else {
        setError(e instanceof Error ? e.message : "Failed to load orders");
      }
    } finally {
      setLoading(false);
    }
  }, [customerId]);

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setFlash(null);
    setError(null);
    try {
      const q = Number(qty);
      if (!customerId.trim()) throw new Error("Customer is required");
      if (!sku.trim()) throw new Error("SKU is required");
      if (!Number.isFinite(q) || q <= 0) throw new Error("Qty must be a positive number");

      const cid: string | number = /^\d+$/.test(customerId.trim())
        ? Number(customerId.trim())
        : customerId.trim();

      await createDmsOrder({
        customer_id: cid,
        location_code: locationCode.trim() || undefined,
        notes: notes.trim() || undefined,
        lines: [{ sku: sku.trim(), qty: q }],
      });
      setFlash("Order created");
      setSku("");
      setQty("1");
      setNotes("");
      await load();
    } catch (err) {
      if (isApiUnreachable(err)) {
        setUnreachable(true);
        setError("API unreachable. Run ./scripts/demo_up.sh");
      } else {
        setError(err instanceof Error ? err.message : "Create order failed");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-950">
        <strong>DMS Core (local SQLite)</strong> — OEM live feed when configured.
        Orders are stored in the DMS order book (reserve stock on create).
      </div>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <ClipboardList className="h-6 w-6" />
            Orders
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            List and create counter orders via{" "}
            <code className="text-xs">/api/v1/dms/orders</code>
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          disabled={loading || submitting}
          onClick={() => void load()}
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin mr-1" />
          ) : (
            <RefreshCw className="h-4 w-4 mr-1" />
          )}
          Refresh
        </Button>
      </div>

      {flash ? (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900">
          {flash}
        </div>
      ) : null}

      {error ? (
        <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-3 text-sm text-amber-950 flex gap-2">
          <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
          <div className="space-y-1">
            <p>{error}</p>
            {unreachable ? (
              <p className="font-mono text-xs">./scripts/demo_up.sh</p>
            ) : null}
          </div>
        </div>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-5">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Plus className="h-4 w-4" />
              Create order
            </CardTitle>
            <CardDescription>Create order and reserve stock</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={onCreate} className="space-y-3">
              <label className="block space-y-1">
                <span className="text-xs font-medium text-muted-foreground">
                  Customer
                </span>
                {customers.length > 0 ? (
                  <select
                    className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                    value={customerId}
                    onChange={(e) => setCustomerId(e.target.value)}
                    required
                  >
                    {customers.map((c) => (
                      <option key={String(c.id)} value={String(c.id ?? "")}>
                        {c.name}
                        {c.id != null ? ` (#${c.id})` : ""}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                    placeholder="Customer id"
                    value={customerId}
                    onChange={(e) => setCustomerId(e.target.value)}
                    required
                  />
                )}
              </label>
              <label className="block space-y-1">
                <span className="text-xs font-medium text-muted-foreground">
                  Location code
                </span>
                <input
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                  value={locationCode}
                  onChange={(e) => setLocationCode(e.target.value)}
                  placeholder="L1"
                />
              </label>
              <div className="grid grid-cols-3 gap-2">
                <label className="block space-y-1 col-span-2">
                  <span className="text-xs font-medium text-muted-foreground">
                    SKU
                  </span>
                  <input
                    className="w-full rounded-md border bg-background px-3 py-2 text-sm font-mono"
                    value={sku}
                    onChange={(e) => setSku(e.target.value)}
                    placeholder="OEM-BP-HC19"
                    required
                  />
                </label>
                <label className="block space-y-1">
                  <span className="text-xs font-medium text-muted-foreground">
                    Qty
                  </span>
                  <input
                    type="number"
                    min={1}
                    className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                    value={qty}
                    onChange={(e) => setQty(e.target.value)}
                    required
                  />
                </label>
              </div>
              <label className="block space-y-1">
                <span className="text-xs font-medium text-muted-foreground">
                  Notes
                </span>
                <input
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Optional"
                />
              </label>
              <Button type="submit" className="w-full" disabled={submitting || unreachable}>
                {submitting ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-1" />
                ) : (
                  <Plus className="h-4 w-4 mr-1" />
                )}
                Create order
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle className="text-lg">Orders</CardTitle>
            <CardDescription>
              {loading
                ? "Loading…"
                : `${orders.length} order${orders.length === 1 ? "" : "s"}`}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground py-8 justify-center">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading orders…
              </div>
            ) : orders.length === 0 ? (
              <div className="rounded-md border border-dashed p-8 text-center space-y-2">
                <p className="text-sm text-muted-foreground">
                  {unreachable
                    ? "No connection to DMS API."
                    : "No orders yet. Create one or seed DMS first."}
                </p>
                <p className="text-xs text-muted-foreground font-mono">
                  ./scripts/demo_up.sh
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left text-muted-foreground">
                      <th className="py-2 pr-3 font-medium">Order</th>
                      <th className="py-2 pr-3 font-medium">Customer</th>
                      <th className="py-2 pr-3 font-medium">Status</th>
                      <th className="py-2 pr-3 font-medium text-right">Total</th>
                      <th className="py-2 pr-3 font-medium">Created</th>
                      <th className="py-2 font-medium">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {orders.map((o, i) => {
                      const lines = o.lines?.length ? o.lines : o.items ?? [];
                      const total = orderTotal(o);
                      const oid = o.id ?? o.order_number;
                      const payHref =
                        oid != null
                          ? `/payments?order_id=${encodeURIComponent(String(oid))}${
                              total != null ? `&amount=${encodeURIComponent(String(total))}` : ""
                            }`
                          : "/payments";
                      const shipHref =
                        oid != null
                          ? `/shipping?order_id=${encodeURIComponent(String(oid))}`
                          : "/shipping";
                      return (
                        <tr
                          key={`${o.id ?? o.order_number ?? i}`}
                          className="border-b last:border-0 align-top"
                        >
                          <td className="py-2 pr-3">
                            <div className="font-mono text-xs">
                              {o.order_number || o.id || "—"}
                            </div>
                            {lines.length > 0 ? (
                              <div className="text-xs text-muted-foreground mt-0.5">
                                {lines
                                  .map(
                                    (l) =>
                                      `${l.sku || "?"}×${l.qty ?? l.quantity ?? "?"}`
                                  )
                                  .join(", ")}
                              </div>
                            ) : null}
                          </td>
                          <td className="py-2 pr-3">
                            {o.customer_name ||
                              (o.customer_id != null
                                ? `#${o.customer_id}`
                                : "—")}
                          </td>
                          <td className="py-2 pr-3">
                            <Badge variant="secondary">{o.status || "open"}</Badge>
                          </td>
                          <td className="py-2 pr-3 text-right tabular-nums">
                            {formatMoney(total)}
                          </td>
                          <td className="py-2 pr-3 text-muted-foreground text-xs">
                            {formatWhen(o.created_at)}
                          </td>
                          <td className="py-2">
                            <div className="flex flex-wrap gap-1">
                              <Button asChild size="sm" variant="outline">
                                <a href={payHref}>Pay</a>
                              </Button>
                              <Button asChild size="sm" variant="outline">
                                <a href={shipHref}>Ship</a>
                              </Button>
                              {o.status === "open" && (
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() =>
                                    void setDmsOrderStatus(String(oid), "picking").then(() => load())
                                  }
                                >
                                  Pick
                                </Button>
                              )}
                              {(o.status === "open" || o.status === "picking") && (
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() =>
                                    void createDmsInvoice(String(oid)).then(() => load())
                                  }
                                >
                                  Invoice
                                </Button>
                              )}
                              {o.status === "invoiced" && (
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() =>
                                    void setDmsOrderStatus(String(oid), "completed").then(() =>
                                      load()
                                    )
                                  }
                                >
                                  Complete
                                </Button>
                              )}
                              {o.status !== "cancelled" && o.status !== "completed" && (
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() =>
                                    void setDmsOrderStatus(String(oid), "cancelled").then(() =>
                                      load()
                                    )
                                  }
                                >
                                  Cancel
                                </Button>
                              )}
                              {oid != null && (
                                <Button asChild size="sm" variant="ghost">
                                  <a
                                    href={dmsInvoicePdfUrl(oid)}
                                    target="_blank"
                                    rel="noreferrer"
                                  >
                                    PDF
                                  </a>
                                </Button>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
