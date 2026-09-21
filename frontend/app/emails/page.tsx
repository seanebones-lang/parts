"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Loader2,
  Mail,
  RefreshCw,
  Search,
  AlertCircle,
  Sparkles,
} from "lucide-react";
import {
  type DeskEmail,
  type EmailStatus,
  getEmailStatus,
  isEmailApiUnreachable,
  listEmails,
  overrideEmail,
  processEmails,
  seedEmails,
  sendEmail,
  trafficColor,
} from "@/lib/email-api";
import { emailToOrder } from "@/lib/automation-api";
import { isTransmissionDemo } from "@/lib/demo-vertical";
import { EmptyState, Panel } from "@/components/jp/ui";
import {
  inquiryCategoryLabel,
  trafficBadgeClass,
  trafficCountClass,
  trafficDotClass,
  trafficLabel,
} from "@/lib/ops-language";
import { cn } from "@/lib/utils";

function preview(text?: string, n = 160): string {
  const t = (text || "").replace(/\s+/g, " ").trim();
  if (t.length <= n) return t;
  return t.slice(0, n) + "…";
}

function extractRequest(e: DeskEmail): string {
  const ex = e.extracted;
  if (ex && typeof ex === "object") {
    const parts = (ex as { parts_requested?: unknown }).parts_requested;
    if (Array.isArray(parts) && parts.length) return parts.map(String).join(", ");
    const q = (ex as { query?: unknown }).query;
    if (typeof q === "string" && q.trim()) return q;
    const summary = (ex as { summary?: unknown }).summary;
    if (typeof summary === "string" && summary.trim()) return summary;
  }
  return preview(e.body_text, 120) || "—";
}

function matchedPart(e: DeskEmail): string {
  const hits = e.hits;
  if (Array.isArray(hits) && hits.length) {
    const first = hits[0];
    if (first && typeof first === "object") {
      const sku = (first as { sku?: string }).sku;
      if (sku) return sku;
    }
    return String(hits[0]);
  }
  const ex = e.extracted;
  if (ex && typeof ex === "object") {
    const sku = (ex as { sku?: string }).sku;
    if (sku) return sku;
  }
  return "—";
}

function TrafficPill({ color }: { color: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-semibold",
        trafficBadgeClass(color)
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full bg-white/90", color === "yellow" && "bg-amber-950/70")} />
      {trafficLabel(color)}
    </span>
  );
}

