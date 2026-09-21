/**
 * Operator-facing language for automation / email classification strings.
 * Keep raw machine tokens out of primary JP UI surfaces.
 */

export type TrafficColor = "green" | "yellow" | "red" | "none";

export function normalizeTrafficColor(raw?: string | null): TrafficColor {
  const c = String(raw || "").toLowerCase().trim();
  if (c === "green" || c === "yellow" || c === "red") return c;
  return "none";
}

/** True semantic traffic-light classes (never map green→blue / yellow→gray). */
export function trafficBadgeClass(color: string): string {
  const c = normalizeTrafficColor(color);
  if (c === "green") {
    return "border-transparent bg-emerald-600 text-white hover:bg-emerald-600";
  }
  if (c === "yellow") {
    return "border-transparent bg-amber-400 text-amber-950 hover:bg-amber-400";
  }
  if (c === "red") {
    return "border-transparent bg-red-600 text-white hover:bg-red-600";
  }
  return "border-slate-300 bg-slate-100 text-slate-700";
}

export function trafficDotClass(color: string): string {
  const c = normalizeTrafficColor(color);
  if (c === "green") return "bg-emerald-500";
  if (c === "yellow") return "bg-amber-400";
  if (c === "red") return "bg-red-500";
  return "bg-slate-300";
}

export function trafficLabel(color: string): string {
  const c = normalizeTrafficColor(color);
  if (c === "green") return "Handled";
  if (c === "yellow") return "Needs review";
  if (c === "red") return "Urgent";
  return "Ungraded";
}

export function trafficCountClass(color: string): string {
  const c = normalizeTrafficColor(color);
  if (c === "green") return "text-emerald-700";
  if (c === "yellow") return "text-amber-700";
  if (c === "red") return "text-red-700";
  return "text-slate-800";
}

