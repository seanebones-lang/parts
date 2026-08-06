"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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

function tlBadge(
  color: string
): "default" | "secondary" | "destructive" | "outline" {
  if (color === "green") return "default";
  if (color === "yellow") return "secondary";
  if (color === "red") return "destructive";
  return "outline";
}

function tlLabel(color: string): string {
  if (color === "green") return "GREEN · handled";
  if (color === "yellow") return "YELLOW · review";
  if (color === "red") return "RED · urgent";
  return "UNGRADED";
}

function preview(text?: string, n = 140): string {
  const t = (text || "").replace(/\s+/g, " ").trim();
  if (t.length <= n) return t;
  return t.slice(0, n) + "…";
}

export default function EmailsPage() {
  const [emails, setEmails] = useState<DeskEmail[]>([]);
  const [status, setStatus] = useState<EmailStatus | null>(null);
  const [selected, setSelected] = useState<DeskEmail | null>(null);
  const [q, setQ] = useState("");
  const [colorFilter, setColorFilter] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [apiDown, setApiDown] = useState(false);

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
        setErr("API unreachable — run ./scripts/demo_up.sh");
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

  const onSeed = async () => {
    setLoading(true);
    setErr(null);
    try {
      await seedEmails({ clear: true, process: true });
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
      await processEmails({ limit: 100 });
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
    setErr(null);
    try {
      const res = await sendEmail(Number(selected.id), { dry_run: dryRun });
      setSelected(res.email);
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
    setErr(null);
    try {
      const res = await overrideEmail(Number(selected.id), color);
      setSelected(res.email);
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
    setErr(null);
    try {
      const res = await emailToOrder(Number(selected.id), confirm);
      const msg = confirm
        ? String(res.message || `Order created`)
        : String(res.message || "Draft preview ready — confirm to reserve stock");
      setErr(null);
      // surface result in err slot as info when not error — use alert-like via status
      window.alert(msg + (res.order ? ` #${(res.order as { id?: number }).id}` : ""));
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 p-6">
      <div className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <Mail className="h-6 w-6" />
          <h1 className="text-2xl font-bold tracking-tight">Email Desk</h1>
          <Badge variant="default">Live · selling point</Badge>
        </div>
        <p className="max-w-3xl text-sm text-muted-foreground">
          Inbound parts questions are classified, answered by section specialists,
          and graded{" "}
          <span className="font-medium text-emerald-600">green</span> (handled) /{" "}
          <span className="font-medium text-amber-600">yellow</span> (review) /{" "}
          <span className="font-medium text-red-600">red</span> (urgent). Full-text
          searchable archive for the team.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total</CardDescription>
            <CardTitle className="text-2xl">{status?.total ?? "—"}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Green</CardDescription>
            <CardTitle className="text-2xl text-emerald-600">
              {counts.green ?? 0}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Yellow</CardDescription>
            <CardTitle className="text-2xl text-amber-600">
              {counts.yellow ?? 0}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Red / needs human</CardDescription>
            <CardTitle className="text-2xl text-red-600">
              {counts.red ?? 0}
              {status?.requires_human != null
                ? ` · ${status.requires_human} queue`
                : ""}
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <div className="relative min-w-[220px] flex-1">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            className="w-full rounded-md border bg-background py-2 pl-8 pr-3 text-sm"
            placeholder="Search subject, body, sender, reply…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void load();
            }}
          />
        </div>
        <select
          className="rounded-md border bg-background px-3 py-2 text-sm"
          value={colorFilter}
          onChange={(e) => setColorFilter(e.target.value)}
        >
          <option value="">All colors</option>
          <option value="green">Green</option>
          <option value="yellow">Yellow</option>
          <option value="red">Red</option>
        </select>
        <Button variant="secondary" size="sm" onClick={() => void load()} disabled={loading}>
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
          <span className="ml-1">Refresh</span>
        </Button>
        <Button size="sm" onClick={() => void onSeed()} disabled={loading}>
          <Sparkles className="mr-1 h-4 w-4" />
          Seed demo
        </Button>
        <Button variant="outline" size="sm" onClick={() => void onProcess()} disabled={loading}>
          Process queue
        </Button>
      </div>

      {err && (
        <div className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <div className="font-medium">{err}</div>
            {apiDown && (
              <div className="text-muted-foreground">
                Then open this page again — desk uses offline SQLite under .parrts/emails.db
              </div>
            )}
          </div>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-5">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Queue</CardTitle>
            <CardDescription>
              Sorted red → yellow → green. Click a row for specialist reply.
            </CardDescription>
          </CardHeader>
          <CardContent className="max-h-[560px] space-y-2 overflow-y-auto">
            {emails.length === 0 && !loading && (
              <p className="text-sm text-muted-foreground">
                No emails yet. Click <strong>Seed demo</strong> to load sample inbound parts mail.
              </p>
            )}
            {emails.map((e) => {
              const c = trafficColor(e);
              const active = selected?.id === e.id;
              return (
                <button
                  key={e.id ?? e.message_id}
                  type="button"
                  onClick={() => setSelected(e)}
                  className={`w-full rounded-md border p-3 text-left transition-colors hover:bg-muted/50 ${
                    active ? "border-foreground bg-muted/40" : ""
                  }`}
                >
                  <div className="mb-1 flex flex-wrap items-center gap-2">
                    <Badge variant={tlBadge(c)}>{tlLabel(c)}</Badge>
                    {e.specialist && (
                      <span className="text-xs text-muted-foreground">{e.specialist}</span>
                    )}
                    {e.priority === "urgent" && (
                      <Badge variant="destructive">urgent</Badge>
                    )}
                  </div>
                  <div className="line-clamp-1 text-sm font-medium">{e.subject || "(no subject)"}</div>
                  <div className="text-xs text-muted-foreground">
                    {e.sender_name || e.sender_email} · {e.email_type || "—"}
                  </div>
                </button>
              );
            })}
          </CardContent>
        </Card>

        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle className="text-base">Detail + suggested reply</CardTitle>
            <CardDescription>
              {selected
                ? `${selected.sender_email || ""} · ${selected.status || ""}`
                : "Select an email"}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {!selected && (
              <p className="text-sm text-muted-foreground">
                Specialists: parts_quote, parts_order, inventory, shipping, payment,
                complaint, customer_service, general — each owns its section.
              </p>
            )}
            {selected && (
              <>
                <div>
                  <div className="text-lg font-semibold">{selected.subject}</div>
                  <div className="mt-1 flex flex-wrap gap-2">
                    <Badge variant={tlBadge(trafficColor(selected))}>
                      {tlLabel(trafficColor(selected))}
                    </Badge>
                    {selected.email_type && <Badge variant="outline">{selected.email_type}</Badge>}
                    {selected.department && (
                      <Badge variant="outline">dept {selected.department}</Badge>
                    )}
                    {selected.requires_human ? (
                      <Badge variant="secondary">human required</Badge>
                    ) : (
                      <Badge variant="default">auto-handled</Badge>
                    )}
                  </div>
                  {typeof selected.traffic_light === "object" &&
                    selected.traffic_light?.reason && (
                      <p className="mt-2 text-sm text-muted-foreground">
                        {selected.traffic_light.reason}
                      </p>
                    )}
                </div>
                <div>
                  <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Inbound
                  </h3>
                  <pre className="whitespace-pre-wrap rounded-md border bg-muted/30 p-3 text-sm">
                    {selected.body_text || preview(String(selected.body_text || ""))}
                  </pre>
                </div>
                <div>
                  <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Suggested response ({selected.specialist || "—"})
                  </h3>
                  <pre className="whitespace-pre-wrap rounded-md border border-emerald-500/30 bg-emerald-500/5 p-3 text-sm">
                    {selected.suggested_response || "(none yet — run Process queue)"}
                  </pre>
                </div>
                {Array.isArray(selected.actions) && selected.actions.length > 0 && (
                  <div>
                    <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      Actions
                    </h3>
                    <ul className="list-inside list-disc text-sm">
                      {selected.actions.map((a, i) => (
                        <li key={i}>{a}</li>
                      ))}
                    </ul>
                  </div>
                )}
                <div className="flex flex-wrap gap-2 border-t pt-3">
                  <Button size="sm" onClick={() => void onApprove(true)} disabled={loading}>
                    Approve (mark sent)
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => void onApprove(false)}
                    disabled={loading}
                  >
                    Send via SMTP
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => void onEmailToOrder(false)}
                    disabled={loading}
                  >
                    Draft order (HIL)
                  </Button>
                  <Button
                    size="sm"
                    variant="default"
                    onClick={() => void onEmailToOrder(true)}
                    disabled={loading}
                  >
                    Confirm → order
                  </Button>
                  <Button size="sm" variant="secondary" onClick={() => void onOverride("green")} disabled={loading}>
                    Override green
                  </Button>
                  <Button size="sm" variant="secondary" onClick={() => void onOverride("yellow")} disabled={loading}>
                    Override yellow
                  </Button>
                  <Button size="sm" variant="destructive" onClick={() => void onOverride("red")} disabled={loading}>
                    Override red
                  </Button>
                </div>
                {status?.mailbox && (
                  <p className="text-xs text-muted-foreground">
                    Mailbox: IMAP{" "}
                    {(status.mailbox as { imap_configured?: boolean }).imap_configured
                      ? "configured"
                      : "off"}{" "}
                    · SMTP{" "}
                    {(status.mailbox as { smtp_configured?: boolean }).smtp_configured
                      ? "configured"
                      : "off"}{" "}
                    · auto_send{" "}
                    {String((status.mailbox as { auto_send?: boolean }).auto_send ?? false)}
                  </p>
                )}
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
