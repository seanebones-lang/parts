/**
 * Typed fetch helpers for backend + parrts thin API.
 * Base URL from NEXT_PUBLIC_API_URL (default http://127.0.0.1:8000).
 */

function resolveApiBaseUrl(): string {
  // Next.js inlines NEXT_PUBLIC_* at build time.
  const g = globalThis as {
    process?: { env?: Record<string, string | undefined> };
  };
  const envUrl = g.process?.env?.NEXT_PUBLIC_API_URL;
  if (envUrl && envUrl.trim()) return envUrl.replace(/\/+$/, "");
  return "http://127.0.0.1:8000";
}

export const API_BASE_URL = resolveApiBaseUrl();

export type HealthStatus = {
  status: string;
  database?: string;
  redis?: string;
  ai_services?: string;
  [key: string]: unknown;
};

export type PartResult = {
  id?: string | number;
  name?: string;
  title?: string;
  part_number?: string;
  sku?: string;
  manufacturer?: string;
  brand?: string;
  category?: string;
  price?: number | string;
  quantity?: number;
  stock?: number;
  availability?: string;
  status?: string;
  description?: string;
  compatible?: string;
  make?: string;
  model?: string;
  score?: number;
  color?: string;
  [key: string]: unknown;
};

export type PartsQueryResponse = {
  results: PartResult[];
  query: string;
  source: "api" | "parrts" | "mock";
  count?: number;
  raw?: unknown;
  trafficLight?: {
    color?: string;
    confidence?: number;
    reason?: string;
  } | null;
};

export class ApiError extends Error {
  status: number;
  body?: unknown;

