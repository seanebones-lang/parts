/**
 * Payments + shipping API client — key-gated Stripe / EasyPost.
 * Never invents charges or labels client-side.
 */

import { API_BASE_URL, ApiError, getJson } from "@/lib/api";

function path(p: string): string {
  const x = p.startsWith("/") ? p : `/${p}`;
  return x;
}

export async function getIntegrations(): Promise<Record<string, unknown>> {
  return getJson<Record<string, unknown>>("/api/v1/system/integrations", {
    baseUrl: API_BASE_URL,
  });
}

export async function getPaymentConfig(): Promise<Record<string, unknown>> {
  return getJson<Record<string, unknown>>("/api/v1/payments/config", {
    baseUrl: API_BASE_URL,
  });
}

export async function createOrderPaymentIntent(body: {
  amount: number;
  currency?: string;
  order_id?: string | number;
  customer_email?: string;
  description?: string;
}): Promise<Record<string, unknown>> {
  return getJson<Record<string, unknown>>("/api/v1/payments/order-intent", {
    baseUrl: API_BASE_URL,
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function getShippingConfig(): Promise<Record<string, unknown>> {
  return getJson<Record<string, unknown>>("/api/v1/shipping/config", {
    baseUrl: API_BASE_URL,
  });
}

export type ShipAddress = {
  name?: string;
  street1: string;
  street2?: string;
  city: string;
  state: string;
  zip: string;
  country?: string;
  phone?: string;
};

export async function getShippingRates(body: {
  from_address: ShipAddress;
  to_address: ShipAddress;
  parcel?: { weight?: number; length?: number; width?: number; height?: number };
  order_id?: string | number;
}): Promise<Record<string, unknown>> {
  return getJson<Record<string, unknown>>("/api/v1/shipping/rates", {
    baseUrl: API_BASE_URL,
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function buyShippingLabel(body: {
  shipment_id: string;
  rate_id: string;
  order_id?: string | number;
}): Promise<Record<string, unknown>> {
  return getJson<Record<string, unknown>>("/api/v1/shipping/label", {
    baseUrl: API_BASE_URL,
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function isCommerceUnreachable(err: unknown): boolean {
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

export { path };
