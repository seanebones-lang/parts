/**
 * Browser offline mutation queue for brief API outages.
 * Stores create-order / create-customer payloads in localStorage.
 * Never invents stock/charges — only replays user-authored mutations.
 */

export type OfflineMutation =
  | {
      id: string;
      kind: "create_order";
      path: "/api/v1/dms/orders";
      body: Record<string, unknown>;
      created_at: string;
      attempts: number;
      last_error?: string;
    }
  | {
      id: string;
      kind: "create_customer";
      path: "/api/v1/dms/customers";
      body: Record<string, unknown>;
      created_at: string;
      attempts: number;
      last_error?: string;
    };

const STORAGE_KEY = "parrts.offline_queue.v1";

function uid(): string {
  return `oq_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 9)}`;
}

export function loadOfflineQueue(): OfflineMutation[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (x) => x && typeof x === "object" && typeof (x as OfflineMutation).id === "string"
    ) as OfflineMutation[];
  } catch {
    return [];
  }
}

export function saveOfflineQueue(items: OfflineMutation[]): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(items.slice(0, 100)));
  } catch {
    /* quota — drop silently */
  }
}

export function enqueueOfflineMutation(
  item: Omit<OfflineMutation, "id" | "created_at" | "attempts"> & {
    id?: string;
    created_at?: string;
    attempts?: number;
  }
): OfflineMutation {
  const full = {
    ...item,
    id: item.id || uid(),
    created_at: item.created_at || new Date().toISOString(),
    attempts: item.attempts ?? 0,
  } as OfflineMutation;
  const q = loadOfflineQueue();
  q.push(full);
  saveOfflineQueue(q);
  return full;
}

export function removeOfflineMutation(id: string): void {
  saveOfflineQueue(loadOfflineQueue().filter((x) => x.id !== id));
}

export function clearOfflineQueue(): void {
  saveOfflineQueue([]);
}

export type FlushResult = {
  ok: boolean;
  flushed: number;
  remaining: number;
  errors: string[];
};

/** Replay queue against API base. Stops leaving failed items with last_error. */
export async function flushOfflineQueue(apiBase: string): Promise<FlushResult> {
  const base = apiBase.replace(/\/+$/, "");
  const q = loadOfflineQueue();
  if (!q.length) return { ok: true, flushed: 0, remaining: 0, errors: [] };

  const remaining: OfflineMutation[] = [];
  const errors: string[] = [];
  let flushed = 0;

  for (const item of q) {
    try {
      const res = await fetch(`${base}${item.path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(item.body),
      });
      if (!res.ok) {
        const text = await res.text().catch(() => "");
        const next = {
          ...item,
          attempts: item.attempts + 1,
          last_error: `HTTP ${res.status} ${text.slice(0, 120)}`,
        };
        remaining.push(next);
        errors.push(`${item.kind}: ${next.last_error}`);
        continue;
      }
      flushed += 1;
    } catch (e) {
      const msg = e instanceof Error ? e.message : "network";
      remaining.push({
        ...item,
        attempts: item.attempts + 1,
        last_error: msg,
      });
      errors.push(`${item.kind}: ${msg}`);
    }
  }

  saveOfflineQueue(remaining);
  return {
    ok: remaining.length === 0,
    flushed,
    remaining: remaining.length,
    errors,
  };
}

export function isBrowserOffline(): boolean {
  if (typeof navigator === "undefined") return false;
  return navigator.onLine === false;
}
