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
import { AlertCircle, GitBranch, Loader2, RefreshCw } from "lucide-react";
import {
  type DmsSupersession,
  ApiError,
  createDmsSupersession,
  isApiUnreachable,
  listDmsSupersessions,
  resolveDmsSupersession,
} from "@/lib/dms-api";

export default function SupersessionsPage() {
  const [rows, setRows] = useState<DmsSupersession[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [flash, setFlash] = useState<string | null>(null);
  const [oldSku, setOldSku] = useState("");
  const [newSku, setNewSku] = useState("");
  const [notes, setNotes] = useState("");
  const [resolveSku, setResolveSku] = useState("");
  const [resolveOut, setResolveOut] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listDmsSupersessions(200);
      setRows(data.supersessions);
    } catch (e) {
      setRows([]);
      if (isApiUnreachable(e) || (e instanceof ApiError && e.status === 404)) {
        setError("API unreachable or supersessions not loaded. Run ./scripts/demo_up.sh");
      } else {
        setError(e instanceof Error ? e.message : "Failed to load supersessions");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const onCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setFlash(null);
    setError(null);
    try {
      await createDmsSupersession({
        old_sku: oldSku.trim(),
        new_sku: newSku.trim(),
        notes: notes.trim() || undefined,
      });
      setFlash(`Mapped ${oldSku.trim()} → ${newSku.trim()}`);
      setOldSku("");
      setNewSku("");
      setNotes("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    } finally {
      setSubmitting(false);
    }
  };

  const onResolve = async (e: React.FormEvent) => {
    e.preventDefault();
    setResolveOut(null);
    setError(null);
    try {
      const r = await resolveDmsSupersession(resolveSku.trim());
      if (r.error) {
        setResolveOut(`Error: ${r.error}`);
      } else if (r.superseded) {
        setResolveOut(
          `${r.sku} → ${r.current_sku} (hops ${r.hops}) · chain: ${(r.chain || []).join(" → ")}`
        );
      } else {
        setResolveOut(`${r.sku || resolveSku} is current (no supersession)`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Resolve failed");
    }
  };

  return (
    <div className="container mx-auto max-w-4xl p-6 space-y-6">
      <div className="rounded-lg border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-950">
        <strong>SKU supersession</strong> — map retired OEM numbers to current catalog SKUs.
        Search/query can surface redirects when DMS is local. No invented OEM partner feeds.
      </div>

      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <GitBranch className="h-6 w-6" />
            Supersessions
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            <code className="text-xs">/api/v1/dms/supersessions</code> · manager+ to write
          </p>
        </div>
        <Button variant="outline" size="sm" disabled={loading} onClick={() => void load()}>
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin mr-1" />
          ) : (
            <RefreshCw className="h-4 w-4 mr-1" />
          )}
          Refresh
        </Button>
      </div>

      {error ? (
        <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm flex gap-2">
          <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      ) : null}
      {flash ? (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm">
          {flash}
        </div>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Add mapping</CardTitle>
            <CardDescription>old_sku → new_sku (both must exist in catalog)</CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-3" onSubmit={onCreate}>
              <label className="text-sm block">
                Old SKU
                <input
                  className="mt-1 w-full rounded border px-2 py-1.5 font-mono text-sm"
                  value={oldSku}
                  onChange={(e) => setOldSku(e.target.value)}
                  required
                />
              </label>
              <label className="text-sm block">
                New SKU
                <input
                  className="mt-1 w-full rounded border px-2 py-1.5 font-mono text-sm"
                  value={newSku}
                  onChange={(e) => setNewSku(e.target.value)}
                  required
                />
              </label>
              <label className="text-sm block">
                Notes
                <input
                  className="mt-1 w-full rounded border px-2 py-1.5 text-sm"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                />
              </label>
              <Button type="submit" size="sm" disabled={submitting}>
                {submitting ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : null}
                Save mapping
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Resolve chain</CardTitle>
            <CardDescription>Walk old → current</CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-3" onSubmit={onResolve}>
              <label className="text-sm block">
                SKU
                <input
                  className="mt-1 w-full rounded border px-2 py-1.5 font-mono text-sm"
                  value={resolveSku}
                  onChange={(e) => setResolveSku(e.target.value)}
                  required
                />
              </label>
              <Button type="submit" size="sm" variant="secondary">
                Resolve
              </Button>
              {resolveOut ? (
                <p className="text-sm font-mono break-all bg-muted/40 p-2 rounded">{resolveOut}</p>
              ) : null}
            </form>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Mappings</CardTitle>
          <CardDescription>
            {loading ? "Loading…" : `${rows.length} row(s)`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!rows.length ? (
            <p className="text-sm text-muted-foreground">
              No supersessions yet. Seed DMS demo or add a mapping.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-muted-foreground border-b">
                    <th className="py-2 pr-2">Old</th>
                    <th className="py-2 pr-2">New</th>
                    <th className="py-2 pr-2">Notes</th>
                    <th className="py-2">When</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <tr key={`${r.id}-${r.old_sku}`} className="border-b last:border-0">
                      <td className="py-2 pr-2 font-mono text-xs">{r.old_sku}</td>
                      <td className="py-2 pr-2 font-mono text-xs">
                        <Badge variant="secondary">{r.new_sku}</Badge>
                      </td>
                      <td className="py-2 pr-2 text-muted-foreground">{r.notes || "—"}</td>
                      <td className="py-2 text-xs text-muted-foreground">
                        {r.created_at || "—"}
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
