/**
 * Frontend-only presentation mode for vertical pilots.
 *
 * Enable with:
 *   NEXT_PUBLIC_DEMO_VERTICAL=transmission
 *
 * When unset/disabled, full PARTS UI is unchanged.
 * Does not change API, DMS, importer, or resolver behavior.
 */

export type DemoVertical = "transmission" | null;

export function getDemoVertical(): DemoVertical {
  const raw = (process.env.NEXT_PUBLIC_DEMO_VERTICAL || "").trim().toLowerCase();
  if (raw === "transmission") return "transmission";
  return null;
}

export function isTransmissionDemo(): boolean {
  return getDemoVertical() === "transmission";
}

/** Neutral operational labels for known pilot location codes (UI only). */
const TRANSMISSION_LOCATION_LABELS: Record<string, string> = {
  "CHI-N": "Main Warehouse",
  OHARE: "Front Counter",
};

/**
 * Map a DMS location code/name to a presentation label.
 * Canonical codes are preserved; display names are presentation-only.
 */
export function transmissionLocationLabel(
  codeOrName?: string | null
): string | null {
  if (!codeOrName) return null;
  const key = String(codeOrName).trim();
  if (TRANSMISSION_LOCATION_LABELS[key]) {
    return TRANSMISSION_LOCATION_LABELS[key];
  }
  // Some APIs return the friendly name already (e.g. "Chicago North")
  const upper = key.toUpperCase();
  if (upper.includes("CHI") && upper.includes("N")) {
    return TRANSMISSION_LOCATION_LABELS["CHI-N"];
  }
  if (upper.includes("OHARE") || upper.includes("O'HARE") || upper.includes("O’HARE")) {
    return TRANSMISSION_LOCATION_LABELS.OHARE;
  }
  // Known seed display names
  if (/chicago\s*north/i.test(key)) return "Main Warehouse";
  if (/o'?hare/i.test(key)) return "Front Counter";
  return null;
}

export function formatTransmissionLocationLine(inv: {
  location?: string | null;
  location_name?: string | null;
  bin?: string | null;
}): { title: string; subtitle: string } {
  const code = (inv.location || "").trim();
  const name = (inv.location_name || "").trim();
  const label =
    transmissionLocationLabel(code) ||
    transmissionLocationLabel(name) ||
    name ||
    code ||
    "Location";
  const codePart = code || name || "";
  const binPart = inv.bin ? `Bin ${inv.bin}` : null;
  const subtitle = [codePart, binPart].filter(Boolean).join(" · ");
  return { title: label, subtitle };
}

export const JP_BRAND = {
  mark: "JP",
  title: "JP Transmission",
  subtitle: "Inventory Pilot · Built by NextEleven",
  documentTitle: "JP Transmission — Inventory Pilot | NextEleven",
  documentDescription:
    "JP Transmission inventory pilot: counter lookup, pilot data import, and safe reversible imports. Evaluation demo by NextEleven.",
  applicationName: "JP Transmission Pilot",
} as const;

export const PARTS_BRAND = {
  mark: "P",
  title: "Parts",
  subtitle: "NextEleven · dealership parts system",
  documentTitle: "Parts — Dealership Parts System | NextEleven",
  documentDescription:
    "Multi-location dealership parts system: AI search, DMS inventory/orders, OEM feed ingest.",
  applicationName: "Parts",
} as const;

export function getBrand() {
  return isTransmissionDemo() ? JP_BRAND : PARTS_BRAND;
}
