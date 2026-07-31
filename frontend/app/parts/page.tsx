"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Search, Package, Bot, Loader2, AlertCircle } from "lucide-react";
import {
  type PartResult,
  type PartsQueryResponse,
  getHealth,
  mockQueryParts,
  queryPartsWithFallback,
} from "@/lib/api";

const DEMO_QUERIES = [
  "brake pads for 2019 Honda Civic",
  "oil filter Toyota Camry 2020",
  "spark plugs NGK Civic",
  "front rotors 2018 Ford F-150",
  "battery group 51R Honda",
  "wiper blades 22 inch",
];

function stockBadgeVariant(
  availability?: string,
  quantity?: number
): "default" | "secondary" | "destructive" | "outline" {
  const a = (availability || "").toLowerCase();
  if (a.includes("out") || quantity === 0) return "destructive";
  if (
    a.includes("low") ||
    (typeof quantity === "number" && quantity > 0 && quantity < 5)
  )
    return "secondary";
  if (a.includes("stock") || (typeof quantity === "number" && quantity > 0))
    return "default";
  return "outline";
}

function formatPrice(price?: number | string): string {
  if (price === undefined || price === null || price === "") return "—";
  const n = typeof price === "number" ? price : Number(price);
  if (Number.isFinite(n)) return `$${n.toFixed(2)}`;
  return String(price);
}

function partTitle(p: PartResult): string {
  return p.name || p.title || p.part_number || "Unknown part";
}

function partSubtitle(p: PartResult): string {
  const loc = (p as { location?: string }).location;
  const bits = [
    loc ? `📍 ${loc}` : null,
    p.manufacturer || p.brand,
    p.part_number ? `SKU ${p.part_number}` : null,
    p.compatible ||
      ([p.make, p.model].filter(Boolean).join(" ") || null) ||
      p.description,
  ].filter(Boolean);
  return bits.join(" · ");
}

function initialQueryFromUrl(): string {
  if (typeof window === "undefined") return DEMO_QUERIES[0];
  try {
    const q = new URLSearchParams(window.location.search).get("q");
    if (q && q.trim()) return q.trim();
  } catch {
    /* ignore */
  }
  return DEMO_QUERIES[0];
}

export default function PartsPage() {
  const [query, setQuery] = useState(DEMO_QUERIES[0]);
  const [loading, setLoading] = useState(false);
  const [healthOk, setHealthOk] = useState<boolean | null>(null);
  const [response, setResponse] = useState<PartsQueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [booted, setBooted] = useState(false);

  const results = useMemo(() => response?.results ?? [], [response]);

  const runSearch = useCallback(
    async (override?: string) => {
      const q = (override ?? query).trim();
      if (!q) return;
      setQuery(q);
      setLoading(true);
      setError(null);
      try {
        try {
          const h = await getHealth();
          const st = typeof h?.status === "string" ? h.status.toLowerCase() : "";
          setHealthOk(
            st === "healthy" ||
              st === "ok" ||
              st === "operational" ||
              st === "degraded"
          );
        } catch {
          setHealthOk(false);
        }

        const res = await queryPartsWithFallback(q);
        setResponse(res);
        if (res.source === "mock") {
          setError(
            "Live API unreachable — showing mock catalog fallback. Run ./scripts/demo_up.sh"
          );
        }
      } catch (e) {
        const mock = mockQueryParts(q);
        setResponse(mock);
        setError(
          e instanceof Error
            ? `${e.message} — using mock data`
            : "Search failed — using mock data"
        );
      } finally {
        setLoading(false);
      }
    },
    [query]
  );

  useEffect(() => {
    if (booted) return;
    setBooted(true);
    const q = initialQueryFromUrl();
    setQuery(q);
    void runSearch(q);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [booted]);

  return (
    <div className="container mx-auto p-6">
      <div className="mb-6 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-950">
        <strong>Live pilot path.</strong> Type a counter question or pick a
        scenario. Results show multi-location SKUs with traffic-light confidence.
      </div>

      <div className="mb-8">
        <h1 className="mb-2 text-4xl font-bold text-foreground">Parts Search</h1>
        <p className="text-xl text-muted-foreground">
          Natural language · multi-location · green / yellow / red confidence
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
          {healthOk === true && (
            <Badge variant="default" className="bg-green-600">
              API connected
            </Badge>
          )}
          {healthOk === false && (
            <Badge variant="secondary">API offline / mock mode</Badge>
          )}
          {response?.source && (
            <Badge variant="outline">Source: {response.source}</Badge>
          )}
          {response?.trafficLight?.color && (
            <Badge
              variant="outline"
              className={
                response.trafficLight.color === "green"
                  ? "border-green-600 bg-green-50 text-green-700"
                  : response.trafficLight.color === "yellow"
                    ? "border-amber-500 bg-amber-50 text-amber-800"
                    : "border-red-600 bg-red-50 text-red-700"
              }
            >
              Traffic: {response.trafficLight.color}
              {typeof response.trafficLight.confidence === "number"
                ? ` (${(response.trafficLight.confidence * 100).toFixed(0)}%)`
                : ""}
            </Badge>
          )}
        </div>
      </div>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="h-5 w-5" />
            Counter lookup
          </CardTitle>
          <CardDescription>
            Prefer live <code className="text-xs">POST /query</code> via API; mock
            fallback if the backend is down.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="mb-3 flex flex-wrap gap-2">
            {DEMO_QUERIES.map((dq) => (
              <button
                key={dq}
                type="button"
                onClick={() => void runSearch(dq)}
                className="rounded-full border bg-muted/50 px-3 py-1 text-xs hover:bg-muted"
                disabled={loading}
              >
                {dq}
              </button>
            ))}
          </div>
          <div className="flex gap-4">
            <div className="flex-1">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") void runSearch();
                }}
                placeholder='e.g. "brake pads for 2019 Honda Civic"'
                className="w-full rounded-lg border px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
                disabled={loading}
              />
            </div>
            <Button
              className="px-8"
              onClick={() => void runSearch()}
              disabled={loading}
            >
              {loading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Bot className="mr-2 h-4 w-4" />
              )}
              Search
            </Button>
          </div>
          {error && (
            <div className="mt-3 flex items-start gap-2 text-sm text-amber-800">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold">
          Results {results.length ? `(${results.length})` : ""}
        </h2>
      </div>

      {results.length === 0 && !loading ? (
        <Card>
          <CardContent className="py-10 text-center text-muted-foreground">
            No results yet — run a search or pick a scenario chip.
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {results.map((p, idx) => (
            <Card key={`${p.part_number || (p as { sku?: string }).sku || idx}-${idx}`}>
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between gap-2">
                  <CardTitle className="text-base leading-snug">
                    {partTitle(p)}
                  </CardTitle>
                  <Badge
                    variant={stockBadgeVariant(
                      p.availability,
                      typeof p.quantity === "number"
                        ? p.quantity
                        : typeof (p as { stock?: number }).stock === "number"
                          ? (p as { stock?: number }).stock
                          : undefined
                    )}
                  >
                    qty{" "}
                    {p.quantity ??
                      (p as { stock?: number }).stock ??
                      "—"}
                  </Badge>
                </div>
                <CardDescription className="text-xs">
                  {partSubtitle(p)}
                </CardDescription>
              </CardHeader>
              <CardContent className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-1 text-muted-foreground">
                  <Package className="h-4 w-4" />
                  {p.category || "part"}
                </span>
                <span className="text-lg font-semibold">
                  {formatPrice(p.price)}
                </span>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
