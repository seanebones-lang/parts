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
  "Do you have 24264418?",
  "Do you have 6L80-PUMP-01?",
  "Do you have a 6R80 pump?",
  "Do you have a 4L60E valve body?",
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

  const unitOutcome =
    result?.outcome ||
    (result?.status === "resolved" ? "RESOLVED" : result ? "NEEDS_HUMAN" : null);
  const needsHuman = unitOutcome === "NEEDS_HUMAN";
  const jp = isTransmissionDemo();

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
          className="flex gap-2"
        >
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="SKU, OEM, casting, vehicle, or natural-language request"
            className="h-11 flex-1 rounded-md border border-slate-300 bg-white px-3 text-sm focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-900/10"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="h-11 rounded-md bg-slate-900 px-5 text-sm font-semibold text-white disabled:opacity-50"
          >
            {loading ? "Searching…" : "Search"}
          </button>
        </form>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {QUICK_QUERIES.map((q) => (
            <button
              key={q}
              type="button"
              disabled={loading}
              onClick={() => {
                setQuery(q);
                void runInquiry(q);
              }}
              className="rounded border border-slate-200 bg-slate-50 px-2 py-1 text-[11px] text-slate-600 hover:border-slate-400"
            >
              {q.length > 42 ? q.slice(0, 40) + "…" : q}
            </button>
          ))}
        </div>
        {recentSearches.length > 0 ? (
          <div className="mt-2 text-[11px] text-slate-400">
            Recent: {recentSearches.slice(0, 3).join(" · ")}
          </div>
        ) : null}
      </Panel>

      {error ? (
        <div className="mb-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </div>
      ) : null}

      {loading ? <EmptyState title="Searching catalog and inventory…" /> : null}

      {!loading && result && unitOutcome ? (
        <div className="space-y-4">
          <div
            className={
              needsHuman
                ? "rounded-lg border border-amber-200 bg-amber-50 px-4 py-3"
                : "rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3"
            }
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <OutcomeBadge outcome={unitOutcome} />
                {typeof result.confidence === "number" ? (
                  <span className="text-xs tabular-nums text-slate-600">
                    Confidence {(result.confidence * 100).toFixed(0)}%
                  </span>
                ) : null}
              </div>
              {result.sku ? (
                <span className="font-mono text-sm font-semibold text-slate-900">
                  {result.sku}
                </span>
              ) : null}
            </div>
            {result.recommended_action ? (
              <p className="mt-2 text-sm text-slate-800">
                <span className="font-medium">Recommended: </span>
                {result.recommended_action}
              </p>
            ) : null}
            {result.ambiguity_reason ? (
              <p className="mt-1 text-sm text-amber-950">
                <span className="font-medium">Why review: </span>
                {result.ambiguity_reason}
              </p>
            ) : null}
          </div>

          <Panel title="Counter actions">
            {feedbackDone ? (
              <div className="space-y-1 text-sm">
                <div className="font-semibold text-slate-900">Final result recorded</div>
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
              <div className="space-y-2">
                <p className="text-sm text-slate-600">
                  The system will not auto-assign a part. Enter the final SKU when verified.
                </p>
                {!correctOpen ? (
                  <button
                    type="button"
                    disabled={feedbackBusy || !result.request_id}
                    className="rounded-md bg-slate-900 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
                    onClick={() => setCorrectOpen(true)}
                  >
                    Resolve request
                  </button>
                ) : (
                  <div className="space-y-2">
                    <input
                      value={correctSku}
                      onChange={(e) => setCorrectSku(e.target.value)}
                      placeholder="Final SKU"
                      className="w-full rounded-md border px-3 py-2 font-mono text-sm"
                    />
                    <input
                      value={correctNote}
                      onChange={(e) => setCorrectNote(e.target.value)}
                      placeholder="Optional note"
                      className="w-full rounded-md border px-3 py-2 text-sm"
                    />
                    <div className="flex gap-2">
                      <button
                        type="button"
                        disabled={feedbackBusy || !correctSku.trim()}
                        className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-50"
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
                        className="rounded-md border px-3 py-1.5 text-sm"
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
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={feedbackBusy || !result.request_id}
                    className="rounded-md bg-emerald-700 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
                    onClick={() => void submitFeedback("accept")}
                  >
                    Accept match
                  </button>
                  <button
                    type="button"
                    disabled={feedbackBusy || !result.request_id}
                    className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium disabled:opacity-50"
                    onClick={() => {
                      setCorrectOpen(true);
                      setCorrectSku(result.sku || "");
                    }}
                  >
                    Correct match
                  </button>
                </div>
                {correctOpen ? (
                  <div className="space-y-2 border-t pt-2">
                    <input
                      value={correctSku}
                      onChange={(e) => setCorrectSku(e.target.value)}
                      placeholder="Correct SKU"
                      className="w-full rounded-md border px-3 py-2 font-mono text-sm"
                    />
                    <input
                      value={correctNote}
                      onChange={(e) => setCorrectNote(e.target.value)}
                      placeholder="Optional note"
                      className="w-full rounded-md border px-3 py-2 text-sm"
                    />
                    <div className="flex gap-2">
                      <button
                        type="button"
                        disabled={feedbackBusy || !correctSku.trim()}
                        className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-50"
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
                        className="rounded-md border px-3 py-1.5 text-sm"
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
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="font-mono text-2xl font-semibold tracking-tight">
                    {result.sku}
                  </div>
                  <div className="mt-1 text-sm text-slate-600">
                    {result.human_readable ||
                      [result.transmission_family, result.part_type]
                        .filter(Boolean)
                        .join(" · ")}
                  </div>
                </div>
                <StockBadge qty={result.aggregate_available ?? 0} />
              </div>

              <div className="mt-4 grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
                <div>
                  <div className="text-[11px] uppercase text-slate-500">Family</div>
                  <div className="font-mono">{result.transmission_family || "—"}</div>
                </div>
                <div>
                  <div className="text-[11px] uppercase text-slate-500">Part type</div>
                  <div>{result.part_type || "—"}</div>
                </div>
                <div>
                  <div className="text-[11px] uppercase text-slate-500">Qty available</div>
                  <div className="font-semibold tabular-nums">
                    {result.aggregate_available ?? 0}
                  </div>
                </div>
                <div>
                  <div className="text-[11px] uppercase text-slate-500">Data status</div>
                  <div className="text-xs capitalize">
                    {result.verification_status || "unverified"}
                  </div>
                </div>
              </div>

              {result.inventory && result.inventory.length > 0 ? (
                <div className="mt-4">
                  <div className="mb-2 text-[11px] font-medium uppercase text-slate-500">
                    Locations
                  </div>
                  <div className="space-y-1">
                    {result.inventory.map((inv, idx) => {
                      const loc = formatTransmissionLocationLine(inv);
                      return (
                        <div
                          key={idx}
                          className="flex items-center justify-between rounded border border-slate-100 bg-slate-50 px-3 py-2 text-sm"
                        >
                          <div>
                            <div className="font-medium">{loc.title}</div>
                            <div className="font-mono text-[11px] text-slate-500">
                              {loc.subtitle}
                            </div>
                          </div>
                          <div className="text-right">
                            <div className="font-semibold tabular-nums">{inv.qty}</div>
                            <div className="text-[10px] capitalize text-slate-500">
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
                <div className="mt-4">
                  <div className="mb-2 text-[11px] font-medium uppercase text-slate-500">
                    Identifiers
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {result.identifiers.map((id, idx) => (
                      <span
                        key={idx}
                        className="rounded border bg-white px-2 py-0.5 font-mono text-xs"
                      >
                        {id.identifier_type}: {id.identifier_value}
                      </span>
                    ))}
                  </div>
                </div>
              ) : null}

              {result.interchanges && result.interchanges.length > 0 ? (
                <div className="mt-4">
                  <div className="mb-2 text-[11px] font-medium uppercase text-slate-500">
                    Interchange
                  </div>
                  <div className="space-y-1 font-mono text-xs text-slate-600">
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
                className="mt-4 text-xs font-medium text-slate-500 hover:underline"
                onClick={() => setDetailsOpen((v) => !v)}
              >
                {detailsOpen ? "Hide technical detail" : "Show technical detail"}
              </button>
              {detailsOpen ? (
                <pre className="mt-2 overflow-x-auto rounded bg-slate-950 p-3 text-[10px] text-slate-200">
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
              <p className="text-sm text-slate-700">
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
          title="Ready for counter search"
          body="Enter a request above. Matches show stock and locations; ambiguous requests go to Needs Review."
        />
      ) : null}
    </>
  );

  if (jp) {
    return (
      <JpPage
        title="Parts Search"
        description="Look up transmission hard parts by natural language, SKU, OEM, or casting number."
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
