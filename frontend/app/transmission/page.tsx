"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { transmissionInquiry, TransmissionInquiryResponse } from "@/lib/dms-api";
import {
  formatTransmissionLocationLine,
  isTransmissionDemo,
} from "@/lib/demo-vertical";

const QUICK_QUERIES = [
  "Do you have a pump for a 2011 Tahoe 6L80?",
  "Do you have 24264418?",
  "Do you have 6L80-PUMP-01?",
  "Do you have a 4L60E pump?",
  "Do you have a 6R80 pump?",
  "Do you have a 4L60E valve body?",
  "Do you have an 8HP70 valve body?",
];

export default function TransmissionInquiryPage() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<TransmissionInquiryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recentSearches, setRecentSearches] = useState<string[]>([]);

  const runInquiry = async (q: string) => {
    if (!q.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await transmissionInquiry(q.trim());
      setResult(res);

      setRecentSearches(prev => {
        const next = [q.trim(), ...prev.filter(x => x !== q.trim())];
        return next.slice(0, 5);
      });
    } catch (e: any) {
      setError(e?.message || "API request failed");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    runInquiry(query);
  };

  const handleQuickQuery = (q: string) => {
    setQuery(q);
    runInquiry(q);
  };

  const renderResult = () => {
    if (!result) return null;

    const {
      status,
      sku,
      human_readable,
      inventory_available,
      aggregate_available,
      inventory,
      identifiers,
      interchanges,
      transmission_family,
      part_type,
      verification_status,
      fitment_status,
      outcome,
      confidence,
      recommended_action,
      ambiguity_reason,
    } = result;

    const unitOutcome =
      outcome ||
      (status === "resolved" ? "RESOLVED" : "NEEDS_HUMAN");
    const needsHuman = unitOutcome === "NEEDS_HUMAN";

    const decisionBanner = (
      <div
        className={
          needsHuman
            ? "mb-4 rounded-lg border border-amber-400 bg-amber-50 px-4 py-3"
            : "mb-4 rounded-lg border border-emerald-400 bg-emerald-50 px-4 py-3"
        }
      >
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            {needsHuman ? (
              <Badge className="bg-amber-700 text-sm px-3 py-1">NEEDS HUMAN REVIEW</Badge>
            ) : (
              <Badge className="bg-emerald-700 text-sm px-3 py-1">RESOLVED</Badge>
            )}
            {typeof confidence === "number" ? (
              <span className="font-mono text-xs text-muted-foreground">
                confidence {confidence.toFixed(2)}
              </span>
            ) : null}
          </div>
        </div>
        {recommended_action ? (
          <p className="mt-2 text-sm text-slate-800">
            <strong>Next action:</strong> {recommended_action}
          </p>
        ) : null}
        {ambiguity_reason ? (
          <p className="mt-1 text-sm text-amber-900">
            <strong>Why:</strong> {ambiguity_reason}
          </p>
        ) : null}
      </div>
    );

    if (status === "ambiguous" || (needsHuman && status === "ambiguous")) {
      return (
        <div>
          {decisionBanner}
          <Card className="border-amber-200 bg-amber-50">
            <CardHeader>
              <CardTitle className="text-amber-900">More information needed</CardTitle>
              <CardDescription>
                {ambiguity_reason ||
                  "The inquiry matches multiple parts. Provide additional identifying information (SKU, casting number, or OEM number)."}
              </CardDescription>
            </CardHeader>
          </Card>
        </div>
      );
    }

    if (status === "no_match" || status === "insufficient") {
      return (
        <div>
          {decisionBanner}
          <Card className="border-slate-200">
            <CardHeader>
              <CardTitle>Part not identified</CardTitle>
              <CardDescription>{human_readable}</CardDescription>
            </CardHeader>
          </Card>
        </div>
      );
    }

    // resolved (with or without stock) — still show decision banner
    const isZeroStock = aggregate_available === 0;

    return (
      <div className="space-y-6">
        {decisionBanner}
        <Card>
          <CardHeader>
            <div>
              <div className="flex items-baseline justify-between">
                <CardTitle className="text-3xl font-mono tracking-tight">{sku}</CardTitle>
                <div>
                  {isZeroStock ? (
                    <Badge variant="destructive" className="text-sm px-3 py-1">OUT OF STOCK</Badge>
                  ) : aggregate_available === 1 ? (
                    <Badge className="bg-amber-600 text-sm px-3 py-1">LOW STOCK — 1 AVAILABLE</Badge>
                  ) : (
                    <Badge className="bg-emerald-600 text-sm px-3 py-1">IN STOCK — {aggregate_available} AVAILABLE</Badge>
                  )}
                </div>
              </div>
              <div className="mt-1 text-lg text-muted-foreground">{human_readable}</div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4 text-sm md:grid-cols-4">
              <div>
                <div className="font-medium text-muted-foreground">Transmission</div>
                <div className="font-mono">{transmission_family || "—"}</div>
              </div>
              <div>
                <div className="font-medium text-muted-foreground">Part Type</div>
                <div>{part_type || "—"}</div>
              </div>
              <div>
                <div className="font-medium text-muted-foreground">Aggregate Qty</div>
                <div className="font-mono text-lg font-semibold">{aggregate_available}</div>
              </div>
              <div>
                <div className="font-medium text-muted-foreground">Verification</div>
                <Badge variant="outline">{verification_status || "unverified"}</Badge>
              </div>
              <div>
                <div className="font-medium text-muted-foreground">Fitment</div>
                <div className="font-mono text-sm">{fitment_status || "—"}</div>
              </div>
            </div>

            {inventory && inventory.length > 0 && (
              <div>
                <div className="mb-2 font-medium text-muted-foreground">Inventory Locations</div>
                <div className="space-y-1 text-sm">
                  {inventory.map((inv, idx) => {
                    const loc = isTransmissionDemo()
                      ? formatTransmissionLocationLine(inv)
                      : {
                          title: inv.location_name || inv.location || "Location",
                          subtitle: inv.bin
                            ? `Bin ${inv.bin}`
                            : inv.location || "",
                        };
                    return (
                    <div key={idx} className="flex justify-between items-center rounded border bg-muted/40 px-3 py-2 text-sm">
                      <div>
                        <div className="font-medium">{loc.title}</div>
                        <div className="font-mono text-xs text-muted-foreground">
                          {loc.subtitle || (inv.bin ? `Bin ${inv.bin}` : "")}
                        </div>
                      </div>
                      <div className="text-right font-mono">
                        <div className={inv.qty === 0 ? "text-red-600 font-semibold" : "font-semibold"}>{inv.qty}</div>
                        <div className="text-[10px] text-muted-foreground">{inv.condition}</div>
                      </div>
                    </div>
                    );
                  })}
                </div>
              </div>
            )}

            {identifiers && identifiers.length > 0 && (
              <div>
                <div className="mb-2 font-medium text-muted-foreground">Identifiers</div>
                <div className="flex flex-wrap gap-2">
                  {identifiers.map((id, idx) => (
                    <Badge key={idx} variant="secondary" className="font-mono">{id.identifier_type}: {id.identifier_value}</Badge>
                  ))}
                </div>
              </div>
            )}

            {interchanges && interchanges.length > 0 && (
              <div>
                <div className="mb-2 font-medium text-muted-foreground">Interchanges (directional, unverified)</div>
                <div className="space-y-1 text-sm text-muted-foreground font-mono">
                  {interchanges.map((ic, idx) => (
                    <div key={idx}>
                      {ic.source_sku} → {ic.target_sku}<br />
                      {ic.relationship_type} · {ic.verification_status}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    );
  };

  return (
    <div className="container mx-auto max-w-5xl p-6">
      <div className="mb-6 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
        <strong>DEMO DATA — UNVERIFIED</strong> — This page demonstrates the transmission
        hard-parts inquiry workflow for JP Transmission evaluation. All fitment, interchange,
        and compatibility data is synthetic demo data and not an authoritative catalog.
      </div>

      <div className="mb-8 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Transmission Hard Parts</h1>
          <p className="mt-2 text-muted-foreground">
            {isTransmissionDemo()
              ? "Counter inventory intelligence · Safe read-only lookup"
              : "Internal counter intelligence tool • Read-only DMS inquiry"}
          </p>
        </div>
        <Button asChild variant="outline">
          <Link href="/transmission/import">Pilot Data Import</Link>
        </Button>
      </div>

      <Card className="mb-8">
        <CardHeader>
          <CardTitle>Inquiry</CardTitle>
          <CardDescription>Enter natural language, SKU, OEM number, or casting number</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="flex gap-3">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter SKU, OEM number, casting, or natural language query..."
              className="flex-1 rounded-md border-2 border-slate-300 bg-white px-4 py-3 text-base font-mono placeholder:text-slate-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={loading}
            />
            <Button type="submit" disabled={loading || !query.trim()}>
              {loading ? "Searching..." : "Search"}
            </Button>
          </form>

          <div className="mt-4 flex flex-wrap gap-2">
            {QUICK_QUERIES.map((q, idx) => (
              <Button
                key={idx}
                variant="outline"
                size="sm"
                className="font-mono text-xs"
                onClick={() => handleQuickQuery(q)}
                disabled={loading}
              >
                {q.length > 45 ? q.substring(0, 42) + "..." : q}
              </Button>
            ))}
          </div>

          {recentSearches.length > 0 && (
            <div className="mt-3 text-xs text-muted-foreground">
              Recent: {recentSearches.slice(0, 3).join("  ·  ")}
            </div>
          )}
        </CardContent>
      </Card>

      {error && (
        <Card className="mb-6 border-red-200 bg-red-50">
          <CardHeader>
            <CardTitle className="text-red-900">Request failed</CardTitle>
            <CardDescription className="text-red-700">{error}</CardDescription>
          </CardHeader>
        </Card>
      )}

      {loading && (
        <div className="py-12 text-center text-muted-foreground">Querying DMS transmission service...</div>
      )}

      {!loading && renderResult()}
    </div>
  );
}
