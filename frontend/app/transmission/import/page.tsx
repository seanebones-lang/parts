"use client";

import Link from "next/link";
import React, { useEffect, useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  ApiError,
  commitTransmissionImport,
  commitTransmissionImportRollback,
  isApiUnreachable,
  listTransmissionImportHistory,
  previewTransmissionImport,
  previewTransmissionImportRollback,
  type TransmissionImportHistoryItem,
  type TransmissionImportResult,
  type TransmissionImportRollbackPreview,
  type TransmissionImportRowPlan,
} from "@/lib/dms-api";

function catalogActionLabel(action?: string): string {
  switch (action) {
    case "insert":
      return "New catalog SKU";
    case "preserve":
      return "Existing catalog preserved";
    case "conflict":
      return "Catalog conflict";
    case "none":
      return "No catalog change";
    default:
      return action || "—";
  }
}

function statusBadge(status?: string) {
  if (status === "valid") {
    return <Badge className="bg-emerald-600">valid</Badge>;
  }
  if (status === "warning") {
    return <Badge className="bg-amber-600">warning</Badge>;
  }
  if (status === "invalid") {
    return <Badge variant="destructive">invalid</Badge>;
  }
  return <Badge variant="outline">{status || "—"}</Badge>;
}

export default function TransmissionImportPage() {
  const [fileName, setFileName] = useState<string>("");
  const [fileSize, setFileSize] = useState<number>(0);
  const [csvText, setCsvText] = useState<string>("");
  const [sourceLabel, setSourceLabel] = useState<string>("");
  const [allowNewLocations, setAllowNewLocations] = useState(false);

  const [preview, setPreview] = useState<TransmissionImportResult | null>(null);
  const [previewKey, setPreviewKey] = useState<string>("");
  const [commitResult, setCommitResult] = useState<TransmissionImportResult | null>(
    null
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [history, setHistory] = useState<TransmissionImportHistoryItem[]>([]);
  const [rbPreview, setRbPreview] = useState<TransmissionImportRollbackPreview | null>(
    null
  );
  const [rbRunId, setRbRunId] = useState<number | null>(null);
  const [rbConfirm, setRbConfirm] = useState(false);

  async function refreshHistory() {
    try {
      const res = await listTransmissionImportHistory(30);
      setHistory(res.imports || []);
    } catch {
      // history is best-effort on this page
    }
  }

  useEffect(() => {
    void refreshHistory();
  }, []);

  const currentKey = useMemo(
    () =>
      JSON.stringify({
        fileName,
        csvText,
        sourceLabel,
        allowNewLocations,
      }),
    [fileName, csvText, sourceLabel, allowNewLocations]
  );

  const previewIsCurrent = Boolean(preview && previewKey === currentKey);
  const canCommit =
    previewIsCurrent &&
    Boolean(preview?.ok) &&
    (preview?.invalid_rows || 0) === 0 &&
    !(preview?.file_errors && preview.file_errors.length > 0) &&
    !busy;

  function invalidatePreview() {
    setPreview(null);
    setPreviewKey("");
    setCommitResult(null);
    setConfirmOpen(false);
  }

  async function onFileChange(file: File | null) {
    invalidatePreview();
    setError(null);
    if (!file) {
      setFileName("");
      setFileSize(0);
      setCsvText("");
      setSourceLabel("");
      return;
    }
    const text = await file.text();
    setFileName(file.name);
    setFileSize(file.size);
    setCsvText(text);
    setSourceLabel(`pilot_csv:${file.name}`);
  }

  async function runPreview() {
    if (!csvText.trim()) {
      setError("Select a CSV file first.");
      return;
    }
    setBusy(true);
    setError(null);
    setCommitResult(null);
    setConfirmOpen(false);
    try {
      const res = await previewTransmissionImport({
        csv_text: csvText,
        source: sourceLabel || undefined,
        allow_new_locations: allowNewLocations,
      });
      setPreview(res);
      setPreviewKey(currentKey);
    } catch (e: unknown) {
      if (isApiUnreachable(e)) {
        setError("Transmission import API unreachable. Retry when the API is online.");
      } else if (e instanceof ApiError) {
        setError(e.message || `API error ${e.status}`);
      } else if (e instanceof Error) {
        setError(e.message);
      } else {
        setError("Preview failed");
      }
      setPreview(null);
      setPreviewKey("");
    } finally {
      setBusy(false);
    }
  }

  async function runCommit() {
    if (!canCommit || !csvText.trim()) return;
    setBusy(true);
    setError(null);
    setConfirmOpen(false);
    try {
      const res = await commitTransmissionImport({
        csv_text: csvText,
        source: sourceLabel || undefined,
        allow_new_locations: allowNewLocations,
      });
      setCommitResult(res);
      if (!res.committed) {
        setError(
          (res.commit_result &&
            typeof res.commit_result === "object" &&
            "reason" in res.commit_result &&
            String((res.commit_result as { reason?: string }).reason)) ||
            "Commit refused. Nothing was written."
        );
      } else {
        await refreshHistory();
      }
    } catch (e: unknown) {
      if (isApiUnreachable(e)) {
        setError("Transmission import API unreachable. Retry when the API is online.");
      } else if (e instanceof ApiError) {
        setError(e.message || `API error ${e.status}`);
      } else if (e instanceof Error) {
        setError(e.message);
      } else {
        setError("Commit failed");
      }
    } finally {
      setBusy(false);
    }
  }

  const rows: TransmissionImportRowPlan[] = preview?.rows || [];

  return (
    <div className="container mx-auto max-w-6xl p-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Pilot Data Import</h1>
          <p className="mt-1 text-muted-foreground">
            Manager/operator inventory onboarding · preview first · explicit commit
          </p>
        </div>
        <Button asChild variant="outline">
          <Link href="/transmission">Open Transmission Counter</Link>
        </Button>
      </div>

      <div className="mb-6 rounded-lg border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-800">
        Existing catalog identity is preserved for matching SKUs. This workflow loads
        physical inventory and new pilot SKUs only. Fitment and interchange are not
        invented from the CSV.
      </div>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>1. Select CSV</CardTitle>
          <CardDescription>
            Browser reads the local file as text. Nothing is written until you commit.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <input
            type="file"
            accept=".csv,text/csv"
            disabled={busy}
            onChange={(e) => onFileChange(e.target.files?.[0] || null)}
          />
          {fileName ? (
            <div className="font-mono text-sm text-muted-foreground">
              {fileName} · {(fileSize / 1024).toFixed(1)} KB
            </div>
          ) : null}

          <div className="grid gap-3 md:grid-cols-2">
            <label className="block text-sm">
              <span className="mb-1 block font-medium">Source / import label</span>
              <input
                className="w-full rounded-md border bg-background px-3 py-2 font-mono text-sm"
                value={sourceLabel}
                disabled={busy || !csvText}
                onChange={(e) => {
                  setSourceLabel(e.target.value);
                  invalidatePreview();
                }}
                placeholder="pilot_csv:filename.csv"
              />
            </label>
            <label className="flex items-start gap-2 pt-6 text-sm">
              <input
                type="checkbox"
                className="mt-1"
                checked={allowNewLocations}
                disabled={busy || !csvText}
                onChange={(e) => {
                  setAllowNewLocations(e.target.checked);
                  invalidatePreview();
                }}
              />
              <span>
                <span className="font-medium">Allow new locations</span>
                <span className="mt-1 block text-muted-foreground">
                  Creates exact location codes found in the file. Leave off unless the
                  codes are intentional.
                </span>
              </span>
            </label>
          </div>

          <Button onClick={runPreview} disabled={busy || !csvText.trim()}>
            {busy ? "Working..." : "Preview Import"}
          </Button>
        </CardContent>
      </Card>

      {error ? (
        <Card className="mb-6 border-red-200 bg-red-50">
          <CardHeader>
            <CardTitle className="text-red-900">Import error</CardTitle>
            <CardDescription className="text-red-800">{error}</CardDescription>
          </CardHeader>
        </Card>
      ) : null}

      {previewIsCurrent && preview ? (
        <Card className="mb-6">
          <CardHeader>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <CardTitle>2. Preview</CardTitle>
                <CardDescription>
                  mode: {preview.mode} · source: {preview.source_label || "—"}
                </CardDescription>
              </div>
              {preview.ok ? (
                (preview.warning_rows || 0) > 0 ? (
                  <Badge className="bg-amber-600">Warnings — commit allowed</Badge>
                ) : (
                  <Badge className="bg-emerald-600">Ready to import</Badge>
                )
              ) : (
                <Badge variant="destructive">Validation failed</Badge>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
              <div>
                <div className="text-muted-foreground">Total rows</div>
                <div className="font-mono text-lg font-semibold">{preview.total_rows ?? 0}</div>
              </div>
              <div>
                <div className="text-muted-foreground">Valid</div>
                <div className="font-mono text-lg font-semibold">{preview.valid_rows ?? 0}</div>
              </div>
              <div>
                <div className="text-muted-foreground">Warnings</div>
                <div className="font-mono text-lg font-semibold">{preview.warning_rows ?? 0}</div>
              </div>
              <div>
                <div className="text-muted-foreground">Invalid</div>
                <div className="font-mono text-lg font-semibold text-red-700">
                  {preview.invalid_rows ?? 0}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
              <div>
                <div className="text-muted-foreground">New SKUs</div>
                <div className="font-mono font-semibold">{preview.new_sku_count ?? 0}</div>
              </div>
              <div>
                <div className="text-muted-foreground">Existing SKUs preserved</div>
                <div className="font-mono font-semibold">{preview.existing_sku_count ?? 0}</div>
              </div>
              <div>
                <div className="text-muted-foreground">Inventory inserts</div>
                <div className="font-mono font-semibold">{preview.inventory_inserts ?? 0}</div>
              </div>
              <div>
                <div className="text-muted-foreground">Inventory updates</div>
                <div className="font-mono font-semibold">{preview.inventory_updates ?? 0}</div>
              </div>
              <div>
                <div className="text-muted-foreground">Catalog inserts</div>
                <div className="font-mono font-semibold">{preview.catalog_inserts ?? 0}</div>
              </div>
              <div>
                <div className="text-muted-foreground">Identifier inserts</div>
                <div className="font-mono font-semibold">{preview.identifier_inserts ?? 0}</div>
              </div>
              <div>
                <div className="text-muted-foreground">New locations planned</div>
                <div className="font-mono font-semibold">{preview.locations_to_create ?? 0}</div>
              </div>
              <div>
                <div className="text-muted-foreground">Unknown locations</div>
                <div className="font-mono font-semibold">
                  {(preview.unknown_locations || []).length}
                </div>
              </div>
            </div>

            {(preview.file_errors || []).length > 0 ? (
              <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-900">
                <div className="mb-1 font-medium">File errors</div>
                <ul className="list-disc pl-5 font-mono text-xs">
                  {(preview.file_errors || []).map((e, i) => (
                    <li key={i}>{e}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            {(preview.unknown_locations || []).length > 0 ? (
              <div className="rounded border border-amber-200 bg-amber-50 p-3 text-sm">
                Unknown locations:{" "}
                <span className="font-mono">
                  {(preview.unknown_locations || []).join(", ")}
                </span>
              </div>
            ) : null}

            {preview.rows_truncated ? (
              <div className="text-sm text-muted-foreground">
                Row list truncated; {preview.rows_truncated} additional rows not shown.
              </div>
            ) : null}

            <div className="overflow-x-auto rounded border">
              <table className="min-w-full text-left text-xs">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="px-2 py-2">Row</th>
                    <th className="px-2 py-2">Status</th>
                    <th className="px-2 py-2">SKU</th>
                    <th className="px-2 py-2">Name</th>
                    <th className="px-2 py-2">Family</th>
                    <th className="px-2 py-2">Loc</th>
                    <th className="px-2 py-2">Qty</th>
                    <th className="px-2 py-2">Cond</th>
                    <th className="px-2 py-2">Catalog</th>
                    <th className="px-2 py-2">Inventory</th>
                    <th className="px-2 py-2">Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <tr key={r.row_number} className="border-t align-top">
                      <td className="px-2 py-2 font-mono">{r.row_number}</td>
                      <td className="px-2 py-2">{statusBadge(r.status)}</td>
                      <td className="px-2 py-2 font-mono">{r.sku}</td>
                      <td className="px-2 py-2">{r.name}</td>
                      <td className="px-2 py-2 font-mono">{r.transmission_family}</td>
                      <td className="px-2 py-2 font-mono">{r.location}</td>
                      <td className="px-2 py-2 font-mono">{r.qty}</td>
                      <td className="px-2 py-2">{r.condition}</td>
                      <td className="px-2 py-2">{catalogActionLabel(r.catalog_action)}</td>
                      <td className="px-2 py-2 font-mono">{r.inventory_action}</td>
                      <td className="px-2 py-2 text-[11px] text-muted-foreground">
                        {[...(r.errors || []), ...(r.warnings || [])].join(" · ") || "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex flex-wrap gap-3">
              <Button
                disabled={!canCommit}
                onClick={() => setConfirmOpen(true)}
              >
                Commit Import
              </Button>
              {!canCommit ? (
                <span className="self-center text-sm text-muted-foreground">
                  Commit stays disabled until a current valid preview exists.
                </span>
              ) : null}
            </div>

            {confirmOpen ? (
              <div className="rounded border border-slate-300 bg-slate-50 p-4">
                <div className="mb-2 font-medium">Confirm commit</div>
                <p className="mb-3 text-sm text-muted-foreground">
                  This will write validated catalog/inventory data to the canonical DMS.
                </p>
                <ul className="mb-4 list-disc pl-5 font-mono text-xs">
                  <li>rows: {preview.valid_rows ?? 0}</li>
                  <li>new SKUs: {preview.new_sku_count ?? 0}</li>
                  <li>inventory inserts: {preview.inventory_inserts ?? 0}</li>
                  <li>inventory updates: {preview.inventory_updates ?? 0}</li>
                  <li>new locations: {preview.locations_to_create ?? 0}</li>
                </ul>
                <div className="flex gap-2">
                  <Button disabled={busy} onClick={runCommit}>
                    {busy ? "Committing..." : "Confirm write"}
                  </Button>
                  <Button
                    variant="outline"
                    disabled={busy}
                    onClick={() => setConfirmOpen(false)}
                  >
                    Cancel
                  </Button>
                </div>
              </div>
            ) : null}
          </CardContent>
        </Card>
      ) : null}

      {commitResult ? (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>3. Commit result</CardTitle>
            <CardDescription>
              {commitResult.committed
                ? "Import committed successfully"
                : "Commit refused — nothing written"}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4 font-mono">
              <div>committed: {String(Boolean(commitResult.committed))}</div>
              <div>
                import run:{" "}
                {String(
                  (commitResult.commit_result as { import_run_id?: number } | undefined)
                    ?.import_run_id ?? "—"
                )}
              </div>
              <div>catalog inserts: {commitResult.catalog_inserts ?? 0}</div>
              <div>inventory inserts: {commitResult.inventory_inserts ?? 0}</div>
              <div>inventory updates: {commitResult.inventory_updates ?? 0}</div>
              <div>identifier inserts: {commitResult.identifier_inserts ?? 0}</div>
              <div>locations created: {commitResult.locations_to_create ?? 0}</div>
              <div>
                rollback available:{" "}
                {String(
                  Boolean(
                    (commitResult.commit_result as { rollback_available?: boolean } | undefined)
                      ?.rollback_available
                  )
                )}
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button asChild>
                <Link href="/transmission">Open Transmission Counter</Link>
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  invalidatePreview();
                  setFileName("");
                  setFileSize(0);
                  setCsvText("");
                  setSourceLabel("");
                  setAllowNewLocations(false);
                  setError(null);
                }}
              >
                Preview Another File
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : null}

      <Card className="mb-6">
        <CardHeader>
          <div className="flex items-center justify-between gap-3">
            <div>
              <CardTitle>Import History</CardTitle>
              <CardDescription>
                Successful pilot imports with rollback eligibility
              </CardDescription>
            </div>
            <Button variant="outline" size="sm" onClick={() => void refreshHistory()}>
              Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {history.length === 0 ? (
            <div className="text-sm text-muted-foreground">No import runs yet.</div>
          ) : (
            <div className="space-y-2">
              {history.map((h) => (
                <div
                  key={String(h.import_run_id)}
                  className="flex flex-wrap items-center justify-between gap-3 rounded border px-3 py-2 text-sm"
                >
                  <div className="font-mono text-xs">
                    #{h.import_run_id} · {h.created_at} · {h.source_label}
                    <div className="text-muted-foreground">
                      rows {h.valid_rows ?? "—"} · inv+{h.inventory_inserts ?? 0}/upd
                      {h.inventory_updates ?? 0} · skus+{h.catalog_inserts ?? 0} ·{" "}
                      {h.rollback_status || "—"}
                    </div>
                  </div>
                  {h.rollback_available ? (
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={busy}
                      onClick={async () => {
                        if (!h.import_run_id) return;
                        setBusy(true);
                        setError(null);
                        try {
                          const p = await previewTransmissionImportRollback(
                            Number(h.import_run_id)
                          );
                          setRbPreview(p);
                          setRbRunId(Number(h.import_run_id));
                          setRbConfirm(false);
                        } catch (e: unknown) {
                          setError(
                            e instanceof Error ? e.message : "Rollback preview failed"
                          );
                        } finally {
                          setBusy(false);
                        }
                      }}
                    >
                      Review rollback
                    </Button>
                  ) : (
                    <Badge variant="outline">{h.rollback_status || "unavailable"}</Badge>
                  )}
                </div>
              ))}
            </div>
          )}

          {rbPreview && rbRunId != null ? (
            <div className="rounded border bg-slate-50 p-4 text-sm">
              <div className="mb-2 font-medium">
                Rollback preview for import #{rbRunId}
              </div>
              <div className="mb-2 font-mono text-xs">
                eligible: {String(Boolean(rbPreview.eligible))} · restores:{" "}
                {rbPreview.inventory_restores ?? 0} · deletes:{" "}
                {rbPreview.rows_to_delete ?? 0}
              </div>
              {rbPreview.reason ? (
                <div className="mb-2 text-red-800">{rbPreview.reason}</div>
              ) : null}
              {(rbPreview.conflicts || []).length > 0 ? (
                <div className="mb-3 space-y-1">
                  <div className="font-medium">Conflicts</div>
                  {(rbPreview.conflicts || []).map((c, i) => (
                    <div key={i} className="rounded border border-red-200 bg-red-50 p-2 font-mono text-[11px]">
                      {JSON.stringify(c)}
                    </div>
                  ))}
                </div>
              ) : null}
              {rbPreview.eligible ? (
                <div className="space-y-2">
                  <p className="text-muted-foreground">
                    Restore the DMS values that existed immediately before import #{rbRunId}.
                    Rollback will refuse if affected data changed after the import.
                  </p>
                  {!rbConfirm ? (
                    <Button size="sm" onClick={() => setRbConfirm(true)}>
                      Confirm rollback review
                    </Button>
                  ) : (
                    <Button
                      size="sm"
                      disabled={busy}
                      onClick={async () => {
                        setBusy(true);
                        setError(null);
                        try {
                          const res = await commitTransmissionImportRollback(rbRunId);
                          if (!res.rolled_back) {
                            setError(String(res.reason || "Rollback refused"));
                            const p = await previewTransmissionImportRollback(rbRunId);
                            setRbPreview(p);
                          } else {
                            setRbPreview(null);
                            setRbRunId(null);
                            setRbConfirm(false);
                            await refreshHistory();
                          }
                        } catch (e: unknown) {
                          setError(
                            e instanceof Error ? e.message : "Rollback failed"
                          );
                        } finally {
                          setBusy(false);
                        }
                      }}
                    >
                      Execute rollback
                    </Button>
                  )}
                </div>
              ) : null}
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
