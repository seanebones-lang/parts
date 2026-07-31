"use client";

import { useCallback, useMemo, useState } from "react";
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
  Search,
  Package,
  Filter,
  Download,
  Upload,
  Bot,
  Loader2,
  AlertCircle,
} from "lucide-react";
import {
  type PartResult,
  type PartsQueryResponse,
  getHealth,
  mockQueryParts,
  queryPartsWithFallback,
} from "@/lib/api";

function stockBadgeVariant(
  availability?: string,
  quantity?: number
): "default" | "secondary" | "destructive" | "outline" {
  const a = (availability || "").toLowerCase();
  if (a.includes("out") || quantity === 0) return "destructive";
  if (a.includes("low") || (typeof quantity === "number" && quantity > 0 && quantity < 5))
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
  const bits = [
    p.manufacturer || p.brand,
    p.part_number ? `Part #${p.part_number}` : null,
    p.compatible ||
      ([p.make, p.model].filter(Boolean).join(" ") || null) ||
      p.description,
  ].filter(Boolean);
  return bits.join(" • ");
}

export default function PartsPage() {
  const [query, setQuery] = useState("brake pads for 2019 Honda Civic");
  const [loading, setLoading] = useState(false);
  const [healthOk, setHealthOk] = useState<boolean | null>(null);
  const [response, setResponse] = useState<PartsQueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const results = useMemo(
    () => response?.results ?? mockQueryParts("").results,
    [response]
  );

  const runSearch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      try {
        const h = await getHealth();
        const st = typeof h?.status === "string" ? h.status.toLowerCase() : "";
        setHealthOk(
          st === "healthy" || st === "ok" || st === "operational"
        );
      } catch {
        setHealthOk(false);
      }

      const res = await queryPartsWithFallback(query);
      setResponse(res);
      if (res.source === "mock") {
        setError(
          "Live API unreachable — showing mock catalog fallback. Start backend or parrts API on :8000."
        );
      }
    } catch (e) {
      const mock = mockQueryParts(query);
      setResponse(mock);
      setError(
        e instanceof Error
          ? `${e.message} — using mock data`
          : "Search failed — using mock data"
      );
    } finally {
      setLoading(false);
    }
  }, [query]);

  return (
    <div className="container mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-foreground mb-2">Parts Catalog</h1>
        <p className="text-xl text-muted-foreground">
          AI-powered semantic search and parts management
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
          {healthOk === true && (
            <Badge variant="default" className="bg-green-600">
              API healthy
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
                  ? "border-green-600 text-green-700 bg-green-50"
                  : response.trafficLight.color === "yellow"
                    ? "border-amber-500 text-amber-800 bg-amber-50"
                    : "border-red-600 text-red-700 bg-red-50"
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

      <Card className="mb-8">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="h-5 w-5" />
            AI Parts Search
          </CardTitle>
          <CardDescription>
            Calls{" "}
            <code className="text-xs">/api/v1/parts/search</code> or{" "}
            <code className="text-xs">/query</code> when available; falls back to
            mock data offline.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex gap-4">
              <div className="flex-1">
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") void runSearch();
                  }}
                  placeholder='Search for parts using natural language... e.g. "brake pads for 2020 Honda Civic"'
                  className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  disabled={loading}
                />
              </div>
              <Button className="px-8" onClick={() => void runSearch()} disabled={loading}>
                {loading ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Bot className="h-4 w-4 mr-2" />
                )}
                AI Search
              </Button>
            </div>

            {error && (
              <div className="flex items-start gap-2 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <select className="px-4 py-2 border rounded-lg" defaultValue="">
                <option value="">All Makes</option>
                <option value="honda">Honda</option>
                <option value="toyota">Toyota</option>
                <option value="ford">Ford</option>
              </select>

              <select className="px-4 py-2 border rounded-lg" defaultValue="">
                <option value="">All Models</option>
                <option value="civic">Civic</option>
                <option value="accord">Accord</option>
                <option value="cr-v">CR-V</option>
              </select>

              <select className="px-4 py-2 border rounded-lg" defaultValue="">
                <option value="">All Years</option>
                <option value="2023">2023</option>
                <option value="2022">2022</option>
                <option value="2021">2021</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mb-8">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Filter className="h-5 w-5" />
              Filters
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium">Category</label>
                <select className="w-full mt-1 px-3 py-2 border rounded-md" defaultValue="">
                  <option value="">All Categories</option>
                  <option value="brakes">Brakes</option>
                  <option value="engine">Engine</option>
                  <option value="tires">Tires</option>
                </select>
              </div>

              <div>
                <label className="text-sm font-medium">Manufacturer</label>
                <select className="w-full mt-1 px-3 py-2 border rounded-md" defaultValue="">
                  <option value="">All Manufacturers</option>
                  <option value="brembo">Brembo</option>
                  <option value="fram">Fram</option>
                  <option value="ngk">NGK</option>
                </select>
              </div>

              <div>
                <label className="text-sm font-medium">Price Range</label>
                <div className="mt-1 space-y-2">
                  <input
                    type="number"
                    placeholder="Min"
                    className="w-full px-3 py-2 border rounded-md"
                  />
                  <input
                    type="number"
                    placeholder="Max"
                    className="w-full px-3 py-2 border rounded-md"
                  />
                </div>
              </div>

              <div>
                <label className="text-sm font-medium">Availability</label>
                <div className="mt-1 space-y-1">
                  <label className="flex items-center">
                    <input type="checkbox" className="mr-2" />
                    In Stock Only
                  </label>
                  <label className="flex items-center">
                    <input type="checkbox" className="mr-2" />
                    Cross-Location Available
                  </label>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="lg:col-span-3">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Search Results</CardTitle>
                  <CardDescription>
                    {response
                      ? `Found ${results.length} part${results.length === 1 ? "" : "s"}${
                          response.query ? ` for “${response.query}”` : ""
                        }`
                      : "Run a search or browse mock catalog"}
                  </CardDescription>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" type="button" disabled>
                    <Download className="h-4 w-4 mr-2" />
                    Export
                  </Button>
                  <Button variant="outline" size="sm" type="button" disabled>
                    <Upload className="h-4 w-4 mr-2" />
                    Import
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {results.map((p, idx) => {
                  const qty =
                    typeof p.quantity === "number"
                      ? p.quantity
                      : typeof p.stock === "number"
                        ? p.stock
                        : undefined;
                  const availability =
                    p.availability ||
                    (qty === 0
                      ? "Out of Stock"
                      : qty !== undefined && qty < 5
                        ? "Low Stock"
                        : "In Stock");
                  return (
                    <div
                      key={String(p.id ?? p.part_number ?? idx)}
                      className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50"
                    >
                      <div className="flex items-center space-x-4">
                        <Package className="h-8 w-8 text-muted-foreground" />
                        <div>
                          <p className="font-medium">{partTitle(p)}</p>
                          <p className="text-sm text-muted-foreground">
                            {partSubtitle(p)}
                          </p>
                          <div className="flex items-center gap-2 mt-1 flex-wrap">
                            <Badge variant={stockBadgeVariant(availability, qty)}>
                              {availability}
                            </Badge>
                            {p.category ? (
                              <Badge variant="outline">{String(p.category)}</Badge>
                            ) : null}
                            {p.make ? (
                              <Badge variant="outline">{String(p.make)}</Badge>
                            ) : null}
                            {p.color ? (
                              <Badge variant="outline">{String(p.color)}</Badge>
                            ) : null}
                            {typeof p.score === "number" ? (
                              <Badge variant="outline">
                                score {(p.score as number).toFixed(3)}
                              </Badge>
                            ) : null}
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="font-medium">{formatPrice(p.price)}</p>
                        <p className="text-sm text-muted-foreground">
                          {qty === undefined
                            ? "qty n/a"
                            : qty === 0
                              ? "Available at other locations"
                              : `${qty} available`}
                        </p>
                        <Button
                          size="sm"
                          className="mt-2"
                          variant={qty === 0 ? "outline" : "default"}
                          type="button"
                        >
                          {qty === 0 ? "Transfer Request" : "Add to Cart"}
                        </Button>
                      </div>
                    </div>
                  );
                })}

                {results.length === 0 && !loading && (
                  <p className="text-sm text-muted-foreground py-8 text-center">
                    No parts matched. Try another query.
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bot className="h-5 w-5" />
            AI Insights & Recommendations
          </CardTitle>
          <CardDescription>
            Demo insights — replace with analytics once retrieval eval is wired.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="p-4 bg-blue-50 rounded-lg">
              <h4 className="font-medium text-blue-900 mb-2">Popular Searches</h4>
              <ul className="text-sm text-blue-700 space-y-1">
                <li>• &quot;brake pads honda civic&quot;</li>
                <li>• &quot;oil filter 2020&quot;</li>
                <li>• &quot;spark plugs toyota&quot;</li>
              </ul>
            </div>

            <div className="p-4 bg-green-50 rounded-lg">
              <h4 className="font-medium text-green-900 mb-2">Compatibility Insights</h4>
              <ul className="text-sm text-green-700 space-y-1">
                <li>• Prefer OEM + quality aftermarket dual list</li>
                <li>• Brake pads often span multi-year fitment</li>
                <li>• Filters often engine-family compatible</li>
              </ul>
            </div>

            <div className="p-4 bg-yellow-50 rounded-lg">
              <h4 className="font-medium text-yellow-900 mb-2">Inventory Optimization</h4>
              <ul className="text-sm text-yellow-700 space-y-1">
                <li>• Watch low-stock spark plugs</li>
                <li>• High-turn oil filters need reorder points</li>
                <li>• Cross-location transfer before special order</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
