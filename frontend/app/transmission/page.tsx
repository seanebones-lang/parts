"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { transmissionInquiry, TransmissionInquiryResponse } from "@/lib/dms-api";

const QUICK_QUERIES = [
  "Do you have a pump for a 2011 Tahoe 6L80?",
  "Do you have 24264418?",
  "Do you have 6L80-PUMP-01?",
  "Do you have 6L90 valve body?",
  "Do you have 4L60E input drum?",
];

export default function TransmissionInquiryPage() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<TransmissionInquiryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runInquiry = async (q: string) => {
    if (!q.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await transmissionInquiry(q.trim());
      setResult(res);
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

    const { status, sku, human_readable, inventory_available, aggregate_available, inventory, identifiers, interchanges, transmission_family, part_type, verification_status } = result;

    if (status === "ambiguous") {
      return (
        <Card className="border-amber-200 bg-amber-50">
          <CardHeader>
            <CardTitle className="text-amber-900">More information needed</CardTitle>
            <CardDescription>The inquiry matches multiple parts. Provide additional identifying information (SKU, casting number, or OEM number).</CardDescription>
          </CardHeader>
        </Card>
      );
    }

    if (status === "no_match" || status === "insufficient") {
      return (
        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle>Part not identified</CardTitle>
            <CardDescription>{human_readable}</CardDescription>
          </CardHeader>
        </Card>
      );
    }

    // resolved (with or without stock)
    const isZeroStock = aggregate_available === 0;

    return (
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-2xl">{sku}</CardTitle>
                <CardDescription className="mt-1 text-base">{human_readable}</CardDescription>
              </div>
              <div className="text-right">
                {isZeroStock ? (
                  <Badge variant="destructive" className="text-sm">OUT OF STOCK</Badge>
                ) : (
                  <Badge variant="default" className="bg-emerald-600 text-sm">IN STOCK</Badge>
                )}
              </div>
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
            </div>

            {inventory && inventory.length > 0 && (
              <div>
                <div className="mb-2 font-medium text-muted-foreground">Inventory Locations</div>
                <div className="space-y-1 text-sm">
                  {inventory.map((inv, idx) => (
                    <div key={idx} className="flex justify-between rounded border bg-muted/40 px-3 py-1.5 font-mono text-xs">
                      <span>{inv.location_name || inv.location} • {inv.bin}</span>
                      <span className={inv.qty === 0 ? "text-red-600" : ""}>{inv.qty} {inv.condition}</span>
                    </div>
                  ))}
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
                <div className="mb-2 font-medium text-muted-foreground">Interchanges (unverified)</div>
                <div className="space-y-1 text-sm text-muted-foreground">
                  {interchanges.map((ic, idx) => (
                    <div key={idx} className="font-mono">{ic.target_sku} — {ic.relationship_type}</div>
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
        <strong>DEMO DATA — UNVERIFIED</strong> — This page demonstrates the transmission hard-parts inquiry workflow and architecture for JP Transmission evaluation. All fitment, interchange, and compatibility data is synthetic demo data and not an authoritative catalog.
      </div>

      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Transmission Hard Parts</h1>
        <p className="mt-2 text-muted-foreground">Internal counter intelligence tool • Read-only DMS inquiry</p>
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
              placeholder="Do you have a pump for a 2011 Tahoe 6L80?"
              className="flex-1 rounded-md border bg-background px-3 py-2 font-mono text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
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
