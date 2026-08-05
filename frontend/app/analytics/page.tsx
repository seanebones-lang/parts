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
  BarChart3,
  Loader2,
  RefreshCw,
} from "lucide-react";
import {
  type DmsAnalytics,
  ApiError,
  getDmsAnalytics,
  isApiUnreachable,
} from "@/lib/dms-api";

function money(n?: number): string {
  if (n === undefined || n === null || !Number.isFinite(n)) return "—";
  return `$${n.toFixed(2)}`;
}

function entriesSorted(m?: Record<string, number>): Array<[string, number]> {
  if (!m) return [];
  return Object.entries(m).sort((a, b) => a[0].localeCompare(b[0]));
}

export default function AnalyticsPage() {
  const [data, setData] = useState<DmsAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [unreachable, setUnreachable] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setUnreachable(false);
    try {
      const a = await getDmsAnalytics();
      setData(a);
    } catch (e) {
      setData(null);
      if (isApiUnreachable(e) || (e instanceof ApiError && e.status === 404)) {
        setUnreachable(true);
        setError(
          e instanceof ApiError && e.status === 404
            ? "Analytics API not loaded (404). Run ./scripts/demo_up.sh"
            : "API unreachable. Run ./scripts/demo_up.sh"
        );
      } else {
        setError(e instanceof Error ? e.message : "Failed to load analytics");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const c = data?.counts;
  const rev = data?.revenue;

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-950">
        <strong>Live DMS analytics</strong> — counts and order-book values from
        real SQLite/Postgres DMS tables. Not mock charts. Order $ is line qty ×
        unit_price (not Stripe settlement).
      </div>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <BarChart3 className="h-6 w-6" />
            Analytics
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            <code className="text-xs">GET /api/v1/dms/analytics</code>
            {data?.generated_at ? (
              <>
                {" "}
                · generated {data.generated_at}
                {data.backend ? ` · backend ${data.backend}` : null}
              </>
            ) : null}
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          disabled={loading}
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

      {error ? (
        <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-3 text-sm text-amber-950 flex gap-2">
          <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
          <div className="space-y-1">
            <p>{error}</p>
            {unreachable ? (
              <p className="text-xs">
                Then open Inventory / Orders to seed demo data if empty.
              </p>
            ) : null}
          </div>
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          ["Catalog SKUs", c?.catalog_parts],
          ["Inventory units", c?.inventory_units],
          ["Orders", c?.orders],
          ["Customers", c?.customers],
          ["Locations", c?.locations],
          ["Transfers", c?.transfers],
          ["Adjustments", c?.stock_adjustments],
          ["Low stock rows (≤2)", c?.low_stock_rows],
        ].map(([label, val]) => (
          <Card key={String(label)}>
            <CardHeader className="pb-2">
              <CardDescription>{label}</CardDescription>
              <CardTitle className="text-2xl tabular-nums">
                {loading && !data ? "…" : val ?? "—"}
              </CardTitle>
            </CardHeader>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Order book $</CardTitle>
            <CardDescription>{rev?.note || "From order lines"}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span>Book total</span>
              <span className="font-medium tabular-nums">
                {money(rev?.order_book_value)}
              </span>
            </div>
            <div className="flex justify-between">
              <span>Open / picking</span>
              <span className="font-medium tabular-nums">
                {money(rev?.open_pipeline_value)}
              </span>
            </div>
            <div className="flex justify-between">
              <span>Invoiced / completed</span>
              <span className="font-medium tabular-nums">
                {money(rev?.realized_value)}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Orders by status</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {entriesSorted(data?.orders_by_status).length === 0 ? (
              <p className="text-sm text-muted-foreground">No orders yet.</p>
            ) : (
              entriesSorted(data?.orders_by_status).map(([st, n]) => (
                <div key={st} className="flex items-center justify-between text-sm">
                  <Badge variant="outline">{st}</Badge>
                  <span className="tabular-nums font-medium">{n}</span>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Transfers by status</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {entriesSorted(data?.transfers_by_status).length === 0 ? (
              <p className="text-sm text-muted-foreground">No transfers yet.</p>
            ) : (
              entriesSorted(data?.transfers_by_status).map(([st, n]) => (
                <div key={st} className="flex items-center justify-between text-sm">
                  <Badge variant="outline">{st}</Badge>
                  <span className="tabular-nums font-medium">{n}</span>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Adjustments by reason</CardTitle>
          </CardHeader>
          <CardContent>
            {!data?.adjustments_by_reason?.length ? (
              <p className="text-sm text-muted-foreground">No adjustments yet.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-muted-foreground border-b">
                      <th className="py-2 pr-2">Reason</th>
                      <th className="py-2 pr-2">Count</th>
                      <th className="py-2">Δ sum</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.adjustments_by_reason.map((r) => (
                      <tr key={r.reason ?? "?"} className="border-b last:border-0">
                        <td className="py-2 pr-2">{r.reason ?? "—"}</td>
                        <td className="py-2 pr-2 tabular-nums">{r.count ?? "—"}</td>
                        <td className="py-2 tabular-nums">{r.delta_sum ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Top inventory SKUs</CardTitle>
            <CardDescription>By on-hand units</CardDescription>
          </CardHeader>
          <CardContent>
            {!data?.top_inventory_skus?.length ? (
              <p className="text-sm text-muted-foreground">No inventory rows.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-muted-foreground border-b">
                      <th className="py-2 pr-2">SKU</th>
                      <th className="py-2">Units</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.top_inventory_skus.map((r) => (
                      <tr key={r.sku ?? "?"} className="border-b last:border-0">
                        <td className="py-2 pr-2 font-mono text-xs">{r.sku ?? "—"}</td>
                        <td className="py-2 tabular-nums">{r.units ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">OEM feed</CardTitle>
        </CardHeader>
        <CardContent className="text-sm space-y-2">
          <div className="flex flex-wrap gap-2 items-center">
            <span>Configured:</span>
            <Badge variant={data?.oem?.feed_configured ? "default" : "outline"}>
              {data?.oem?.feed_configured ? "yes" : "no"}
            </Badge>
          </div>
          <p className="text-muted-foreground text-xs">
            Live OEM requires OEM_FEED_URL (+ token). Synthetic/file adapters work
            offline. See{" "}
            <Link href="/inventory" className="underline">
              Inventory
            </Link>
            .
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