  constructor(message: string, status: number, body?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

function joinUrl(base: string, path: string): string {
  const b = base.replace(/\/+$/, "");
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${b}${p}`;
}

/** Low-level JSON GET/POST helper. */
export async function getJson<T = unknown>(
  path: string,
  init?: RequestInit & { baseUrl?: string }
): Promise<T> {
  const base = init?.baseUrl ?? API_BASE_URL;
  const { baseUrl: _omit, ...rest } = init ?? {};
  const url = path.startsWith("http") ? path : joinUrl(base, path);

  const res = await fetch(url, {
    ...rest,
    headers: {
      Accept: "application/json",
      ...(rest.body ? { "Content-Type": "application/json" } : {}),
      ...rest.headers,
    },
  });

  let body: unknown = null;
  const text = await res.text();
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = text;
    }
  }

  if (!res.ok) {
    throw new ApiError(
      `Request failed ${res.status} ${res.statusText} for ${url}`,
      res.status,
      body
    );
  }

  return body as T;
}

/** GET /health */
export async function getHealth(
  baseUrl: string = API_BASE_URL
): Promise<HealthStatus> {
  return getJson<HealthStatus>("/health", { baseUrl });
}

function normalizePart(item: unknown): PartResult {
  if (!item || typeof item !== "object") {
    return { name: String(item ?? "Unknown part") };
  }
  const o = item as Record<string, unknown>;
  return {
    ...o,
    id: (o.id ?? o.part_id ?? o.sku) as string | number | undefined,
    name: (o.name ?? o.title ?? o.part_name ?? o.description) as
      | string
      | undefined,
    part_number: (o.part_number ?? o.sku ?? o.partNumber) as string | undefined,
    manufacturer: (o.manufacturer ?? o.brand ?? o.mfr) as string | undefined,
    price: o.price as number | string | undefined,
    quantity: (o.quantity ?? o.stock ?? o.qty) as number | undefined,
    stock: (o.stock ?? o.quantity ?? o.qty) as number | undefined,
    location: (o.location ?? o.store ?? o.site) as string | undefined,
    category: o.category as string | undefined,
    availability: (o.availability ?? o.status) as string | undefined,
    score: (o.score ?? o.similarity ?? o.rrf_score) as number | undefined,
    color: (o.color ?? o.traffic_light) as string | undefined,
  };
}

function extractResults(payload: unknown): PartResult[] {
  if (!payload) return [];
  if (Array.isArray(payload)) return payload.map(normalizePart);

  if (typeof payload === "object") {
    const o = payload as Record<string, unknown>;
    const candidates = [
      o.results,
      o.parts,
      o.search_results,
      o.hits,
      o.data,
      o.items,
    ];
    for (const c of candidates) {
      if (Array.isArray(c)) return c.map(normalizePart);
      if (c && typeof c === "object") {
        const nested = c as Record<string, unknown>;
        for (const key of ["results", "parts", "items", "hits"]) {
          if (Array.isArray(nested[key])) {
            return (nested[key] as unknown[]).map(normalizePart);
          }
        }
      }
    }
  }
  return [];
}

/**
 * Query parts via enterprise path first, then parrts thin API fallbacks.
 * Tries:
 *  1. GET  /api/v1/parts/search/{query}
 *  2. POST /api/v1/parts/search  { text | query }
 *  3. POST /query                { text | query }
 *  4. POST /query_parts          { text }
 */
export async function queryParts(
  text: string,
  baseUrl: string = API_BASE_URL
): Promise<PartsQueryResponse> {
  const q = text.trim();
  if (!q) {
    return { results: [], query: text, source: "api", count: 0 };
  }

  const encoded = encodeURIComponent(q);
  const attempts: Array<{
    source: "api" | "parrts";
    run: () => Promise<unknown>;
  }> = [
    // Prefer offline-capable hybrid core first (dealership demo path).
    {
      source: "parrts",
      run: () =>
        getJson(`/query`, {
          baseUrl,
          method: "POST",
          body: JSON.stringify({ text: q, query: q }),
        }),
    },
    {
      source: "api",
      run: () =>
        getJson(`/api/v1/parts/search/${encoded}`, {
          baseUrl,
          method: "GET",
        }),
    },
    {
      source: "api",
      run: () =>
        getJson(`/api/v1/parts/search`, {
          baseUrl,
          method: "POST",
          body: JSON.stringify({ text: q, query: q }),
        }),
    },
    {
      source: "parrts",
      run: () =>
        getJson(`/query_parts`, {
          baseUrl,
          method: "POST",
          body: JSON.stringify({ text: q }),
        }),
    },
  ];

  let lastError: unknown;
  for (const attempt of attempts) {
    try {
      const raw = await attempt.run();
      const results = extractResults(raw);
      let trafficLight: PartsQueryResponse["trafficLight"] = null;
      if (raw && typeof raw === "object") {
        const tl = (raw as Record<string, unknown>).traffic_light;
        if (tl && typeof tl === "object") {
          const t = tl as Record<string, unknown>;
          trafficLight = {
            color: typeof t.color === "string" ? t.color : undefined,
            confidence:
              typeof t.confidence === "number" ? t.confidence : undefined,
            reason: typeof t.reason === "string" ? t.reason : undefined,
          };
        }
      }
      return {
        results,
        query: q,
        source: attempt.source,
        count: results.length,
        raw,
        trafficLight,
      };
    } catch (err) {
      lastError = err;
    }
  }

  throw lastError instanceof Error
    ? lastError
    : new Error("All parts query endpoints failed");
}

/** Static mock catalog used when live API is unavailable. */
export const MOCK_PARTS: PartResult[] = [
  {
    id: "mock-1",
    name: "Brake Pad Set - Front",
    manufacturer: "Brembo",
    part_number: "BRK123",
    category: "Brakes",
    make: "Honda",
    compatible: "2019-2023 Honda Civic",
    price: 89.99,
    quantity: 25,
    availability: "In Stock",
  },
  {
    id: "mock-2",
    name: "Oil Filter",
    manufacturer: "Fram",
    part_number: "FLT456",
    category: "Engine",
    make: "Honda",
    compatible: "2019-2023 Honda Civic",
    price: 12.99,
    quantity: 50,
    availability: "In Stock",
  },
  {
    id: "mock-3",
    name: "Spark Plug Set",
    manufacturer: "NGK",
    part_number: "SPK789",
    category: "Engine",
    make: "Honda",
    compatible: "2019-2023 Honda Civic",
    price: 24.99,
    quantity: 3,
    availability: "Low Stock",
  },
  {
    id: "mock-4",
    name: "Tire 225/60R16",
    manufacturer: "Michelin",
    part_number: "TIR012",
    category: "Tires",
    make: "Honda",
    compatible: "2019-2023 Honda Civic",
    price: 149.99,
    quantity: 0,
    availability: "Out of Stock",
  },
];

export function mockQueryParts(text: string): PartsQueryResponse {
  const q = text.trim().toLowerCase();
  const results = !q
    ? MOCK_PARTS
    : MOCK_PARTS.filter((p) => {
        const hay = [
          p.name,
          p.manufacturer,
          p.part_number,
          p.category,
          p.make,
          p.compatible,
          p.description,
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        return q.split(/\s+/).some((tok) => hay.includes(tok));
      });

  return {
    results: results.length ? results : MOCK_PARTS,
    query: text,
    source: "mock",
    count: (results.length ? results : MOCK_PARTS).length,
  };
}

/** Live query with automatic mock fallback. */
export async function queryPartsWithFallback(
  text: string,
  baseUrl: string = API_BASE_URL
): Promise<PartsQueryResponse> {
  try {
    const live = await queryParts(text, baseUrl);
    if (live.results.length > 0) return live;
    // Empty live response still counts as success if API answered
    return live;
  } catch {
    return mockQueryParts(text);
  }
}