export default function EmailsPage() {
  const jp = isTransmissionDemo();
  const [emails, setEmails] = useState<DeskEmail[]>([]);
  const [status, setStatus] = useState<EmailStatus | null>(null);
  const [selected, setSelected] = useState<DeskEmail | null>(null);
  const [q, setQ] = useState("");
  const [colorFilter, setColorFilter] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [apiDown, setApiDown] = useState(false);
  const [techOpen, setTechOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      const [st, lst] = await Promise.all([
        getEmailStatus(),
        listEmails({
          q: q.trim() || undefined,
          traffic_light: colorFilter || undefined,
          limit: 100,
        }),
      ]);
      setStatus(st);
      setEmails(lst.emails || []);
      setApiDown(false);
      if (selected?.id) {
        const match = (lst.emails || []).find((e) => e.id === selected.id);
        if (match) setSelected(match);
      }
    } catch (e) {
      if (isEmailApiUnreachable(e)) {
        setApiDown(true);
        setErr("API unreachable — start the demo stack");
      } else {
        setErr(e instanceof Error ? e.message : String(e));
      }
    } finally {
      setLoading(false);
    }
  }, [q, colorFilter, selected?.id]);

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const counts = useMemo(() => status?.by_traffic_light || {}, [status]);

  const sorted = useMemo(() => {
    const rank = (c: string) =>
      c === "red" ? 0 : c === "yellow" ? 1 : c === "green" ? 2 : 3;
    return [...emails].sort(
      (a, b) => rank(trafficColor(a)) - rank(trafficColor(b))
    );
  }, [emails]);

  const onSeed = async () => {
    setLoading(true);
    setErr(null);
    try {
      await seedEmails({
        clear: true,
        process: true,
        vertical: jp ? "transmission" : undefined,
      });
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  const onProcess = async () => {
    setLoading(true);
    setErr(null);
    try {
      await processEmails({ limit: 50 });
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  const onOverride = async (color: "green" | "yellow" | "red") => {
    if (!selected?.id) return;
    setLoading(true);
    try {
      await overrideEmail(selected.id, color);
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  const onApprove = async (dryRun: boolean) => {
    if (!selected?.id) return;
    setLoading(true);
    try {
      await sendEmail(selected.id, {
        body: selected.suggested_response || undefined,
        dry_run: dryRun,
        force: true,
      });
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  const onEmailToOrder = async (confirm: boolean) => {
    if (!selected?.id) return;
    setLoading(true);
    try {
      const res = await emailToOrder(selected.id, confirm);
      const msg = confirm
        ? String((res as { message?: string }).message || "Order created")
        : String((res as { message?: string }).message || "Draft preview ready");
      window.alert(msg);
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  const shellClass = jp
    ? "mx-auto w-full max-w-6xl px-6 py-5"
    : "mx-auto flex max-w-6xl flex-col gap-6 p-6";

  return (
    <div className={shellClass}>
      <div className="mb-4 flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-2">
          {!jp ? <Mail className="h-6 w-6" /> : null}
          <h1
            className={
              jp
                ? "text-xl font-semibold tracking-tight text-slate-900"
                : "text-2xl font-bold tracking-tight"
            }
          >
            Email Desk
          </h1>
        </div>
        <p className="max-w-3xl text-sm text-slate-500">
          {jp
            ? "Customer inquiry → identify request → check inventory → prepare response → human review when needed."
            : "Inbound parts questions graded green (handled) / yellow (review) / red (urgent)."}
        </p>
      </div>

      <div className="mb-4 grid gap-3 sm:grid-cols-4">
        {[
          { label: "Total", value: status?.total ?? "—", className: "text-slate-900" },
          {
            label: "Handled",
            value: counts.green ?? 0,
            className: trafficCountClass("green"),
          },
          {
            label: "Needs review",
            value: counts.yellow ?? 0,
            className: trafficCountClass("yellow"),
          },
          {
            label: "Urgent",
            value: counts.red ?? 0,
            className: trafficCountClass("red"),
          },
        ].map((s) => (
          <div
            key={s.label}
            className="rounded-lg border border-slate-200 bg-white px-4 py-3 shadow-sm"
          >
            <div className="text-[11px] font-medium uppercase tracking-wide text-slate-500">
              {s.label}
            </div>
            <div className={cn("mt-1 text-2xl font-semibold tabular-nums", s.className)}>
              {s.value}
            </div>
          </div>
        ))}
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <div className="relative min-w-[200px] flex-1">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-slate-400" />
          <input
            className="w-full rounded-md border border-slate-300 bg-white py-2 pl-8 pr-3 text-sm"
            placeholder="Search subject, body, sender…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void load();
            }}
          />
        </div>
        <select
          className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
          value={colorFilter}
          onChange={(e) => setColorFilter(e.target.value)}
        >
          <option value="">All statuses</option>
          <option value="green">Handled (green)</option>
          <option value="yellow">Needs review (yellow)</option>
          <option value="red">Urgent (red)</option>
        </select>
        <Button variant="secondary" size="sm" onClick={() => void load()} disabled={loading}>
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
          <span className="ml-1">Refresh</span>
        </Button>
        <Button size="sm" onClick={() => void onSeed()} disabled={loading}>
          <Sparkles className="mr-1 h-4 w-4" />
          {jp ? "Seed transmission demo" : "Seed demo"}
        </Button>
        <Button variant="outline" size="sm" onClick={() => void onProcess()} disabled={loading}>
          Process queue
        </Button>
      </div>

      {err && (
        <div className="mb-4 flex items-start gap-2 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-900">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <div className="font-medium">{err}</div>
            {apiDown && (
              <div className="text-red-800/80">Start API, then refresh this page.</div>
            )}
          </div>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-5">
        <Panel
          className="lg:col-span-2"
          title="Queue"
          right={
            <span className="text-[11px] text-slate-400">Urgent → review → handled</span>
          }
        >
          <div className="max-h-[560px] space-y-2 overflow-y-auto">
            {sorted.length === 0 && !loading && (
              <EmptyState
                title="No emails yet"
                body={
                  jp
                    ? "Click Seed transmission demo to load JP hard-parts inquiries."
                    : "Click Seed demo to load sample inbound parts mail."
                }
              />
            )}
            {sorted.map((e) => {
              const c = trafficColor(e);
              const active = selected?.id === e.id;
              const cat = inquiryCategoryLabel(e.email_type || e.specialist);
              return (
                <button
                  key={e.id ?? e.message_id}
                  type="button"
                  onClick={() => {
                    setSelected(e);
                    setTechOpen(false);
                  }}
                  className={cn(
                    "w-full rounded-md border p-3 text-left transition-colors hover:bg-slate-50",
                    active ? "border-slate-400 bg-slate-50" : "border-slate-200 bg-white"
                  )}
                >
                  <div className="mb-1.5 flex flex-wrap items-center gap-2">
                    <span className={cn("h-2.5 w-2.5 rounded-full", trafficDotClass(c))} />
                    <TrafficPill color={c} />
                    <span className="text-[11px] font-medium text-slate-500">{cat}</span>
                  </div>
                  <div className="line-clamp-1 text-sm font-medium text-slate-900">
                    {e.subject || "(no subject)"}
                  </div>
                  <div className="mt-0.5 text-xs text-slate-500">
                    {e.sender_name || e.sender_email || "—"}
                    {e.received_at
                      ? ` · ${new Date(e.received_at).toLocaleString()}`
                      : ""}
                  </div>
                  <div className="mt-1 line-clamp-2 text-xs text-slate-600">
                    {extractRequest(e)}
                  </div>
                </button>
              );
            })}
          </div>
        </Panel>

        <Panel
          className="lg:col-span-3"
          title="Inquiry detail"
          right={
            selected ? (
              <TrafficPill color={trafficColor(selected)} />
            ) : null
          }
        >
          {!selected ? (
            <EmptyState
              title="Select an inquiry"
              body={
                jp
                  ? "Workflow: identify the parts request, check inventory evidence, prepare a response, then review when needed."
                  : "Select a queue item to view the suggested reply."
              }
            />
          ) : (
            <div className="space-y-4 text-sm">
              <div>
                <div className="text-lg font-semibold text-slate-900">{selected.subject}</div>
                <div className="mt-1 text-xs text-slate-500">
                  {selected.sender_name || "Customer"}
                  {selected.sender_email ? ` · ${selected.sender_email}` : ""}
                  {selected.received_at
                    ? ` · ${new Date(selected.received_at).toLocaleString()}`
                    : ""}
                </div>
                <div className="mt-2 flex flex-wrap gap-2">
                  <span className="rounded border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] font-medium text-slate-700">
                    {inquiryCategoryLabel(selected.email_type || selected.specialist)}
                  </span>
                  {selected.requires_human ? (
                    <span className="rounded bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-950">
                      Human review required
                    </span>
                  ) : (
                    <span className="rounded bg-emerald-100 px-2 py-0.5 text-[11px] font-semibold text-emerald-900">
                      No immediate intervention
                    </span>
                  )}
                </div>
              </div>

              <section>
                <h3 className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                  Customer inquiry
                </h3>
                <pre className="whitespace-pre-wrap rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-800">
                  {selected.body_text || "—"}
                </pre>
              </section>

              <section className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-md border border-slate-200 p-3">
                  <h3 className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                    Extracted request
                  </h3>
                  <p className="mt-1 text-sm text-slate-800">{extractRequest(selected)}</p>
                </div>
                <div className="rounded-md border border-slate-200 p-3">
                  <h3 className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                    Matched part / candidate
                  </h3>
                  <p className="mt-1 font-mono text-sm text-slate-800">{matchedPart(selected)}</p>
                </div>
              </section>

              <section className="rounded-md border border-slate-200 p-3">
                <h3 className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                  Inventory / review state
                </h3>
                <p className="mt-1 text-sm text-slate-800">
                  {selected.requires_human
                    ? "Needs counter or manager confirmation before treating as complete."
                    : "System marked this inquiry as handled. Confirm stock on the counter if fulfilling today."}
                </p>
                {typeof selected.traffic_light === "object" &&
                selected.traffic_light?.reason ? (
                  <p className="mt-1 text-xs text-slate-500">{selected.traffic_light.reason}</p>
                ) : null}
              </section>

              <section>
                <h3 className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                  Suggested response
                </h3>
                <pre className="whitespace-pre-wrap rounded-md border border-emerald-200 bg-emerald-50/60 p-3 text-sm text-slate-800">
                  {selected.suggested_response ||
                    "(none yet — run Process queue after seeding)"}
                </pre>
              </section>

              {Array.isArray(selected.actions) && selected.actions.length > 0 ? (
                <section>
                  <h3 className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                    Available actions
                  </h3>
                  <ul className="list-inside list-disc text-sm text-slate-700">
                    {selected.actions.map((a, i) => (
                      <li key={i}>{a}</li>
                    ))}
                  </ul>
                </section>
              ) : null}

              <div className="flex flex-wrap gap-2 border-t border-slate-100 pt-3">
                <Button size="sm" onClick={() => void onApprove(true)} disabled={loading}>
                  Mark sent (record)
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => void onApprove(false)}
                  disabled={loading}
                >
                  Send via SMTP
                </Button>
                {!jp ? (
                  <>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => void onEmailToOrder(false)}
                      disabled={loading}
                    >
                      Draft order
                    </Button>
                    <Button
                      size="sm"
                      onClick={() => void onEmailToOrder(true)}
                      disabled={loading}
                    >
                      Confirm → order
                    </Button>
                  </>
                ) : null}
                <Button
                  size="sm"
                  className="bg-emerald-600 text-white hover:bg-emerald-700"
                  onClick={() => void onOverride("green")}
                  disabled={loading}
                >
                  Mark handled
                </Button>
                <Button
                  size="sm"
                  className="bg-amber-400 text-amber-950 hover:bg-amber-500"
                  onClick={() => void onOverride("yellow")}
                  disabled={loading}
                >
                  Mark needs review
                </Button>
                <Button
                  size="sm"
                  className="bg-red-600 text-white hover:bg-red-700"
                  onClick={() => void onOverride("red")}
                  disabled={loading}
                >
                  Mark urgent
                </Button>
              </div>

              <button
                type="button"
                className="text-xs font-medium text-slate-500 hover:underline"
                onClick={() => setTechOpen((v) => !v)}
              >
                {techOpen ? "Hide technical classification" : "Show technical classification"}
              </button>
              {techOpen ? (
                <pre className="overflow-x-auto rounded bg-slate-950 p-3 text-[10px] text-slate-200">
                  {JSON.stringify(
                    {
                      email_type: selected.email_type,
                      specialist: selected.specialist,
                      department: selected.department,
                      status: selected.status,
                      priority: selected.priority,
                      traffic_light: selected.traffic_light,
                      classification_confidence: selected.classification_confidence,
                    },
                    null,
                    2
                  )}
                </pre>
              ) : null}
            </div>
          )}
        </Panel>
      </div>
    </div>
  );
}
