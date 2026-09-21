/**
 * Email desk API client — /api/v1/emails/*
 * Auto-answer + green/yellow/red + searchable archive.
 */

import { API_BASE_URL, ApiError, getJson } from "@/lib/api";

const PREFIX = "/api/v1/emails";

function path(p: string): string {
  const x = p.startsWith("/") ? p : `/${p}`;
  return `${PREFIX}${x}`;
}

async function emailGet<T = unknown>(p: string, init?: RequestInit): Promise<T> {
  return getJson<T>(path(p), { ...init, baseUrl: API_BASE_URL });
}

async function emailPost<T = unknown>(
  p: string,
  body?: unknown,
  init?: RequestInit
): Promise<T> {
  return getJson<T>(path(p), {
    ...init,
    baseUrl: API_BASE_URL,
    method: "POST",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

export function isEmailApiUnreachable(err: unknown): boolean {
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

export type EmailTrafficLight = {
  color?: string | null;
  confidence?: number | null;
  reason?: string | null;
  requires_human?: boolean;
  actions?: string[];
};

export type DeskEmail = {
  id?: number;
  message_id?: string;
  subject?: string;
  sender_email?: string;
  sender_name?: string;
  body_text?: string;
  received_at?: string;
  status?: string;
  email_type?: string;
  priority?: string;
  department?: string;
  classification_confidence?: number;
  traffic_light?: EmailTrafficLight | string | null;
  traffic_confidence?: number;
  traffic_reason?: string;
  requires_human?: boolean;
  specialist?: string;
  suggested_response?: string;
  extracted?: Record<string, unknown>;
  hits?: unknown[];
  actions?: string[];
  agents_invoked?: string[];
  ai_processed?: boolean;
  response_sent?: boolean;
  error_message?: string | null;
  [key: string]: unknown;
};

export type EmailStatus = {
  ok?: boolean;
  total?: number;
  requires_human?: number;
  by_traffic_light?: Record<string, number>;
  by_status?: Record<string, number>;
  specialists?: string[];
  selling_point?: string;
  mailbox?: { imap_configured?: boolean; smtp_configured?: boolean; auto_send?: boolean };
  production_ready?: boolean;
  db_path?: string;
  [key: string]: unknown;
};

export function trafficColor(e: DeskEmail): string {
  const tl = e.traffic_light;
  if (typeof tl === "string") return tl.toLowerCase();
  if (tl && typeof tl === "object" && tl.color) return String(tl.color).toLowerCase();
  return "none";
}

export async function getEmailStatus(): Promise<EmailStatus> {
  return emailGet<EmailStatus>("/status");
}

export async function listEmails(params?: {
  q?: string;
  status?: string;
  traffic_light?: string;
  requires_human?: boolean;
  limit?: number;
  skip?: number;
}): Promise<{ ok?: boolean; count: number; emails: DeskEmail[]; status?: EmailStatus }> {
  const sp = new URLSearchParams();
  if (params?.q) sp.set("q", params.q);
  if (params?.status) sp.set("status", params.status);
  if (params?.traffic_light) sp.set("traffic_light", params.traffic_light);
  if (params?.requires_human !== undefined)
    sp.set("requires_human", String(params.requires_human));
  if (params?.limit !== undefined) sp.set("limit", String(params.limit));
  if (params?.skip !== undefined) sp.set("skip", String(params.skip));
  const qs = sp.toString();
  return emailGet(`/${qs ? `?${qs}` : ""}`);
}

export async function getEmail(id: number): Promise<{ ok?: boolean; email: DeskEmail }> {
  return emailGet(`/${id}`);
}

export async function seedEmails(opts?: {
  clear?: boolean;
  process?: boolean;
  /** "transmission" for JP vertical seed; omit/default for generic PARTS seed */
  vertical?: string;
}): Promise<{ ok?: boolean; seeded?: number; emails?: DeskEmail[]; status?: EmailStatus; vertical?: string }> {
  return emailPost("/seed", {
    clear: opts?.clear ?? false,
    process: opts?.process ?? true,
    vertical: opts?.vertical,
  });
}

export async function processEmails(opts?: {
  email_id?: number;
  limit?: number;
}): Promise<{ ok?: boolean; processed?: number; results?: DeskEmail[] }> {
  return emailPost("/process", {
    email_id: opts?.email_id,
    limit: opts?.limit ?? 50,
  });
}

export async function ingestEmail(body: {
  subject: string;
  body: string;
  sender_email: string;
  sender_name?: string;
  process?: boolean;
}): Promise<{ ok?: boolean; email: DeskEmail }> {
  return emailPost("/ingest", body);
}

export async function sendEmail(
  id: number,
  opts?: { body?: string; force?: boolean; dry_run?: boolean }
): Promise<{ ok?: boolean; email: DeskEmail }> {
  return emailPost(`/${id}/send`, {
    body: opts?.body,
    force: opts?.force ?? false,
    dry_run: opts?.dry_run ?? false,
  });
}

export async function overrideEmail(
  id: number,
  color: "green" | "yellow" | "red",
  notes?: string
): Promise<{ ok?: boolean; email: DeskEmail }> {
  return emailPost(`/${id}/override`, { color, notes });
}

export async function getMailboxStatus(): Promise<Record<string, unknown>> {
  return emailGet("/mailbox");
}
