"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
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
  Loader2,
  Package,
  RefreshCw,
  Database,
  Download,
} from "lucide-react";
import {
  type DmsInventoryRow,
  type DmsStatus,
  ApiError,
  isApiUnreachable,
  getDmsStatus,
  listDmsInventory,
  seedDms,
  syncOem,
} from "@/lib/dms-api";

function qtyOf(row: DmsInventoryRow): number {
  const q = row.qty ?? row.quantity ?? row.on_hand;
  return typeof q === "number" && Number.isFinite(q) ? q : 0;
}

function formatMoney(n?: number): string {
  if (n === undefined || n === null || !Number.isFinite(n)) return "—";
  return `$${n.toFixed(2)}`;
}

export default function InventoryPage() {
  const [rows, setRows] = useState<DmsInventoryRow[]>([]);
  const [status, setStatus] = useState<DmsStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionBusy, setActionBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [unreachable, setUnreachable] = useState(false);
  const [flash, setFlash] = useState<string | null>(null);
  const [userKeyInput, setUserKeyInput] = useState("");
  const [activeUserKey, setActiveUserKey] = useState("");
  const [aclUser, setAclUser] = useState<string | null>(null);

  const load = useCallback(async (filterKey?: string) => {
    setLoading(true);
    setError(null);
    setUnreachable(false);
    const key = (filterKey ?? activeUserKey).trim();
    try {
      const [inv, st] = await Promise.all([
        listDmsInventory(key ? { user_key: key } : undefined),
        getDmsStatus().catch(() => null),
      ]);
      setRows(inv.rows);
      setAclUser(inv.acl_user ?? (key || null));
      setStatus(st);
    } catch (e) {
      setRows([]);
      setStatus(null);
      setAclUser(null);
      if (isApiUnreachable(e) || (e instanceof ApiError && e.status === 404)) {
        setUnreachable(true);
        setError(
          e instanceof ApiError && e.status === 404
            ? "DMS API not loaded yet (404). Start stack with ./scripts/demo_up.sh after DMS backend is enabled."
            : "API unreachable. Start the demo stack with ./scripts/demo_up.sh"
        );
      } else {
        setError(e instanceof Error ? e.message : "Failed to load inventory");
      }
    } finally {
      setLoading(false);
    }
  }, [activeUserKey]);

  useEffect(() => {
    void load();
  }, [load]);

  const totalQty = useMemo(
    () => rows.reduce((acc, r) => acc + qtyOf(r), 0),
    [rows]
  );

  const runAction = async (key: string, fn: () => Promise<unknown>, okMsg: string) => {
    setActionBusy(key);
    setFlash(null);
    setError(null);
    try {
      const res = await fn();
      const msg =
        res && typeof res === "object" && "message" in res
          ? String((res as { message?: unknown }).message ?? okMsg)
          : okMsg;
      setFlash(msg);
      await load();
    } catch (e) {
      if (isApiUnreachable(e)) {
        setUnreachable(true);
        setError("API unreachable. Run ./scripts/demo_up.sh");
      } else {
        setError(e instanceof Error ? e.message : "Action failed");
      }
    } finally {
      setActionBusy(null);
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-950">
        <strong>DMS Core (local SQLite)</strong> — OEM live feed when configured.
        Stock levels come from <code className="text-xs">/api/v1/dms/inventory</code>.
        Optional ACL filter: <code className="text-xs">user_key</code> /{" "}
        <code className="text-xs">X-Parts-User</code> (
        <Link href="/orgs" className="underline font-semibold">
          Orgs / ACL
        </Link>
        ).
      </div>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Package className="h-6 w-6" />
            Inventory
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Multi-location on-hand from DMS Core
            {status?.db_path ? (
              <>
                {" "}
                · <span className="font-mono text-xs">{status.db_path}</span>
              </>
            ) : null}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={loading || !!actionBusy}
            onClick={() => void load()}
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin mr-1" />
            ) : (
              <RefreshCw className="h-4 w-4 mr-1" />
            )}
            Refresh
          </Button>
          <Button
            variant="secondary"
            size="sm"
            disabled={!!actionBusy}
            onClick={() =>
              void runAction("seed", () => seedDms(), "Seed complete (synthetic OEM + locations)")
            }
          >
            {actionBusy === "seed" ? (
              <Loader2 className="h-4 w-4 animate-spin mr-1" />
            ) : (
              <Database className="h-4 w-4 mr-1" />
            )}
            Seed DMS
          </Button>
          <Button
            size="sm"
            disabled={!!actionBusy}
            onClick={() =>
              void runAction(
                "oem",
                () => syncOem({ source: "synthetic" }),
                "OEM synthetic sync complete"
              )
            }
          >
            {actionBusy === "oem" ? (
              <Loader2 className="h-4 w-4 animate-spin mr-1" />
            ) : (
              <Download className="h-4 w-4 mr-1" />
            )}
            OEM sync (synthetic)
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap items-end gap-2 rounded-md border px-3 py-3">
        <label className="text-sm space-y-1 min-w-[12rem] flex-1">
          <span className="text-muted-foreground">ACL user_key filter</span>
          <input
            className="w-full rounded-md border px-3 py-2 text-sm"
            value={userKeyInput}
            onChange={(e) => setUserKeyInput(e.target.value)}
            placeholder="counter1 (empty = all)"
            disabled={loading || !!actionBusy || unreachable}
          />
        </label>
        <Button
          size="sm"
          variant="secondary"
          disabled={loading || !!actionBusy || unreachable}
          onClick={() => {
            const k = userKeyInput.trim();
            setActiveUserKey(k);
            void load(k);
          }}
        >
          Apply filter
        </Button>
        <Button
          size="sm"
          variant="outline"
          disabled={loading || !!actionBusy || unreachable || (!activeUserKey && !userKeyInput)}
          onClick={() => {
            setUserKeyInput("");
            setActiveUserKey("");
            void load("");
          }}
        >
          Clear
        </Button>
        {aclUser ? (
          <Badge variant="default">filtered: {aclUser}</Badge>
        ) : (
          <Badge variant="outline">unfiltered</Badge>
        )}
      </div>

      {status ? (
        <div className="flex flex-wrap gap-2 text-xs">
          {status.catalog_count != null && (
            <Badge variant="secondary">Catalog {status.catalog_count}</Badge>
          )}
          {status.inventory_rows != null && (
            <Badge variant="secondary">Inventory rows {status.inventory_rows}</Badge>
          )}
          {status.customer_count != null && (
            <Badge variant="secondary">Customers {status.customer_count}</Badge>
          )}
          {status.order_count != null && (
            <Badge variant="secondary">Orders {status.order_count}</Badge>
          )}
          <Badge variant={status.oem_configured ? "default" : "outline"}>
            OEM feed {status.oem_configured ? "configured" : "not configured"}
          </Badge>
        </div>
      ) : null}

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
              <p>
                <Link
                  href="#"
                  className="font-semibold underline"
                  onClick={(e) => {
                    e.preventDefault();
                  }}
                >
                  ./scripts/demo_up.sh
                </Link>{" "}
                — free ports, start API :8000 + FE :3000, then refresh this page.
              </p>
            ) : null}
          </div>
        </div>
      ) : null}

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">Stock by location</CardTitle>
          <CardDescription>
            {loading
              ? "Loading…"
              : `${rows.length} row${rows.length === 1 ? "" : "s"} · ${totalQty} units on hand`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground py-8 justify-center">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading inventory…
            </div>
          ) : rows.length === 0 ? (
            <div className="rounded-md border border-dashed p-8 text-center space-y-3">
              <p className="text-sm text-muted-foreground">
                {unreachable
                  ? "No connection to DMS API."
                  : "No inventory rows yet. Seed DMS or run OEM synthetic sync."}
              </p>
              <div className="flex flex-wrap justify-center gap-2">
                {!unreachable && (
                  <>
                    <Button
                      size="sm"
                      variant="secondary"
                      disabled={!!actionBusy}
                      onClick={() =>
                        void runAction("seed", () => seedDms(), "Seed complete")
                      }
                    >
                      Seed DMS
                    </Button>
                    <Button
                      size="sm"
                      disabled={!!actionBusy}
                      onClick={() =>
                        void runAction(
                          "oem",
                          () => syncOem({ source: "synthetic" }),
                          "OEM synthetic sync complete"
                        )
                      }
                    >
                      OEM sync (synthetic)
                    </Button>
                  </>
                )}
                <Button size="sm" variant="outline" asChild>
                  <a
                    href="https://github.com/seanebones-lang/parts/blob/main/scripts/demo_up.sh"
                    target="_blank"
                    rel="noreferrer"
                  >
                    demo_up.sh
                  </a>
                </Button>
              </div>
              <p className="text-xs text-muted-foreground font-mono">
                ./scripts/demo_up.sh
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="py-2 pr-3 font-medium">SKU</th>
                    <th className="py-2 pr-3 font-medium">Name</th>
                    <th className="py-2 pr-3 font-medium">Location</th>
                    <th className="py-2 pr-3 font-medium text-right">Qty</th>
                    <th className="py-2 pr-3 font-medium text-right">List</th>
                    <th className="py-2 font-medium">Make / Model</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r, i) => {
                    const q = qtyOf(r);
                    const key = `${r.sku ?? ""}-${r.location_id ?? r.location ?? ""}-${i}`;
                    return (
                      <tr key={key} className="border-b last:border-0">
                        <td className="py-2 pr-3 font-mono text-xs">
                          {r.sku || r.part_number || "—"}
                        </td>
                        <td className="py-2 pr-3">{r.name || "—"}</td>
                        <td className="py-2 pr-3">
                          {r.location_name ||
                            r.location ||
                            r.location_code ||
                            (r.location_id != null ? String(r.location_id) : "—")}
                        </td>
                        <td className="py-2 pr-3 text-right">
                          <Badge
                            variant={
                              q === 0
                                ? "destructive"
                                : q < 5
                                  ? "secondary"
                                  : "default"
                            }
                          >
                            {q}
                          </Badge>
                        </td>
                        <td className="py-2 pr-3 text-right tabular-nums">
                          {formatMoney(r.list_price)}
                        </td>
                        <td className="py-2 text-muted-foreground">
                          {[r.make, r.model].filter(Boolean).join(" ") || "—"}
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
  );
}
