/**
 * DMS Core API client — NEXT_PUBLIC_API_URL + /api/v1/dms/*
 * Offline-capable SQLite DMS (see docs/DMS_OEM.md).
 */

import { API_BASE_URL, ApiError, getJson } from "@/lib/api";

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
  status?: string;
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

export async function listDmsInventory(): Promise<{
  rows: DmsInventoryRow[];
  raw: unknown;
}> {
  const raw = await dmsGet<unknown>("/inventory");
  const rows = extractArray(raw, [
    "inventory",
    "items",
    "rows",
    "levels",
    "results",
    "data",
  ]).map(normalizeInventoryRow);
  return { rows, raw };
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
  return dmsPost("/customers", input);
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
  return dmsPost("/orders", body);
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

export { API_BASE_URL, ApiError };