/** Map classifier / specialist tokens to operator category labels. */
export function inquiryCategoryLabel(raw?: string | null): string {
  const t = String(raw || "")
    .trim()
    .toLowerCase()
    .replace(/-/g, "_");
  const map: Record<string, string> = {
    parts_quote: "Parts Quote",
    quote_request: "Parts Quote",
    price_request: "Parts Quote",
    parts_order: "Parts Order",
    order: "Parts Order",
    inventory: "Inventory Inquiry",
    parts_availability: "Inventory Inquiry",
    shipping: "Shipping",
    order_status: "Shipping",
    payment: "Customer Service",
    invoice: "Customer Service",
    complaint: "Complaint",
    customer_service: "Customer Service",
    general: "Customer Service",
    general_question: "Customer Service",
    compatibility_fitment: "Fitment Question",
    sell_part: "Parts Quote",
  };
  if (map[t]) return map[t];
  if (!t) return "Inquiry";
  return t
    .split("_")
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export function humanAutomationKind(kind?: string | null): string {
  switch (kind) {
    case "transmission_request_uow":
      return "Parts inquiry";
    case "transmission_import":
      return "Inventory import";
    case "transmission_import_rollback":
      return "Import rollback";
    case "transmission_jev_shadow":
      return "Decision observe";
    case "email_process":
      return "Email inquiry";
    default:
      return kind ? String(kind).replace(/_/g, " ") : "Activity";
  }
}

/**
 * Turn raw automation summaries into operator language.
 * Examples:
 *   "quote_request → green specialist=parts_quote"
 *   → { title: "Email inquiry handled", detail: "Parts quote · Completed automatically" }
 */
export function humanizeActivitySummary(
  kind?: string | null,
  summary?: string | null,
  requiresHuman?: boolean
): { title: string; detail: string } {
  const k = String(kind || "");
  const s = String(summary || "").trim();

  if (k === "email_process" || /email/i.test(k)) {
    const lower = s.toLowerCase();
    let color: TrafficColor = "none";
    if (/\bgreen\b/.test(lower)) color = "green";
    else if (/\byellow\b/.test(lower)) color = "yellow";
    else if (/\bred\b/.test(lower)) color = "red";
    else if (requiresHuman) color = "yellow";

    // extract type token before arrow or as first word
    const typeMatch =
      s.match(/^([a-z0-9_]+)\s*→/i) ||
      s.match(/\b(quote_request|parts_quote|parts_order|inventory|shipping|complaint|payment|customer_service|general)\b/i);
    const typeTok = typeMatch ? typeMatch[1] : "";
    const cat = inquiryCategoryLabel(typeTok);

    if (color === "green") {
      return {
        title: "Email inquiry handled",
        detail: `${cat} · Completed automatically`,
      };
    }
    if (color === "yellow") {
      return {
        title: "Email needs review",
        detail: `${cat} · Human confirmation required`,
      };
    }
    if (color === "red") {
      return {
        title: "Urgent customer issue",
        detail: `${cat} · Human attention required`,
      };
    }
    return {
      title: humanAutomationKind(k),
      detail: cat !== "Inquiry" ? cat : s || "Recorded",
    };
  }

  if (k === "transmission_import" || /import ok/i.test(s)) {
    return {
      title: "Inventory import completed",
      detail: humanizeImportSummary(s) || "Import recorded",
    };
  }

  if (k === "transmission_request_uow") {
    if (/FINAL RESOLVED/i.test(s)) {
      const sku = s.match(/sku=([^\s]+)/i)?.[1];
      return {
        title: "Parts inquiry finalized",
        detail: sku && sku !== "—" ? `Accepted ${sku}` : "Final result recorded",
      };
    }
    if (/NEEDS_HUMAN|needs human/i.test(s)) {
      return { title: "Parts inquiry needs review", detail: "Counter confirmation required" };
    }
    if (/RESOLVED/i.test(s)) {
      return { title: "Parts inquiry matched", detail: s.replace(/_/g, " ") };
    }
  }

  // strip machine tokens from leftover summaries
  const cleaned = s
    .replace(/specialist=\S+/gi, "")
    .replace(/\b(quote_request|parts_quote|parts_order)\b/gi, (m) => inquiryCategoryLabel(m))
    .replace(/\s*→\s*/g, " · ")
    .replace(/\s{2,}/g, " ")
    .trim();

  return {
    title: humanAutomationKind(k),
    detail: cleaned || "Recorded",
  };
}

/** import ok rows=3 cat+=3 inv+=3 → readable line */
export function humanizeImportSummary(raw?: string | null): string {
  if (!raw) return "";
  const s = String(raw);
  const parts: string[] = [];
  const rows = s.match(/rows?\s*=?\s*(\d+)/i) || s.match(/\brows\s+(\d+)/i);
  const cat = s.match(/cat\+?=?\s*(\d+)/i) || s.match(/catalog[^\d]*(\d+)/i);
  const inv = s.match(/inv\+?=?\s*(\d+)/i) || s.match(/inventory[^\d]*(\d+)/i);
  const invUpd = s.match(/upd=?(\d+)/i);
  if (rows) parts.push(`${rows[1]} records processed`);
  if (inv) parts.push(`${inv[1]} inventory records added`);
  if (invUpd && invUpd[1] !== "0") parts.push(`${invUpd[1]} inventory updated`);
  if (cat) parts.push(`${cat[1]} SKUs added`);
  if (parts.length) return parts.join(" · ");
  if (/import ok/i.test(s)) return "Inventory import completed";
  return s
    .replace(/import ok/gi, "Import completed")
    .replace(/cat\+=/gi, "SKUs+")
    .replace(/inv\+=/gi, "inventory+")
    .replace(/_/g, " ");
}

export function humanizeImportHistoryItem(item: {
  source_label?: string | null;
  source?: string | null;
  summary?: string | null;
  valid_rows?: number | null;
  catalog_inserts?: number | null;
  inventory_inserts?: number | null;
  inventory_updates?: number | null;
  import_run_id?: number | null;
  id?: number | null;
}): { title: string; stats: string } {
  const src = String(item.source_label || item.source || "").replace(/^pilot_csv:/i, "");
  const title =
    src ||
    (item.import_run_id != null || item.id != null
      ? `Import #${item.import_run_id ?? item.id}`
      : "Inventory import");
  const parts: string[] = [];
  if (typeof item.valid_rows === "number") parts.push(`${item.valid_rows} records processed`);
  if (typeof item.inventory_inserts === "number" && item.inventory_inserts)
    parts.push(`${item.inventory_inserts} inventory records added`);
  if (typeof item.inventory_updates === "number" && item.inventory_updates)
    parts.push(`${item.inventory_updates} inventory updated`);
  if (typeof item.catalog_inserts === "number" && item.catalog_inserts)
    parts.push(`${item.catalog_inserts} SKUs added`);
  const fromSummary = humanizeImportSummary(item.summary || "");
  return {
    title,
    stats: parts.length ? parts.join(" · ") : fromSummary || "Import recorded",
  };
}
