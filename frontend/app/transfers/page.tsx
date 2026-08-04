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
import { AlertCircle, ArrowRightLeft, Loader2, RefreshCw } from "lucide-react";
import {
  type DmsLocation,
  type DmsTransfer,
  ApiError,
  isApiUnreachable,
  listDmsLocations,
  listDmsTransfers,
  createDmsTransfer,
  approveDmsTransfer,
  cancelDmsTransfer,
  listDmsInventory,
} from "@/lib/dms-api";

export default function TransfersPage() {
  const [transfers, setTransfers] = useState<DmsTransfer[]>([]);
  const [locations, setLocations] = useState<DmsLocation[]>([]);
  const [threshold, setThreshold] = useState<number>(10);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [unreachable, setUnreachable] = useState(false);
  const [flash, setFlash] = useState<string | null>(null);

  const [sku, setSku] = useState("");
  const [fromLoc, setFromLoc] = useState("");
  const [toLoc, setToLoc] = useState("");
  const [qty, setQty] = useState("1");
  const [notes, setNotes] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setUnreachable(false);
    try {
      const [t, locs, inv] = await Promise.all([
        listDmsTransfers({ limit: 50 }),
        listDmsLocations(),
        listDmsInventory().catch(() => ({ rows: [] as { sku?: string }[] })),
      ]);
      setTransfers(t.transfers);
      if (t.approval_threshold) setThreshold(t.approval_threshold);
      setLocations(locs.locations);
      if (!fromLoc && locs.locations[0]?.code) {
        setFromLoc(String(locs.locations[0].code));
      }
      if (!toLoc && locs.locations[1]?.code) {
        setToLoc(String(locs.locations[1].code));
      } else if (!toLoc && locs.locations[0]?.code) {
        setToLoc(String(locs.locations[0].code));
      }
      if (!sku && inv.rows[0]?.sku) setSku(String(inv.rows[0].sku));
    } catch (e) {
      setTransfers([]);
      if (isApiUnreachable(e) || (e instanceof ApiError && e.status === 404)) {
        setUnreachable(true);
        setError("API unreachable or DMS not loaded. Run ./scripts/demo_up.sh");
      } else {
        setError(e instanceof Error ? e.message : "Failed to load transfers");
      }
    } finally {
      setLoading(false);
    }
  }, [fromLoc, toLoc, sku]);

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- initial load only
  }, []);

  const onCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy("create");
    setFlash(null);
    setError(null);
    try {
      const q = Number(qty);
      if (!sku.trim() || !fromLoc || !toLoc) throw new Error("sku, from, to required");
      if (!Number.isFinite(q) || q <= 0) throw new Error("qty must be > 0");
      const res = (await createDmsTransfer({
        sku: sku.trim(),
        from_location: fromLoc,
        to_location: toLoc,
        qty: q,
        notes: notes.trim() || undefined,
        requested_by: "desk",
      })) as { transfer?: { status?: string; id?: number }; conserved?: boolean };
      const st = res.transfer?.status;
      setFlash(
        st === "pending_approval"
          ? `Transfer #${res.transfer?.id} pending manager approval (qty ≥ ${threshold})`
          : `Transfer #${res.transfer?.id} completed (stock conserved=${res.conserved})`
      );
      setNotes("");
      await load();
    } catch (err) {
      if (isApiUnreachable(err)) {
        setUnreachable(true);
        setError("API unreachable");
      } else if (err instanceof ApiError) {
        const d =
          typeof err.body === "object" && err.body && "detail" in (err.body as object)
            ? String((err.body as { detail?: unknown }).detail)
            : err.message;
        setError(d);
      } else {
        setError(err instanceof Error ? err.message : "Create failed");
      }
    } finally {
      setBusy(null);
    }
  };

  const run = async (key: string, fn: () => Promise<unknown>, ok: string) => {
    setBusy(key);
    setError(null);
    setFlash(null);
    try {
      await fn();
      setFlash(ok);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="rounded-lg border border-violet-200 bg-violet-50 px-4 py-3 text-sm text-violet-950">
        <strong>Inter-store transfers</strong> — stock is conserved (total qty for SKU
        unchanged). Qty ≥ <code className="text-xs">{threshold}</code> (
        <code className="text-xs">PARRTS_TRANSFER_APPROVAL_QTY</code>) needs manager
        approval. Demo default role is admin (open desk).
      </div>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <ArrowRightLeft className="h-6 w-6" />
            Transfers
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Move parts between locations ·{" "}
            <Link href="/inventory" className="underline">
              Inventory
            </Link>
          </p>
        </div>
        <Button variant="outline" size="sm" disabled={loading || !!busy} onClick={() => void load()}>
          {loading ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <RefreshCw className="h-4 w-4 mr-1" />}
          Refresh
        </Button>
      </div>

      {flash ? (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900">
          {flash}
        </div>
      ) : null}
      {error ? (
        <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-3 text-sm flex gap-2">
          <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
          <div>
            <p>{error}</p>
            {unreachable ? <p className="font-mono text-xs mt-1">./scripts/demo_up.sh</p> : null}
          </div>
        </div>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Create transfer</CardTitle>
          <CardDescription>POST /api/v1/dms/transfers</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onCreate} className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <label className="text-sm space-y-1">
              <span className="text-muted-foreground">SKU</span>
              <input
                className="w-full rounded-md border px-3 py-2 text-sm"
                value={sku}
                onChange={(e) => setSku(e.target.value)}
                disabled={!!busy || unreachable}
              />
            </label>
            <label className="text-sm space-y-1">
              <span className="text-muted-foreground">From</span>
              <select
                className="w-full rounded-md border px-3 py-2 text-sm bg-background"
                value={fromLoc}
                onChange={(e) => setFromLoc(e.target.value)}
                disabled={!!busy || unreachable}
              >
                {locations.map((l) => (
                  <option key={String(l.code)} value={String(l.code)}>
                    {l.code}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm space-y-1">
              <span className="text-muted-foreground">To</span>
              <select
                className="w-full rounded-md border px-3 py-2 text-sm bg-background"
                value={toLoc}
                onChange={(e) => setToLoc(e.target.value)}
                disabled={!!busy || unreachable}
              >
                {locations.map((l) => (
                  <option key={String(l.code)} value={String(l.code)}>
                    {l.code}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm space-y-1">
              <span className="text-muted-foreground">Qty</span>
              <input
                className="w-full rounded-md border px-3 py-2 text-sm"
                value={qty}
                onChange={(e) => setQty(e.target.value)}
                disabled={!!busy || unreachable}
              />
            </label>
            <div className="flex items-end">
              <Button type="submit" size="sm" disabled={!!busy || unreachable} className="w-full">
                {busy === "create" ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : null}
                Submit
              </Button>
            </div>
            <label className="text-sm space-y-1 sm:col-span-2 lg:col-span-5">
              <span className="text-muted-foreground">Notes</span>
              <input
                className="w-full rounded-md border px-3 py-2 text-sm"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                disabled={!!busy || unreachable}
              />
            </label>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recent transfers ({transfers.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : transfers.length === 0 ? (
            <p className="text-sm text-muted-foreground">No transfers yet. Seed inventory first.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="py-2 pr-2">ID</th>
                    <th className="py-2 pr-2">SKU</th>
                    <th className="py-2 pr-2">From → To</th>
                    <th className="py-2 pr-2">Qty</th>
                    <th className="py-2 pr-2">Status</th>
                    <th className="py-2">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {transfers.map((t) => (
                    <tr key={String(t.id)} className="border-b last:border-0">
                      <td className="py-2 pr-2 font-mono text-xs">{t.id}</td>
                      <td className="py-2 pr-2 font-mono text-xs">{t.sku}</td>
                      <td className="py-2 pr-2">
                        {t.from_code} → {t.to_code}
                      </td>
                      <td className="py-2 pr-2">{t.qty}</td>
                      <td className="py-2 pr-2">
                        <Badge
                          variant={
                            t.status === "completed"
                              ? "default"
                              : t.status === "pending_approval"
                                ? "secondary"
                                : "outline"
                          }
                        >
                          {t.status}
                        </Badge>
                      </td>
                      <td className="py-2">
                        {t.status === "pending_approval" ? (
                          <div className="flex gap-1">
                            <Button
                              size="sm"
                              variant="secondary"
                              disabled={!!busy}
                              onClick={() =>
                                void run(
                                  `a-${t.id}`,
                                  () => approveDmsTransfer(t.id!),
                                  `Approved #${t.id}`
                                )
                              }
                            >
                              Approve
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              disabled={!!busy}
                              onClick={() =>
                                void run(
                                  `c-${t.id}`,
                                  () => cancelDmsTransfer(t.id!),
                                  `Cancelled #${t.id}`
                                )
                              }
                            >
                              Cancel
                            </Button>
                          </div>
                        ) : (
                          "—"
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
