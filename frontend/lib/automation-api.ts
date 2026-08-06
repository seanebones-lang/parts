/**
 * Automation API client — /api/v1/automation/*
 * White-label AI workflow runs, HIL alerts, email→order bridge, rulesets.
 */

import { API_BASE_URL, ApiError, getJson } from "@/lib/api";

const PREFIX = "/api/v1/automation";

function path(p: string): string {
  const s = p.startsWith("/") ? p : `/${p}`;
  return `${PREFIX}${s}`;
}

async function autoGet<T = unknown>(p: string, init?: RequestInit): Promise<T> {
  return getJson<T>(path(p), { ...init, baseUrl: API_BASE_URL });
}

async function autoPost<T = unknown>(
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

async function autoPut<T = unknown>(
  p: string,
  body?: unknown,
  init?: RequestInit
): Promise<T> {
  return getJson<T>(path(p), {
    ...init,
    baseUrl: API_BASE_URL,
    method: "PUT",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

export { ApiError };

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

export type AutomationRun = {
  id?: number;
  kind?: string;
  source_ref?: string;
  status?: string;
  summary?: string;
  detail?: Record<string, unknown>;
  requires_human?: boolean;
  created_at?: string;
};

export type AutomationAlert = {
  id?: number;
  run_id?: number;
  severity?: string;
  code?: string;
  message?: string;
  fields?: string[];
  resolved?: boolean;
  created_at?: string;
};

export type AutomationResults = {
  ok?: boolean;
  db_path?: string;
  total_runs?: number;
  open_alerts?: number;
  recent_requires_human?: number;
  by_status?: Record<string, number>;
  by_kind?: Record<string, number>;
  runs?: AutomationRun[];
  alerts?: AutomationAlert[];
  rulesets?: Record<string, unknown>;
  integrations?: Record<string, unknown>;
};

export async function getAutomationResults(limit = 50): Promise<AutomationResults> {
  return autoGet<AutomationResults>(`/results?limit=${limit}`);
}

export async function getAutomationStatus(): Promise<Record<string, unknown>> {
  return autoGet("/status");
}

export async function resolveAutomationAlert(alertId: number | string): Promise<unknown> {
  return autoPost(`/alerts/${alertId}/resolve`, {});
}

export async function getRulesets(): Promise<{ ok?: boolean; rulesets?: Record<string, unknown> }> {
  return autoGet("/rulesets");
}

export async function putRulesets(
  data: Record<string, unknown>
): Promise<{ ok?: boolean; rulesets?: Record<string, unknown> }> {
  return autoPut("/rulesets", { data });
}

export async function emailToOrder(
  emailId: number | string,
  confirm = false
): Promise<Record<string, unknown>> {
  return autoPost(`/email/${emailId}/to-order`, { confirm });
}
