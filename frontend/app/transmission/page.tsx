"use client";

import React, { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  formatTransmissionLocationLine,
  isTransmissionDemo,
} from "@/lib/demo-vertical";
import {
  transmissionInquiry,
  transmissionInquiryFeedback,
  type TransmissionInquiryResponse,
  formatOpsError,
  getActiveQuoteId,
  newIdempotencyKey,
  opsAddQuoteLine,
  opsCreateQuote,
  opsGetQuote,
  opsReserve,
  opsStock,
  setActiveQuoteId,
} from "@/lib/dms-api";
import {
  EmptyState,
  JpPage,
  OutcomeBadge,
  Panel,
  StockBadge,
} from "@/components/jp/ui";

const QUICK_QUERIES = [
  "Do you have a pump for a 2011 Tahoe 6L80?",
  "6L80 pump",
  "4L60E valve body",
  "Need a 6L80 core",
  "6R80 pump",
  "6L80 torque converter",
  "10R80 core",
  "24264418",
  "6L80-PUMP-01",
];

function TransmissionInquiryInner() {
  const searchParams = useSearchParams();
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<TransmissionInquiryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recentSearches, setRecentSearches] = useState<string[]>([]);
  const [feedbackBusy, setFeedbackBusy] = useState(false);
  const [feedbackDone, setFeedbackDone] = useState<{
    final_accepted_sku?: string | null;
    human_override?: boolean;
    feedback_action?: string;
  } | null>(null);
  const [correctOpen, setCorrectOpen] = useState(false);
  const [correctSku, setCorrectSku] = useState("");
  const [correctNote, setCorrectNote] = useState("");
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [bizBusy, setBizBusy] = useState(false);
  const [bizMsg, setBizMsg] = useState<string | null>(null);
  const [bizErr, setBizErr] = useState<string | null>(null);
  const [reserveOpen, setReserveOpen] = useState(false);
  const [reserveLoc, setReserveLoc] = useState("CHI-N");
  const [reserveQty, setReserveQty] = useState("1");
  const [stockRows, setStockRows] = useState<any[]>([]);
  const [condFilter, setCondFilter] = useState<string>("all");
  const [locFilter, setLocFilter] = useState<string>("all");
  const [availOnly, setAvailOnly] = useState(false);

  const runInquiry = async (q: string) => {
    if (!q.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setFeedbackDone(null);
    setCorrectOpen(false);
    setCorrectSku("");
    setCorrectNote("");
    setDetailsOpen(false);
    try {
      const res = await transmissionInquiry(q.trim());
      setResult(res);
      setRecentSearches((prev) => {
        const next = [q.trim(), ...prev.filter((x) => x !== q.trim())];
        return next.slice(0, 5);
      });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Search failed");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const q = searchParams?.get("q");
    if (q && q.trim()) {
      setQuery(q);
      void runInquiry(q);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  const submitFeedback = async (
    action: "accept" | "correct" | "resolve",
    finalSku?: string,
    note?: string
  ) => {
    if (!result?.request_id) {
      setError("Missing request id — search again.");
      return;
    }
    setFeedbackBusy(true);
    setError(null);
    try {
      const res = await transmissionInquiryFeedback({
        request_id: result.request_id,
        action,
        final_sku: finalSku,
        note,
      });
      setFeedbackDone({
        final_accepted_sku: res.final_accepted_sku,
        human_override: res.human_override,
        feedback_action: res.feedback_action,
      });
      setCorrectOpen(false);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to record result");
    } finally {
      setFeedbackBusy(false);
    }
  };

  const searchMode =
    result?.search_mode ||
    (result?.status === "inventory_matches"
      ? "inventory_matches"
      : result?.status === "resolved"
        ? "exact_match"
        : result
          ? "needs_review"
          : null);
  const unitOutcome =
    searchMode === "inventory_matches"
      ? null
      : result?.outcome ||
        (result?.status === "resolved" ? "RESOLVED" : result ? "NEEDS_HUMAN" : null);
  const needsHuman = unitOutcome === "NEEDS_HUMAN";
  const isBrowse = searchMode === "inventory_matches";
  const isExact = searchMode === "exact_match" || (!!unitOutcome && unitOutcome === "RESOLVED");
  const jp = isTransmissionDemo();
  const candidates = result?.discovery?.candidates || [];

  const filteredCandidates = candidates.filter((c) => {
    if (condFilter !== "all" && String(c.condition || "").toLowerCase() !== condFilter) return false;
    if (locFilter !== "all" && String(c.location_code || "") !== locFilter) return false;
    if (availOnly && Number(c.available || 0) <= 0) return false;
    return true;
  });
  const locOptions = Array.from(
    new Set(candidates.map((c) => String(c.location_code || "")).filter(Boolean))
  );
  const condOptions = Array.from(
    new Set(candidates.map((c) => String(c.condition || "").toLowerCase()).filter(Boolean))
  );

  const addLotToQuote = async (c: {
    sku?: string;
    location_code?: string;
    available?: number;
  }) => {
    if (!c.sku || !c.location_code) return;
    setBizBusy(true);
    setBizErr(null);
    setBizMsg(null);
    try {
      let qid = getActiveQuoteId();
      if (qid) {
        try {
          const q = (await opsGetQuote(qid)) as any;
          if (!["draft", "open"].includes(String(q.status || ""))) qid = null;
        } catch {
          qid = null;
        }
      }
      let updated: any;
      if (!qid) {
        const q = (await opsCreateQuote({ customer_label: "Walk-in" })) as any;
        qid = Number(q.id);
        updated = await opsAddQuoteLine(qid, {
          sku: String(c.sku),
          location: String(c.location_code),
          qty: 1,
        });
        setBizMsg(`Created ${updated.quote_number} and added ${c.sku}`);
      } else {
        updated = await opsAddQuoteLine(qid, {
          sku: String(c.sku),
          location: String(c.location_code),
          qty: 1,
        });
        setBizMsg(`Added ${c.sku} to ${updated.quote_number}`);
      }
      setActiveQuoteId(Number(updated.id));
    } catch (e) {
      setBizErr(formatOpsError(e, "Could not add to quote"));
    } finally {
      setBizBusy(false);
    }
  };

  const reserveLot = async (c: {
    sku?: string;
    location_code?: string;
    available?: number;
  }) => {
    if (!c.sku || !c.location_code) return;
    if (Number(c.available || 0) <= 0) {
      setBizErr("No available quantity on this lot.");
      return;
    }
    setBizBusy(true);
    setBizErr(null);
    setBizMsg(null);
    try {
      const key = newIdempotencyKey("disc-reserve");
      await opsReserve({
        sku: String(c.sku),
        location: String(c.location_code),
        qty: 1,
        idempotency_key: key,
      });
      setBizMsg(`Reserved 1 of ${c.sku} at ${c.location_code}.`);
    } catch (e) {
      setBizErr(formatOpsError(e));
    } finally {
      setBizBusy(false);
    }
  };

  const body = (
    <>
      {!jp ? (
        <div className="mb-6 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <strong>DEMO DATA — UNVERIFIED</strong>
        </div>
      ) : null}

      <Panel className="mb-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void runInquiry(query);
          }}
          className="space-y-3"
        >
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Counter search
          </div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Type what the customer is asking for — SKU, OEM, casting, vehicle, or plain English"
              className="h-12 flex-1 rounded-md border border-slate-300 bg-white px-4 text-[15px] focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-900/10"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="h-12 rounded-md bg-slate-900 px-6 text-[15px] font-semibold text-white disabled:opacity-50"
            >
              {loading ? "Searching…" : "Search"}
            </button>
          </div>
        </form>
        <div className="mt-3 flex flex-wrap gap-2">
          {QUICK_QUERIES.map((q) => (
            <button
              key={q}
              type="button"
              disabled={loading}
              onClick={() => {
                setQuery(q);
                void runInquiry(q);
              }}
              className="rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:border-slate-400 hover:bg-white"
            >
              {q.length > 48 ? q.slice(0, 46) + "…" : q}
            </button>
          ))}
        </div>
        {recentSearches.length > 0 ? (
          <div className="mt-3 text-xs text-slate-500">
            <span className="font-semibold text-slate-600">Recent: </span>
            {recentSearches.slice(0, 5).map((s, i) => (
              <button
                key={s}
                type="button"
                className="mr-2 hover:underline"
                onClick={() => {
                  setQuery(s);
                  void runInquiry(s);
                }}
              >
                {s}
                {i < Math.min(4, recentSearches.length - 1) ? "" : ""}
              </button>
            ))}
          </div>
        ) : null}
      </Panel>

      {error ? (
        <div className="mb-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </div>
      ) : null}

      {loading ? <EmptyState title="Searching catalog and inventory…" /> : null}

      {/* ---- INVENTORY MATCHES (dense catalog browse) ---- */}
      {!loading && result && isBrowse ? (
        <div className="space-y-4">
          <div className="rounded-lg border-2 border-slate-800 bg-slate-900 px-5 py-4 text-white">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <div className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                  Inventory matches
                </div>
                <div className="mt-1 text-2xl font-semibold tracking-tight">
                  {[result.transmission_family, result.part_type].filter(Boolean).join(" · ") ||
                    "Matching lots"}
                </div>
                <p className="mt-2 text-[15px] text-slate-200">
                  {result.discovery?.candidate_count ?? candidates.length} inventory lot
                  {(result.discovery?.candidate_count ?? candidates.length) === 1 ? "" : "s"}
                  {" · "}
                  {result.discovery?.total_available ?? 0} available
                  {" · "}
                  {result.discovery?.total_on_hand ?? 0} on hand
                </p>
              </div>
              <div className="text-right text-sm text-slate-300">
                Select a sellable unit — not an automatic single-SKU resolve.
              </div>
            </div>
          </div>

          {bizMsg ? (
            <div className="rounded border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900">
              {bizMsg}
            </div>
          ) : null}
          {bizErr ? (
            <div className="rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
              {bizErr}
            </div>
          ) : null}

          <Panel title="Filters">
            <div className="flex flex-wrap gap-3 text-sm">
              <label className="flex items-center gap-2">
                <span className="text-xs font-semibold uppercase text-slate-500">Condition</span>
                <select
                  value={condFilter}
                  onChange={(e) => setCondFilter(e.target.value)}
                  className="h-9 rounded-md border border-slate-300 px-2"
                >
                  <option value="all">All</option>
                  {condOptions.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex items-center gap-2">
                <span className="text-xs font-semibold uppercase text-slate-500">Location</span>
                <select
                  value={locFilter}
                  onChange={(e) => setLocFilter(e.target.value)}
                  className="h-9 rounded-md border border-slate-300 px-2"
                >
                  <option value="all">All</option>
                  {locOptions.map((c) => (
                    <option key={c} value={c}>
                      {c === "CHI-N" ? "Main Warehouse" : c === "OHARE" ? "Front Counter" : c}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
                <input
                  type="checkbox"
                  checked={availOnly}
                  onChange={(e) => setAvailOnly(e.target.checked)}
                />
                Available only
              </label>
              <a href="/quotes" className="ml-auto text-sm font-semibold text-slate-700 underline">
                Open quotes
              </a>
            </div>
          </Panel>

          <Panel flush title={`Lots (${filteredCandidates.length})`}>
            {filteredCandidates.length === 0 ? (
              <div className="p-5">
                <EmptyState title="No lots match these filters" />
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[980px] text-left text-sm">
                  <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                    <tr className="border-b border-slate-200">
                      <th className="px-3 py-2.5 font-semibold">SKU</th>
                      <th className="px-3 py-2.5 font-semibold">Description</th>
                      <th className="px-3 py-2.5 font-semibold">Type</th>
                      <th className="px-3 py-2.5 font-semibold">Variant</th>
                      <th className="px-3 py-2.5 font-semibold">Casting / ID</th>
                      <th className="px-3 py-2.5 font-semibold">Condition</th>
                      <th className="px-3 py-2.5 font-semibold">Location</th>
                      <th className="px-3 py-2.5 font-semibold">Bin</th>
                      <th className="px-3 py-2.5 text-right font-semibold">On hand</th>
                      <th className="px-3 py-2.5 text-right font-semibold">Rsv</th>
                      <th className="px-3 py-2.5 text-right font-semibold">Avail</th>
                      <th className="px-3 py-2.5 text-right font-semibold">Demo $</th>
                      <th className="px-3 py-2.5 font-semibold">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredCandidates.map((c, i) => {
                      const avail = Number(c.available || 0);
                      const locTitle =
                        c.location_code === "CHI-N"
                          ? "Main Warehouse"
                          : c.location_code === "OHARE"
                            ? "Front Counter"
                            : c.location_name || c.location_code;
                      return (
                        <tr
                          key={`${c.sku}-${c.location_code}-${i}`}
                          className="border-b border-slate-100 hover:bg-slate-50/80"
                        >
                          <td className="px-3 py-2 font-mono text-[13px] font-medium">{c.sku}</td>
                          <td className="px-3 py-2 text-[13px] text-slate-800">
                            <div className="font-medium">{c.name}</div>
                            {c.description && c.description !== c.name ? (
                              <div className="mt-0.5 max-w-xs truncate text-xs text-slate-500" title={c.description}>
                                {c.description}
                              </div>
                            ) : null}
                          </td>
                          <td className="px-3 py-2 text-xs capitalize">
                            {c.actual_part_category || c.part_type_label || "—"}
                          </td>
                          <td className="px-3 py-2 font-mono text-xs">{c.transmission_variant || "—"}</td>
                          <td className="px-3 py-2 font-mono text-xs">{c.casting_or_id || "—"}</td>
                          <td className="px-3 py-2 text-xs capitalize">{c.condition || "—"}</td>
                          <td className="px-3 py-2 text-[13px]">
                            <div>{locTitle}</div>
                            <div className="font-mono text-[11px] text-slate-400">{c.location_code}</div>
                          </td>
                          <td className="px-3 py-2 font-mono text-xs">{c.bin || "—"}</td>
                          <td className="px-3 py-2 text-right tabular-nums">{c.on_hand ?? 0}</td>
                          <td className="px-3 py-2 text-right tabular-nums">{c.reserved ?? 0}</td>
                          <td className="px-3 py-2 text-right tabular-nums font-semibold">{avail}</td>
                          <td className="px-3 py-2 text-right tabular-nums text-xs text-slate-600">
                            {c.list_price != null ? `$${Number(c.list_price).toFixed(2)}` : "—"}
                          </td>
                          <td className="px-3 py-2">
                            <div className="flex flex-wrap gap-1">
                              <button
                                type="button"
                                disabled={bizBusy}
                                className="h-8 rounded bg-slate-900 px-2 text-xs font-semibold text-white disabled:opacity-50"
                                onClick={() => void addLotToQuote(c)}
                              >
                                Quote
                              </button>
                              <button
                                type="button"
                                disabled={bizBusy || avail <= 0}
                                className="h-8 rounded border border-amber-400 bg-amber-50 px-2 text-xs font-semibold text-amber-950 disabled:opacity-40"
                                onClick={() => void reserveLot(c)}
                              >
                                Reserve
                              </button>
                              <a
                                href="/inventory"
                                className="inline-flex h-8 items-center rounded border border-slate-300 px-2 text-xs font-medium"
                              >
                                Inv
                              </a>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>
          <p className="text-xs text-slate-500">
            Application notes in descriptions are unverified source text — not DMS fitment.
            {result.elapsed_ms != null ? ` · ${Math.round(result.elapsed_ms)} ms` : ""}
          </p>
        </div>
      ) : null}

      {!loading && result && unitOutcome && !isBrowse ? (
        <div className="space-y-4">
          <div
            className={
              needsHuman
                ? "rounded-lg border-2 border-amber-300 bg-amber-50 px-5 py-4"
                : "rounded-lg border-2 border-emerald-300 bg-emerald-50 px-5 py-4"
            }
          >
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-3">
                <OutcomeBadge outcome={unitOutcome} />
                {typeof result.confidence === "number" ? (
                  <span className="text-sm tabular-nums text-slate-700">
                    Confidence {(result.confidence * 100).toFixed(0)}%
                  </span>
                ) : null}
              </div>
              {result.sku ? (
                <span className="font-mono text-xl font-semibold tracking-tight text-slate-900 sm:text-2xl">
                  {result.sku}
                </span>
              ) : null}
            </div>
            {result.recommended_action ? (
              <p className="mt-3 text-[15px] text-slate-800">
                <span className="font-semibold">Next step: </span>
                {result.recommended_action}
              </p>
            ) : null}
            {result.ambiguity_reason ? (
              <p className="mt-2 text-[15px] text-amber-950">
                <span className="font-semibold">Why review: </span>
                {result.ambiguity_reason}
              </p>
            ) : null}
          </div>

          {/* Business actions first when resolved; verification secondary */}
          {result.status === "resolved" && result.sku ? (
            <Panel title="Business actions">
              {bizMsg ? (
                <div className="mb-3 rounded border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900">
                  {bizMsg}
                </div>
              ) : null}
              {bizErr ? (
                <div className="mb-3 rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
                  {bizErr}
                </div>
              ) : null}
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={bizBusy}
                  className="h-11 rounded-md bg-slate-900 px-5 text-sm font-semibold text-white disabled:opacity-50"
                  onClick={async () => {
                      if (!result.sku) return;
                      setBizBusy(true);
                      setBizErr(null);
                      setBizMsg(null);
                      try {
                        let rows = stockRows;
                        if (!rows.length) {
                          const st = await opsStock({ sku: String(result.sku) });
                          rows = st.rows || [];
                          setStockRows(rows);
                        }
                        const withStock = rows.filter((r: any) => Number(r.available ?? r.on_hand ?? 0) > 0);
                        const loc =
                          withStock.length === 1
                            ? String(withStock[0].location_code || "CHI-N")
                            : withStock[0]
                              ? String(withStock[0].location_code || "CHI-N")
                              : "CHI-N";
                        let qid = getActiveQuoteId();
                        if (qid) {
                          try {
                            const q = (await opsGetQuote(qid)) as any;
                            if (!["draft", "open"].includes(String(q.status || ""))) qid = null;
                          } catch {
                            qid = null;
                          }
                        }
                        let updated: any;
                        if (!qid) {
                          const q = (await opsCreateQuote({ customer_label: "Walk-in" })) as any;
                          qid = Number(q.id);
                          updated = await opsAddQuoteLine(qid, { sku: String(result.sku), location: loc, qty: 1 });
                          setBizMsg(`Created ${updated.quote_number} and added ${result.sku}`);
                        } else {
                          updated = await opsAddQuoteLine(qid, { sku: String(result.sku), location: loc, qty: 1 });
                          setBizMsg(`Added ${result.sku} to ${updated.quote_number}`);
                        }
                        setActiveQuoteId(Number(updated.id));
                      } catch (e) {
                        setBizErr(formatOpsError(e, "Could not add to quote"));
                      } finally {
                        setBizBusy(false);
                      }
                    }}
                >
                  Add to Quote
                </button>
                <button
                  type="button"
                  disabled={bizBusy}
                  className="h-11 rounded-md border border-amber-400 bg-amber-50 px-5 text-sm font-semibold text-amber-950 disabled:opacity-50"
                  onClick={async () => {
                      if (!result.sku) return;
                      setBizErr(null);
                      setBizMsg(null);
                      try {
                        const st = await opsStock({ sku: String(result.sku) });
                        const rows = st.rows || [];
                        setStockRows(rows);
                        const withStock = rows.filter((r: any) => Number(r.available ?? 0) > 0);
                        if (withStock.length === 1) {
                          setReserveLoc(String(withStock[0].location_code || "CHI-N"));
                        } else if (withStock[0]) {
                          setReserveLoc(String(withStock[0].location_code || "CHI-N"));
                        }
                        setReserveQty("1");
                        setReserveOpen(true);
                      } catch (e) {
                        setBizErr(formatOpsError(e, "Could not load stock for reserve"));
                      }
                    }}
                >
                  Reserve
                </button>
                <a
                  className="inline-flex h-11 items-center rounded-md border border-slate-300 bg-white px-4 text-sm font-semibold text-slate-800"
                  href={`/inventory`}
                >
                  View Inventory
                </a>
                <a
                  className="inline-flex h-11 items-center rounded-md border border-slate-300 bg-white px-4 text-sm font-medium text-slate-700"
                  href="/quotes"
                >
                  Open Quotes
                </a>
              </div>
              {reserveOpen ? (
                  <div className="mt-4 space-y-3 rounded-md border border-amber-200 bg-white p-4">
                    <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Reserve inventory</div>
                    <label className="block text-sm font-medium text-slate-700">
                      Location
                      <select
                        value={reserveLoc}
                        onChange={(e) => setReserveLoc(e.target.value)}
                        className="mt-1 h-10 w-full rounded-md border border-slate-300 px-3 text-sm"
                      >
                        {(stockRows.length ? stockRows : [{ location_code: "CHI-N", available: 0 }]).map(
                          (r: any, i: number) => (
                            <option key={i} value={String(r.location_code)}>
                              {formatTransmissionLocationLine({ location: r.location_code }).title} · avail{" "}
                              {r.available ?? 0}
                            </option>
                          )
                        )}
                      </select>
                    </label>
                    <label className="block text-sm font-medium text-slate-700">
                      Quantity
                      <input
                        type="number"
                        min={1}
                        value={reserveQty}
                        onChange={(e) => setReserveQty(e.target.value)}
                        className="mt-1 h-10 w-full rounded-md border border-slate-300 px-3 text-sm"
                      />
                    </label>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        disabled={bizBusy}
                        className="h-10 rounded-md bg-amber-500 px-4 text-sm font-semibold text-amber-950 disabled:opacity-50"
                        onClick={async () => {
                          if (!result.sku) return;
                          setBizBusy(true);
                          setBizErr(null);
                          try {
                            const n = Number(reserveQty);
                            if (!Number.isFinite(n) || n <= 0) throw new Error("Enter a positive quantity.");
                            const row = stockRows.find((r: any) => String(r.location_code) === reserveLoc);
                            const avail = Number(row?.available ?? 0);
                            if (n > avail) {
                              throw new Error(
                                `Only ${avail} units are available. You attempted to reserve ${n}.`
                              );
                            }
                            const key = newIdempotencyKey("search-reserve");
                            await opsReserve({
                              sku: String(result.sku),
                              location: reserveLoc,
                              qty: n,
                              idempotency_key: key,
                            });
                            setBizMsg(`Reserved ${n} of ${result.sku} at ${reserveLoc}.`);
                            setReserveOpen(false);
                          } catch (e) {
                            setBizErr(formatOpsError(e));
                          } finally {
                            setBizBusy(false);
                          }
                        }}
                      >
                        {bizBusy ? "Working…" : "Confirm reserve"}
                      </button>
                      <button
                        type="button"
                        className="h-10 rounded-md border border-slate-300 px-4 text-sm font-medium"
                        onClick={() => setReserveOpen(false)}
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : null}
            </Panel>
          ) : null}

          <Panel title={needsHuman ? "Resolve request" : "Verify match"}>
            {feedbackDone ? (
              <div className="space-y-1 text-sm">
                <div className="text-base font-semibold text-slate-900">Final result recorded</div>
                <p>
                  SKU{" "}
                  <span className="font-mono font-semibold">
                    {feedbackDone.final_accepted_sku || "—"}
                  </span>
                  {feedbackDone.human_override
                    ? " · corrected by counter"
                    : " · accepted as matched"}
                </p>
              </div>
            ) : needsHuman ? (
              <div className="space-y-3">
                <p className="text-[15px] text-slate-700">
                  The system intentionally stopped — it will not auto-assign a part. Enter the final SKU when verified at the counter.
                </p>
                {!correctOpen ? (
                  <button
                    type="button"
                    disabled={feedbackBusy || !result.request_id}
                    className="h-11 rounded-md bg-amber-600 px-5 text-sm font-semibold text-white disabled:opacity-50"
                    onClick={() => setCorrectOpen(true)}
                  >
                    Resolve Request
                  </button>
                ) : (
                  <div className="space-y-2">
                    <input
                      value={correctSku}
                      onChange={(e) => setCorrectSku(e.target.value)}
                      placeholder="Final SKU"
                      className="h-10 w-full rounded-md border border-slate-300 px-3 font-mono text-sm"
                    />
                    <input
                      value={correctNote}
                      onChange={(e) => setCorrectNote(e.target.value)}
                      placeholder="Optional note"
                      className="h-10 w-full rounded-md border border-slate-300 px-3 text-sm"
                    />
                    <div className="flex gap-2">
                      <button
                        type="button"
                        disabled={feedbackBusy || !correctSku.trim()}
                        className="h-10 rounded-md bg-slate-900 px-4 text-sm font-semibold text-white disabled:opacity-50"
                        onClick={() =>
                          void submitFeedback(
                            "resolve",
                            correctSku.trim(),
                            correctNote.trim() || undefined
                          )
                        }
                      >
                        Save final result
                      </button>
                      <button
                        type="button"
                        className="h-10 rounded-md border border-slate-300 px-4 text-sm"
                        onClick={() => setCorrectOpen(false)}
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="space-y-2">
                <p className="text-sm text-slate-500">
                  System verification — separate from quoting and reserving stock.
                </p>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={feedbackBusy || !result.request_id}
                    className="h-10 rounded-md border border-emerald-300 bg-emerald-50 px-4 text-sm font-semibold text-emerald-950 disabled:opacity-50"
                    onClick={() => void submitFeedback("accept")}
                  >
                    Accept Match
                  </button>
                  <button
                    type="button"
                    disabled={feedbackBusy || !result.request_id}
                    className="h-10 rounded-md border border-slate-300 bg-white px-4 text-sm font-medium disabled:opacity-50"
                    onClick={() => {
                      setCorrectOpen(true);
                      setCorrectSku(result.sku || "");
                    }}
                  >
                    Correct Match
                  </button>
                </div>
                {correctOpen ? (
                  <div className="space-y-2 border-t border-slate-100 pt-3">
                    <input
                      value={correctSku}
                      onChange={(e) => setCorrectSku(e.target.value)}
                      placeholder="Correct SKU"
                      className="h-10 w-full rounded-md border border-slate-300 px-3 font-mono text-sm"
                    />
                    <input
                      value={correctNote}
                      onChange={(e) => setCorrectNote(e.target.value)}
                      placeholder="Optional note"
                      className="h-10 w-full rounded-md border border-slate-300 px-3 text-sm"
                    />
                    <div className="flex gap-2">
                      <button
                        type="button"
                        disabled={feedbackBusy || !correctSku.trim()}
                        className="h-10 rounded-md bg-slate-900 px-4 text-sm font-semibold text-white disabled:opacity-50"
                        onClick={() =>
                          void submitFeedback(
                            "correct",
                            correctSku.trim(),
                            correctNote.trim() || undefined
                          )
                        }
                      >
                        Save correction
                      </button>
                      <button
                        type="button"
                        className="h-10 rounded-md border border-slate-300 px-4 text-sm"
                        onClick={() => setCorrectOpen(false)}
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : null}
              </div>
            )}
          </Panel>

          {result.status === "resolved" && result.sku ? (
            <Panel title="Part match">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <div className="font-mono text-3xl font-semibold tracking-tight text-slate-900">
                    {result.sku}
                  </div>
                  <div className="mt-2 text-[15px] text-slate-600">
                    {result.human_readable ||
                      [result.transmission_family, result.part_type]
                        .filter(Boolean)
                        .join(" · ")}
                  </div>
                </div>
                <StockBadge qty={result.aggregate_available ?? 0} />
              </div>

              <div className="mt-5 grid grid-cols-2 gap-4 text-sm md:grid-cols-4">
                <div className="rounded-md border border-slate-100 bg-slate-50 px-3 py-2.5">
                  <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Family</div>
                  <div className="mt-1 font-mono text-[15px] font-medium">{result.transmission_family || "—"}</div>
                </div>
                <div className="rounded-md border border-slate-100 bg-slate-50 px-3 py-2.5">
                  <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Part type</div>
                  <div className="mt-1 text-[15px] font-medium capitalize">{result.part_type || "—"}</div>
                </div>
                <div className="rounded-md border border-slate-100 bg-slate-50 px-3 py-2.5">
                  <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Available</div>
                  <div className="mt-1 text-2xl font-semibold tabular-nums text-slate-900">
                    {result.aggregate_available ?? 0}
                  </div>
                </div>
                <div className="rounded-md border border-slate-100 bg-slate-50 px-3 py-2.5">
                  <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Data status</div>
                  <div className="mt-1 text-[15px] capitalize">
                    {result.verification_status || "unverified"}
                  </div>
                </div>
              </div>

              {result.inventory && result.inventory.length > 0 ? (
                <div className="mt-5">
                  <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Locations
                  </div>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {result.inventory.map((inv, idx) => {
                      const loc = formatTransmissionLocationLine(inv);
                      return (
                        <div
                          key={idx}
                          className="flex items-center justify-between rounded-md border border-slate-200 bg-white px-4 py-3 text-sm"
                        >
                          <div>
                            <div className="text-[15px] font-semibold text-slate-900">{loc.title}</div>
                            <div className="font-mono text-xs text-slate-500">
                              {loc.subtitle}
                            </div>
                          </div>
                          <div className="text-right">
                            <div className="text-lg font-semibold tabular-nums">{inv.qty}</div>
                            <div className="text-xs capitalize text-slate-500">
                              {inv.condition}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ) : null}

              {result.identifiers && result.identifiers.length > 0 ? (
                <div className="mt-5">
                  <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Identifiers
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {result.identifiers.map((id, idx) => (
                      <span
                        key={idx}
                        className="rounded-md border border-slate-200 bg-white px-2.5 py-1 font-mono text-[13px]"
                      >
                        {id.identifier_type}: {id.identifier_value}
                      </span>
                    ))}
                  </div>
                </div>
              ) : null}

              {result.interchanges && result.interchanges.length > 0 ? (
                <div className="mt-5">
                  <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Interchange
                  </div>
                  <div className="space-y-1 font-mono text-[13px] text-slate-600">
                    {result.interchanges.map((ic, idx) => (
                      <div key={idx}>
                        {ic.source_sku} → {ic.target_sku} · {ic.relationship_type} ·{" "}
                        {ic.verification_status}
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}

              <button
                type="button"
                className="mt-5 text-xs font-medium text-slate-500 hover:underline"
                onClick={() => setDetailsOpen((v) => !v)}
              >
                {detailsOpen ? "Hide technical detail" : "Show technical detail"}
              </button>
              {detailsOpen ? (
                <pre className="mt-2 overflow-x-auto rounded bg-slate-950 p-3 text-[11px] text-slate-200">
                  {JSON.stringify(
                    {
                      status: result.status,
                      fitment_status: result.fitment_status,
                      evidence_sufficiency: result.evidence_sufficiency,
                      candidate_match_quality: result.candidate_match_quality,
                      decision_source: result.decision_source,
                      request_id: result.request_id,
                    },
                    null,
                    2
                  )}
                </pre>
              ) : null}
            </Panel>
          ) : needsHuman ? (
            <Panel title="What to verify">
              <p className="text-[15px] leading-relaxed text-slate-700">
                {result.human_readable ||
                  result.ambiguity_reason ||
                  "Provide OEM/casting number, exact family, or part type so the counter can finish the match."}
              </p>
            </Panel>
          ) : null}
        </div>
      ) : null}

      {!loading && !result ? (
        <EmptyState
          title="Type what the customer is asking for"
          body="Search by natural language, SKU, OEM number, casting number, or vehicle/transmission. Matches show stock and locations; when evidence is incomplete the system stops for review instead of guessing."
          className="py-14"
        >
          <div className="mx-auto grid max-w-2xl gap-2 text-left text-sm text-slate-600 sm:grid-cols-2">
            <div className="rounded-md border border-slate-200 bg-white px-3 py-2">
              <div className="text-xs font-semibold uppercase text-slate-500">Natural language</div>
              <div className="mt-1">Need a 6L80 pump for a 2011 Tahoe</div>
            </div>
            <div className="rounded-md border border-slate-200 bg-white px-3 py-2">
              <div className="text-xs font-semibold uppercase text-slate-500">SKU / OEM</div>
              <div className="mt-1 font-mono">6L80-PUMP-01 · 24264418</div>
            </div>
          </div>
        </EmptyState>
      ) : null}
    </>
  );

  if (jp) {
    return (
      <JpPage
        title="Parts Search"
        description="Counter workspace — look up transmission hard parts by natural language, SKU, OEM, or casting number."
        fullBleed
      >
        {body}
      </JpPage>
    );
  }
  return <div className="container mx-auto max-w-5xl p-6">{body}</div>;
}

export default function TransmissionInquiryPage() {
  return (
    <Suspense fallback={<div className="p-6 text-sm text-slate-500">Loading search…</div>}>
      <TransmissionInquiryInner />
    </Suspense>
  );
}
