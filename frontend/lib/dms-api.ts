/**
 * DMS Core API client — NEXT_PUBLIC_API_URL + /api/v1/dms/*
 * Offline-capable SQLite DMS (see docs/DMS_OEM.md).
 */

import { API_BASE_URL, ApiError, getJson } from "@/lib/api";
import { enqueueOfflineMutation, isBrowserOffline } from "@/lib/offline-queue";

const DMS_PREFIX = "/api/v1/dms";

function dmsPath(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${DMS_PREFIX}${p}`;
}

async function dmsGet<T = unknown>(path: string, init?: RequestInit): Promise<T> {
  return getJson<T>(dmsPath(path), { ...init, baseUrl: API_BASE_URL });
}

async function dmsPost<T = unknown>(
  path: string,
  body?: unknown,
  init?: RequestInit
): Promise<T> {
  return getJson<T>(dmsPath(path), {
    ...init,
    baseUrl: API_BASE_URL,
    method: "POST",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

async function dmsPut<T = unknown>(
  path: string,
  body?: unknown,
  init?: RequestInit
): Promise<T> {
  return getJson<T>(dmsPath(path), {
    ...init,
    baseUrl: API_BASE_URL,
    method: "PUT",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

/** True when fetch failed due to network / API down (not 4xx business errors). */
export function isApiUnreachable(err: unknown): boolean {
  if (err instanceof TypeError) return true;
  if (err instanceof ApiError) return err.status === 0 || err.status >= 500;
  if (err instanceof Error) {
    const m = err.message.toLowerCase();
    return (
      m.includes("failed to fetch") ||
      m.includes("network") ||
      m.includes("econnrefused") ||
      m.includes("load failed")
    );
  }
  return false;
}

export type DmsStatus = {
  ok?: boolean;
  status?: string;
  db_path?: string;
  catalog_count?: number;
  inventory_rows?: number;
  inventory_count?: number;
  customer_count?: number;
  customers?: number;
  order_count?: number;
  orders?: number;
  location_count?: number;
  oem_configured?: boolean;
  oem_feed_url_set?: boolean;
  last_oem_sync?: string | null;
  message?: string;
  [key: string]: unknown;
};

export type DmsInventoryRow = {
  id?: string | number;
  sku?: string;
  part_number?: string;
  name?: string;
  title?: string;
  location_id?: string | number;
  location_code?: string;
  location_name?: string;
  location?: string;
  qty?: number;
  quantity?: number;
  on_hand?: number;
  reserved?: number;
  list_price?: number;
  msrp?: number;
  make?: string;
  model?: string;
  category?: string;
  [key: string]: unknown;
};

export type DmsCustomer = {
  id?: string | number;
  name?: string;
  email?: string;
  phone?: string;
  company?: string;
  notes?: string;
  created_at?: string;
  [key: string]: unknown;
};

export type DmsOrderLine = {
  sku?: string;
  part_number?: string;
  name?: string;
  qty?: number;
  quantity?: number;
  unit_price?: number;
  line_total?: number;
  [key: string]: unknown;
};

export type DmsOrder = {
  id?: string | number;
  order_number?: string;
  customer_id?: string | number;
  customer_name?: string;
  customer_email?: string;
  status?: string;
  payment_status?: string | null;
  ship_status?: string | null;
  tracking_code?: string | null;
  location_id?: string | number;
  location_code?: string;
  total?: number;
  subtotal?: number;
  lines?: DmsOrderLine[];
  items?: DmsOrderLine[];
  created_at?: string;
  notes?: string;
  [key: string]: unknown;
};

export type DmsCatalogPart = {
  sku?: string;
  name?: string;
  description?: string;
  make?: string;
  model?: string;
  list_price?: number;
  [key: string]: unknown;
};

export type CreateCustomerInput = {
  name: string;
  email?: string;
  phone?: string;
  company?: string;
  notes?: string;
};

export type CreateOrderLineInput = {
  sku: string;
  qty: number;
  unit_price?: number;
};

export type CreateOrderInput = {
  customer_id: string | number;
  location_id?: string | number;
  location_code?: string;
  notes?: string;
  lines: CreateOrderLineInput[];
  items?: CreateOrderLineInput[];
};

export type OemSyncInput = {
  source?: "synthetic" | "file" | "http" | string;
  path?: string;
};

function asRecord(v: unknown): Record<string, unknown> | null {
  if (v && typeof v === "object" && !Array.isArray(v)) {
    return v as Record<string, unknown>;
  }
  return null;
}

/** Pull first array found under common keys (or top-level array). */
function extractArray(payload: unknown, keys: string[]): unknown[] {
  if (Array.isArray(payload)) return payload;
  const o = asRecord(payload);
  if (!o) return [];
  for (const k of keys) {
    const v = o[k];
    if (Array.isArray(v)) return v;
  }
  // nested data/result
  for (const nest of ["data", "result", "payload"]) {
    const inner = o[nest];
    if (Array.isArray(inner)) return inner;
    const r = asRecord(inner);
    if (r) {
      for (const k of keys) {
        if (Array.isArray(r[k])) return r[k] as unknown[];
      }
    }
  }
  return [];
}

function num(v: unknown): number | undefined {
  if (typeof v === "number" && Number.isFinite(v)) return v;
  if (typeof v === "string" && v.trim() !== "" && Number.isFinite(Number(v))) {
    return Number(v);
  }
  return undefined;
}

function str(v: unknown): string | undefined {
  if (typeof v === "string") return v;
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  return undefined;
}

export function normalizeInventoryRow(item: unknown): DmsInventoryRow {
  const o = asRecord(item) ?? { name: String(item ?? "") };
  const qty =
    num(o.qty) ?? num(o.quantity) ?? num(o.on_hand) ?? num(o.stock) ?? undefined;
  const loc =
    str(o.location_name) ??
    str(o.location) ??
    str(o.location_code) ??
    (o.location_id != null ? String(o.location_id) : undefined);
  return {
    ...o,
    id: (o.id ?? o.sku ?? o.part_number) as string | number | undefined,
    sku: str(o.sku) ?? str(o.part_number),
    part_number: str(o.part_number) ?? str(o.sku),
    name: str(o.name) ?? str(o.title) ?? str(o.description),
    location_id: o.location_id as string | number | undefined,
    location_code: str(o.location_code),
    location_name: loc,
    location: loc,
    qty,
    quantity: qty,
    on_hand: num(o.on_hand) ?? qty,
    reserved: num(o.reserved),
    list_price: num(o.list_price) ?? num(o.price),
    msrp: num(o.msrp),
    make: str(o.make),
    model: str(o.model),
    category: str(o.category),
  };
}

export function normalizeCustomer(item: unknown): DmsCustomer {
  const o = asRecord(item) ?? {};
  return {
    ...o,
    id: o.id as string | number | undefined,
    name: str(o.name) ?? str(o.company) ?? "Unnamed",
    email: str(o.email),
    phone: str(o.phone),
    company: str(o.company),
    notes: str(o.notes),
    created_at: str(o.created_at),
  };
}

export function normalizeOrderLine(item: unknown): DmsOrderLine {
  const o = asRecord(item) ?? {};
  const qty = num(o.qty) ?? num(o.quantity);
  return {
    ...o,
    sku: str(o.sku) ?? str(o.part_number),
    part_number: str(o.part_number) ?? str(o.sku),
    name: str(o.name),
    qty,
    quantity: qty,
    unit_price: num(o.unit_price) ?? num(o.price),
    line_total: num(o.line_total) ?? num(o.total),
  };
}

export function normalizeOrder(item: unknown): DmsOrder {
  const o = asRecord(item) ?? {};
  const rawLines = Array.isArray(o.lines)
    ? o.lines
    : Array.isArray(o.items)
      ? o.items
      : [];
  return {
    ...o,
    id: o.id as string | number | undefined,
    order_number: str(o.order_number) ?? (o.id != null ? String(o.id) : undefined),
    customer_id: o.customer_id as string | number | undefined,
    customer_name: str(o.customer_name) ?? str(o.customer),
    status: str(o.status) ?? "open",
    location_id: o.location_id as string | number | undefined,
    location_code: str(o.location_code) ?? str(o.location),
    total: num(o.total) ?? num(o.subtotal),
    subtotal: num(o.subtotal),
    lines: rawLines.map(normalizeOrderLine),
    items: rawLines.map(normalizeOrderLine),
    created_at: str(o.created_at),
    notes: str(o.notes),
  };
}

export async function getDmsStatus(): Promise<DmsStatus> {
  const raw = await dmsGet<unknown>("/status");
  const o = asRecord(raw) ?? {};
  return {
    ...o,
    ok: typeof o.ok === "boolean" ? o.ok : o.status === "ok" || o.status === "healthy",
    status: str(o.status),
    db_path: str(o.db_path),
    catalog_count: num(o.catalog_count) ?? num(o.catalog_parts) ?? num(o.parts),
    inventory_rows:
      num(o.inventory_rows) ?? num(o.inventory_count) ?? num(o.inventory),
    customer_count: num(o.customer_count) ?? num(o.customers),
    order_count: num(o.order_count) ?? num(o.orders),
    location_count: num(o.location_count) ?? num(o.locations),
    last_oem_sync:
      str(o.last_oem_sync) ??
      (o.last_oem_sync && typeof o.last_oem_sync === "object"
        ? JSON.stringify(o.last_oem_sync)
        : null),
    message: str(o.message),
  };
}

export async function listDmsInventory(opts?: {
  location?: string;
  user_key?: string;
}): Promise<{
  rows: DmsInventoryRow[];
  raw: unknown;
  acl_user?: string | null;
}> {
  const params = new URLSearchParams();
  if (opts?.location?.trim()) params.set("location", opts.location.trim());
  if (opts?.user_key?.trim()) params.set("user_key", opts.user_key.trim());
  const qs = params.toString() ? `?${params.toString()}` : "";
  const headers: HeadersInit = {};
  if (opts?.user_key?.trim()) {
    headers["X-Parts-User"] = opts.user_key.trim();
  }
  const raw = await dmsGet<unknown>(`/inventory${qs}`, { headers });
  const o = asRecord(raw);
  const rows = extractArray(raw, [
    "inventory",
    "items",
    "rows",
    "levels",
    "results",
    "data",
  ]).map(normalizeInventoryRow);
  return {
    rows,
    raw,
    acl_user: o ? str(o.acl_user) ?? null : null,
  };
}

export async function listDmsCatalog(q?: string): Promise<{
  parts: DmsCatalogPart[];
  raw: unknown;
}> {
  const qs = q && q.trim() ? `?q=${encodeURIComponent(q.trim())}` : "";
  const raw = await dmsGet<unknown>(`/catalog${qs}`);
  const parts = extractArray(raw, [
    "catalog",
    "parts",
    "items",
    "results",
    "data",
  ]).map((item) => {
    const o = asRecord(item) ?? {};
    return {
      ...o,
      sku: str(o.sku) ?? str(o.part_number),
      name: str(o.name),
      description: str(o.description),
      make: str(o.make),
      model: str(o.model),
      list_price: num(o.list_price) ?? num(o.price),
    } as DmsCatalogPart;
  });
  return { parts, raw };
}

export type UpsertCatalogInput = {
  sku: string;
  name: string;
  description?: string;
  make?: string;
  model?: string;
  year?: string;
  category?: string;
  oem_brand?: string;
  list_price?: number;
  msrp?: number;
  source?: string;
  location_qty?: Record<string, number>;
};

export async function upsertDmsCatalog(input: UpsertCatalogInput): Promise<unknown> {
  return dmsPost("/catalog", input);
}

export async function importDmsCatalogCsv(csv_text: string): Promise<unknown> {
  return dmsPost("/catalog/import-csv", { csv_text, source: "csv" });
}

export async function setDmsOrderStatus(
  orderId: string | number,
  status: string
): Promise<unknown> {
  return getJson(`/api/v1/dms/orders/${orderId}/status`, {
    baseUrl: API_BASE_URL,
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export async function createDmsInvoice(orderId: string | number): Promise<unknown> {
  return dmsPost(`/orders/${orderId}/invoice`, {});
}

export async function notifyDmsOrder(
  orderId: string | number,
  opts?: { kind?: string; dry_run?: boolean }
): Promise<unknown> {
  return dmsPost(`/orders/${orderId}/notify`, {
    kind: opts?.kind || "order_status",
    dry_run: opts?.dry_run ?? true,
  });
}

export async function listDmsNotifications(opts?: {
  order_id?: number;
  limit?: number;
}): Promise<{ notifications: unknown[]; count?: number; raw: unknown }> {
  const q = new URLSearchParams();
  if (opts?.order_id != null) q.set("order_id", String(opts.order_id));
  if (opts?.limit != null) q.set("limit", String(opts.limit));
  const qs = q.toString() ? `?${q.toString()}` : "";
  const raw = await dmsGet<Record<string, unknown>>(`/notifications${qs}`);
  const notifications = extractArray(raw, ["notifications", "items", "results", "data"]);
  return {
    notifications,
    count: typeof raw?.count === "number" ? raw.count : notifications.length,
    raw,
  };
}

export function dmsInvoicePdfUrl(orderId: string | number): string {
  return `${API_BASE_URL}/api/v1/dms/orders/${orderId}/invoice.pdf`;
}

export async function listDmsCustomers(): Promise<{
  customers: DmsCustomer[];
  raw: unknown;
}> {
  const raw = await dmsGet<unknown>("/customers");
  const customers = extractArray(raw, [
    "customers",
    "items",
    "results",
    "data",
  ]).map(normalizeCustomer);
  return { customers, raw };
}

export async function createDmsCustomer(
  input: CreateCustomerInput
): Promise<unknown> {
  try {
    return await dmsPost("/customers", input);
  } catch (e) {
    if (isBrowserOffline() || isApiUnreachable(e)) {
      const queued = enqueueOfflineMutation({
        kind: "create_customer",
        path: "/api/v1/dms/customers",
        body: { ...input },
      });
      return {
        success: true,
        queued: true,
        offline: true,
        queue_id: queued.id,
        message: "API unreachable — customer create queued offline; will retry when online",
      };
    }
    throw e;
  }
}

export async function listDmsOrders(): Promise<{
  orders: DmsOrder[];
  raw: unknown;
}> {
  const raw = await dmsGet<unknown>("/orders");
  const orders = extractArray(raw, ["orders", "items", "results", "data"]).map(
    normalizeOrder
  );
  return { orders, raw };
}

export async function createDmsOrder(input: CreateOrderInput): Promise<unknown> {
  const body = {
    customer_id: input.customer_id,
    location_id: input.location_id,
    location_code: input.location_code,
    notes: input.notes,
    lines: input.lines,
    items: input.items ?? input.lines,
  };
  try {
    return await dmsPost("/orders", body);
  } catch (e) {
    if (isBrowserOffline() || isApiUnreachable(e)) {
      const queued = enqueueOfflineMutation({
        kind: "create_order",
        path: "/api/v1/dms/orders",
        body: body as Record<string, unknown>,
      });
      return {
        success: true,
        queued: true,
        offline: true,
        queue_id: queued.id,
        message: "API unreachable — order create queued offline; will retry when online",
      };
    }
    throw e;
  }
}

export async function seedDms(): Promise<unknown> {
  return dmsPost("/seed", {});
}

export async function syncOem(input: OemSyncInput = {}): Promise<unknown> {
  return dmsPost("/oem/sync", {
    source: input.source ?? "synthetic",
    path: input.path,
  });
}

export async function reindexDms(): Promise<unknown> {
  return dmsPost("/reindex", {});
}

// --- Orgs / locations / ACL (Wave 23 multi-rooftop operator UI) ---

export type DmsOrg = {
  id?: number | string;
  code?: string;
  name?: string;
  [key: string]: unknown;
};

export type DmsLocation = {
  id?: number | string;
  code?: string;
  name?: string;
  org_id?: number | string | null;
  [key: string]: unknown;
};

export type DmsAcl = {
  user_key?: string;
  location_codes?: string[];
  restricted?: boolean;
  [key: string]: unknown;
};

export async function listDmsOrgs(): Promise<{ orgs: DmsOrg[]; raw: unknown }> {
  const raw = await dmsGet<unknown>("/orgs");
  const orgs = extractArray(raw, ["orgs", "items", "results", "data"]).map((item) => {
    const o = asRecord(item) ?? {};
    return {
      ...o,
      id: o.id as number | string | undefined,
      code: str(o.code),
      name: str(o.name) ?? str(o.code),
    } as DmsOrg;
  });
  return { orgs, raw };
}

export async function createDmsOrg(input: {
  code: string;
  name?: string;
}): Promise<unknown> {
  return dmsPost("/orgs", {
    code: input.code,
    name: input.name ?? input.code,
  });
}

export async function listDmsLocations(): Promise<{
  locations: DmsLocation[];
  raw: unknown;
}> {
  const raw = await dmsGet<unknown>("/locations");
  const locations = extractArray(raw, [
    "locations",
    "items",
    "results",
    "data",
  ]).map((item) => {
    const o = asRecord(item) ?? {};
    return {
      ...o,
      id: o.id as number | string | undefined,
      code: str(o.code),
      name: str(o.name) ?? str(o.code),
      org_id: (o.org_id as number | string | null | undefined) ?? null,
    } as DmsLocation;
  });
  return { locations, raw };
}

export async function setDmsLocationOrg(
  locationCode: string,
  orgCode: string
): Promise<unknown> {
  const code = encodeURIComponent(locationCode);
  return dmsPut(`/locations/${code}/org`, { org_code: orgCode });
}

export async function getDmsAcl(userKey: string): Promise<DmsAcl> {
  const key = encodeURIComponent(userKey.trim());
  const raw = await dmsGet<unknown>(`/acl/${key}`);
  const o = asRecord(raw) ?? {};
  const codes = extractArray(raw, ["location_codes", "locations", "codes"]).map(
    (c) => String(c)
  );
  return {
    ...o,
    user_key: str(o.user_key) ?? userKey,
    location_codes: codes,
    restricted: typeof o.restricted === "boolean" ? o.restricted : codes.length > 0,
  };
}

export async function setDmsAcl(
  userKey: string,
  locationCodes: string[]
): Promise<unknown> {
  const key = encodeURIComponent(userKey.trim());
  return dmsPut(`/acl/${key}`, { location_codes: locationCodes });
}

// --- Transfers (Wave 26) ---

export type DmsTransfer = {
  id?: number | string;
  sku?: string;
  from_code?: string;
  to_code?: string;
  qty?: number;
  status?: string;
  requested_by?: string;
  approved_by?: string;
  notes?: string;
  created_at?: string;
  [key: string]: unknown;
};

export async function listDmsTransfers(opts?: {
  status?: string;
  limit?: number;
}): Promise<{ transfers: DmsTransfer[]; approval_threshold?: number; raw: unknown }> {
  const params = new URLSearchParams();
  if (opts?.status) params.set("status", opts.status);
  if (opts?.limit) params.set("limit", String(opts.limit));
  const qs = params.toString() ? `?${params.toString()}` : "";
  const raw = await dmsGet<unknown>(`/transfers${qs}`);
  const o = asRecord(raw) ?? {};
  const transfers = extractArray(raw, ["transfers", "items", "results"]).map((item) => {
    const r = asRecord(item) ?? {};
    return {
      ...r,
      id: r.id as number | string | undefined,
      sku: str(r.sku),
      from_code: str(r.from_code),
      to_code: str(r.to_code),
      qty: num(r.qty),
      status: str(r.status),
      requested_by: str(r.requested_by),
      approved_by: str(r.approved_by),
      notes: str(r.notes),
      created_at: str(r.created_at),
    } as DmsTransfer;
  });
  return {
    transfers,
    approval_threshold: num(o.approval_threshold),
    raw,
  };
}

export async function createDmsTransfer(input: {
  sku: string;
  from_location: string;
  to_location: string;
  qty: number;
  notes?: string;
  requested_by?: string;
  force_complete?: boolean;
}): Promise<unknown> {
  return dmsPost("/transfers", input);
}

export async function approveDmsTransfer(id: string | number): Promise<unknown> {
  return dmsPost(`/transfers/${id}/approve`, {});
}

export async function cancelDmsTransfer(id: string | number): Promise<unknown> {
  return dmsPost(`/transfers/${id}/cancel`, {});
}

export type StockAdjustInput = {
  sku: string;
  location: string;
  delta: number;
  reason?: string;
  notes?: string;
  actor?: string;
};

export type DmsStockAdjustment = {
  id?: number | string;
  sku?: string;
  location_code?: string;
  location_name?: string;
  delta?: number;
  qty_before?: number;
  qty_after?: number;
  reason?: string;
  notes?: string;
  actor?: string;
  created_at?: string;
  [key: string]: unknown;
};

export async function adjustDmsInventory(input: StockAdjustInput): Promise<unknown> {
  return dmsPost("/inventory/adjust", input);
}

export async function listDmsStockAdjustments(opts?: {
  sku?: string;
  location?: string;
  limit?: number;
}): Promise<{ adjustments: DmsStockAdjustment[]; raw: unknown }> {
  const params = new URLSearchParams();
  if (opts?.sku?.trim()) params.set("sku", opts.sku.trim());
  if (opts?.location?.trim()) params.set("location", opts.location.trim());
  if (opts?.limit) params.set("limit", String(opts.limit));
  const qs = params.toString() ? `?${params.toString()}` : "";
  const raw = await dmsGet<unknown>(`/inventory/adjustments${qs}`);
  const adjustments = extractArray(raw, ["adjustments", "items", "results"]).map((item) => {
    const r = asRecord(item) ?? {};
    return {
      ...r,
      id: r.id as number | string | undefined,
      sku: str(r.sku),
      location_code: str(r.location_code),
      location_name: str(r.location_name),
      delta: num(r.delta),
      qty_before: num(r.qty_before),
      qty_after: num(r.qty_after),
      reason: str(r.reason),
      notes: str(r.notes),
      actor: str(r.actor),
      created_at: str(r.created_at),
    } as DmsStockAdjustment;
  });
  return { adjustments, raw };
}

export type DmsAnalytics = {
  ok?: boolean;
  success?: boolean;
  source?: string;
  backend?: string;
  generated_at?: string;
  counts?: {
    locations?: number;
    catalog_parts?: number;
    inventory_rows?: number;
    inventory_units?: number;
    customers?: number;
    orders?: number;
    stock_adjustments?: number;
    transfers?: number;
    low_stock_rows?: number;
    zero_stock_rows?: number;
    orders_last_7d?: number;
    adjustments_last_7d?: number;
    [key: string]: number | undefined;
  };
  orders_by_status?: Record<string, number>;
  transfers_by_status?: Record<string, number>;
  adjustments_by_reason?: Array<{
    reason?: string;
    count?: number;
    delta_sum?: number;
  }>;
  revenue?: {
    order_book_value?: number;
    realized_value?: number;
    open_pipeline_value?: number;
    currency?: string;
    note?: string;
  };
  top_inventory_skus?: Array<{ sku?: string; units?: number }>;
  dead_stock?: Array<{ sku?: string; units?: number }>;
  fill_rate?: {
    ordered_units?: number;
    fulfilled_units?: number;
    cancelled_units?: number;
    fulfillment_ratio?: number | null;
    note?: string;
  };
  supersessions?: { mapping_count?: number };
  payments?: { event_count?: number; note?: string };
  shipments?: { event_count?: number; note?: string };
  oem?: {
    feed_configured?: boolean;
    last_sync?: unknown;
    recent_runs?: unknown[];
  };
  [key: string]: unknown;
};

export async function getDmsAnalytics(): Promise<DmsAnalytics> {
  const raw = await dmsGet<unknown>("/analytics");
  const o = asRecord(raw) ?? {};
  const countsRaw = asRecord(o.counts) ?? {};
  const counts: DmsAnalytics["counts"] = {};
  for (const [k, v] of Object.entries(countsRaw)) {
    const n = num(v);
    if (n !== undefined) counts[k] = n;
  }
  const orders_by_status: Record<string, number> = {};
  const obs = asRecord(o.orders_by_status) ?? {};
  for (const [k, v] of Object.entries(obs)) {
    const n = num(v);
    if (n !== undefined) orders_by_status[k] = n;
  }
  const transfers_by_status: Record<string, number> = {};
  const tbs = asRecord(o.transfers_by_status) ?? {};
  for (const [k, v] of Object.entries(tbs)) {
    const n = num(v);
    if (n !== undefined) transfers_by_status[k] = n;
  }
  const adjList = extractArray(o.adjustments_by_reason, ["adjustments_by_reason", "items"]);
  const adjustments_by_reason = (adjList.length ? adjList : Array.isArray(o.adjustments_by_reason) ? (o.adjustments_by_reason as unknown[]) : []).map((item) => {
    const r = asRecord(item) ?? {};
    return {
      reason: str(r.reason),
      count: num(r.count),
      delta_sum: num(r.delta_sum),
    };
  });
  const topList = extractArray(o.top_inventory_skus, ["top_inventory_skus", "items"]);
  const top_inventory_skus = (topList.length ? topList : Array.isArray(o.top_inventory_skus) ? (o.top_inventory_skus as unknown[]) : []).map((item) => {
    const r = asRecord(item) ?? {};
    return { sku: str(r.sku), units: num(r.units) };
  });
  const deadList = extractArray(o.dead_stock, ["dead_stock", "items"]);
  const dead_stock = (deadList.length ? deadList : Array.isArray(o.dead_stock) ? (o.dead_stock as unknown[]) : []).map((item) => {
    const r = asRecord(item) ?? {};
    return { sku: str(r.sku), units: num(r.units) };
  });
  const fillRaw = asRecord(o.fill_rate) ?? {};
  const ssRaw = asRecord(o.supersessions) ?? {};
  const payRaw = asRecord(o.payments) ?? {};
  const shipRaw = asRecord(o.shipments) ?? {};
  const revenueRaw = asRecord(o.revenue) ?? {};
  const oemRaw = asRecord(o.oem) ?? {};
  return {
    ...o,
    ok: typeof o.ok === "boolean" ? o.ok : true,
    source: str(o.source),
    backend: str(o.backend),
    generated_at: str(o.generated_at),
    counts,
    orders_by_status,
    transfers_by_status,
    adjustments_by_reason,
    revenue: {
      order_book_value: num(revenueRaw.order_book_value),
      realized_value: num(revenueRaw.realized_value),
      open_pipeline_value: num(revenueRaw.open_pipeline_value),
      currency: str(revenueRaw.currency) ?? "USD",
      note: str(revenueRaw.note),
    },
    top_inventory_skus,
    dead_stock,
    fill_rate: {
      ordered_units: num(fillRaw.ordered_units),
      fulfilled_units: num(fillRaw.fulfilled_units),
      cancelled_units: num(fillRaw.cancelled_units),
      fulfillment_ratio:
        fillRaw.fulfillment_ratio === null || fillRaw.fulfillment_ratio === undefined
          ? null
          : num(fillRaw.fulfillment_ratio) ?? null,
      note: str(fillRaw.note),
    },
    supersessions: { mapping_count: num(ssRaw.mapping_count) },
    payments: {
      event_count: num(payRaw.event_count),
      note: str(payRaw.note),
    },
    shipments: {
      event_count: num(shipRaw.event_count),
      note: str(shipRaw.note),
    },
    oem: {
      feed_configured: Boolean(oemRaw.feed_configured),
      last_sync: oemRaw.last_sync,
      recent_runs: Array.isArray(oemRaw.recent_runs) ? oemRaw.recent_runs : [],
    },
  };
}

export type DmsSupersession = {
  id?: number;
  old_sku?: string;
  new_sku?: string;
  notes?: string;
  effective_from?: string;
  created_at?: string;
  actor?: string;
};

export async function listDmsSupersessions(limit = 100): Promise<{
  supersessions: DmsSupersession[];
  count: number;
}> {
  const raw = await dmsGet<unknown>(`/supersessions?limit=${limit}`);
  const o = asRecord(raw) ?? {};
  const list = extractArray(o.supersessions, ["supersessions", "items", "data"]);
  const supersessions = (list.length ? list : []).map((item) => {
    const r = asRecord(item) ?? {};
    return {
      id: num(r.id),
      old_sku: str(r.old_sku),
      new_sku: str(r.new_sku),
      notes: str(r.notes),
      effective_from: str(r.effective_from),
      created_at: str(r.created_at),
      actor: str(r.actor),
    };
  });
  return { supersessions, count: num(o.count) ?? supersessions.length };
}

export async function createDmsSupersession(body: {
  old_sku: string;
  new_sku: string;
  notes?: string;
}): Promise<unknown> {
  return dmsPost("/supersessions", body);
}

export async function resolveDmsSupersession(sku: string): Promise<{
  ok?: boolean;
  sku?: string;
  current_sku?: string;
  chain?: string[];
  hops?: number;
  superseded?: boolean;
  error?: string;
}> {
  const raw = await dmsGet<unknown>(`/supersessions/resolve?sku=${encodeURIComponent(sku)}`);
  const o = asRecord(raw) ?? {};
  const chain = Array.isArray(o.chain) ? o.chain.map((x) => String(x)) : undefined;
  return {
    ok: typeof o.ok === "boolean" ? o.ok : Boolean(o.success),
    sku: str(o.sku),
    current_sku: str(o.current_sku),
    chain,
    hops: num(o.hops),
    superseded: typeof o.superseded === "boolean" ? o.superseded : undefined,
    error: str(o.error),
  };
}

export async function exportDmsCompliance(days = 90): Promise<Record<string, unknown>> {
  const raw = await dmsGet<unknown>(`/compliance/export?days=${days}`);
  return (asRecord(raw) as Record<string, unknown>) ?? {};
}

// --- Transmission Hard Parts Inquiry (Phase 5) ---

export type TransmissionInquiryResponse = {
  query: string;
  status: string;
  sku: string | null;
  transmission_family: string | null;
  part_type: string | null;
  fitment_status: string | null;
  inventory_available: boolean;
  aggregate_available: number;
  verification_status: string | null;
  human_readable: string;
  inventory: Array<{
    location?: string;
    location_name?: string;
    qty?: number;
    condition?: string;
    bin?: string;
  }>;
  identifiers: Array<{
    identifier_type?: string;
    identifier_value?: string;
  }>;
  interchanges: Array<{
    source_sku?: string;
    target_sku?: string;
    relationship_type?: string;
    verification_status?: string;
  }>;
  /** Formal unit-of-work outcome: RESOLVED | NEEDS_HUMAN */
  outcome?: string | null;
  confidence?: number | null;
  recommended_action?: string | null;
  ambiguity_reason?: string | null;
  intent?: string | null;
  candidate_match_quality?: string | null;
  evidence_sufficiency?: string | null;
  decision_source?: string | null;
  request_id?: string | null;
  decision?: Record<string, unknown> | null;
};

export async function transmissionInquiry(
  query: string
): Promise<TransmissionInquiryResponse> {
  return dmsPost<TransmissionInquiryResponse>("/transmission/inquiry", { query });
}

// --- Transmission Pilot Import (Phase 10) ---

export type TransmissionImportRowPlan = {
  row_number?: number;
  status?: "valid" | "warning" | "invalid" | string;
  errors?: string[];
  warnings?: string[];
  sku?: string;
  name?: string;
  transmission_family?: string;
  location?: string;
  qty?: number;
  condition?: string;
  bin?: string;
  catalog_action?: string;
  inventory_action?: string;
  identifier_action?: string;
  location_action?: string;
  existing_sku?: boolean;
};

export type TransmissionImportResult = {
  success?: boolean;
  ok?: boolean;
  mode?: "preview" | "commit" | string;
  source_label?: string;
  allow_new_locations?: boolean;
  total_rows?: number;
  valid_rows?: number;
  warning_rows?: number;
  invalid_rows?: number;
  new_sku_count?: number;
  existing_sku_count?: number;
  catalog_inserts?: number;
  catalog_updates?: number;
  inventory_inserts?: number;
  inventory_updates?: number;
  identifier_inserts?: number;
  locations_to_create?: number;
  locations_referenced?: string[];
  unknown_locations?: string[];
  file_errors?: string[];
  committed?: boolean;
  commit_result?: Record<string, unknown>;
  rows?: TransmissionImportRowPlan[];
  rows_truncated?: number;
  [key: string]: unknown;
};

export type TransmissionImportInput = {
  csv_text: string;
  source?: string;
  allow_new_locations?: boolean;
};

export async function previewTransmissionImport(
  input: TransmissionImportInput
): Promise<TransmissionImportResult> {
  return dmsPost<TransmissionImportResult>("/transmission/import/preview", {
    csv_text: input.csv_text,
    source: input.source,
    allow_new_locations: Boolean(input.allow_new_locations),
  });
}

export async function commitTransmissionImport(
  input: TransmissionImportInput
): Promise<TransmissionImportResult> {
  return dmsPost<TransmissionImportResult>("/transmission/import/commit", {
    csv_text: input.csv_text,
    source: input.source,
    allow_new_locations: Boolean(input.allow_new_locations),
  });
}

export type TransmissionImportHistoryItem = {
  import_run_id?: number;
  created_at?: string;
  source_label?: string;
  status?: string;
  summary?: string;
  valid_rows?: number;
  warning_rows?: number;
  catalog_inserts?: number;
  inventory_inserts?: number;
  inventory_updates?: number;
  identifier_inserts?: number;
  locations_created?: number;
  mutation_count?: number;
  rollback_status?: string;
  rollback_available?: boolean;
  rolled_back_at?: string;
  backend?: string;
  [key: string]: unknown;
};

export type TransmissionImportRollbackPreview = {
  eligible?: boolean;
  import_run_id?: number;
  source_label?: string;
  reason?: string | null;
  conflicts?: Array<Record<string, unknown>>;
  actions?: Array<Record<string, unknown>>;
  preserve?: Array<Record<string, unknown>>;
  inventory_restores?: number;
  rows_to_delete?: number;
  [key: string]: unknown;
};

export async function listTransmissionImportHistory(
  limit = 50
): Promise<{ success?: boolean; count?: number; imports: TransmissionImportHistoryItem[] }> {
  return dmsGet(`/transmission/import/history?limit=${encodeURIComponent(String(limit))}`);
}

export async function previewTransmissionImportRollback(
  runId: number
): Promise<TransmissionImportRollbackPreview> {
  return dmsPost(`/transmission/import/${runId}/rollback/preview`, {});
}

export async function commitTransmissionImportRollback(
  runId: number
): Promise<Record<string, unknown>> {
  return dmsPost(`/transmission/import/${runId}/rollback`, {});
}

export { API_BASE_URL, ApiError };
