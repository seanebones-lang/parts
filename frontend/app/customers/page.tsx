"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  AlertCircle,
  Loader2,
  Plus,
  RefreshCw,
  Users,
} from "lucide-react";
import {
  type DmsCustomer,
  ApiError,
  isApiUnreachable,
  listDmsCustomers,
  createDmsCustomer,
} from "@/lib/dms-api";

function formatWhen(s?: string): string {
  if (!s) return "—";
  try {
    const d = new Date(s);
    if (Number.isNaN(d.getTime())) return s;
    return d.toLocaleString();
  } catch {
    return s;
  }
}

export default function CustomersPage() {
  const [customers, setCustomers] = useState<DmsCustomer[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [unreachable, setUnreachable] = useState(false);
  const [flash, setFlash] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [company, setCompany] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setUnreachable(false);
    try {
      const res = await listDmsCustomers();
      setCustomers(res.customers);
    } catch (e) {
      setCustomers([]);
      if (isApiUnreachable(e) || (e instanceof ApiError && e.status === 404)) {
        setUnreachable(true);
        setError(
          e instanceof ApiError && e.status === 404
            ? "DMS API not loaded yet (404). Run ./scripts/demo_up.sh after DMS backend is enabled."
            : "API unreachable. Run ./scripts/demo_up.sh"
        );
      } else {
        setError(e instanceof Error ? e.message : "Failed to load customers");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const onCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setFlash(null);
    setError(null);
    try {
      if (!name.trim()) throw new Error("Name is required");
      await createDmsCustomer({
        name: name.trim(),
        email: email.trim() || undefined,
        phone: phone.trim() || undefined,
        company: company.trim() || undefined,
      });
      setFlash("Customer created");
      setName("");
      setEmail("");
      setPhone("");
      setCompany("");
      await load();
    } catch (err) {
      if (isApiUnreachable(err)) {
        setUnreachable(true);
        setError("API unreachable. Run ./scripts/demo_up.sh");
      } else {
        setError(err instanceof Error ? err.message : "Create customer failed");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-950">
        <strong>DMS Core (local SQLite)</strong> — OEM live feed when configured.
        Customer master for pilot counter orders.
      </div>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Users className="h-6 w-6" />
            Customers
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            List and create via{" "}
            <code className="text-xs">/api/v1/dms/customers</code>
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          disabled={loading || submitting}
          onClick={() => void load()}
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin mr-1" />
          ) : (
            <RefreshCw className="h-4 w-4 mr-1" />
          )}
          Refresh
        </Button>
      </div>

      {flash ? (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900">
          {flash}
        </div>
      ) : null}

      {error ? (
        <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-3 text-sm text-amber-950 flex gap-2">
          <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
          <div className="space-y-1">
            <p>{error}</p>
            {unreachable ? (
              <p className="font-mono text-xs">./scripts/demo_up.sh</p>
            ) : null}
          </div>
        </div>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-5">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Plus className="h-4 w-4" />
              New customer
            </CardTitle>
            <CardDescription>Add a counter / wholesale account</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={onCreate} className="space-y-3">
              <label className="block space-y-1">
                <span className="text-xs font-medium text-muted-foreground">
                  Name *
                </span>
                <input
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Jane Counter"
                  required
                />
              </label>
              <label className="block space-y-1">
                <span className="text-xs font-medium text-muted-foreground">
                  Company
                </span>
                <input
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                  value={company}
                  onChange={(e) => setCompany(e.target.value)}
                  placeholder="Optional"
                />
              </label>
              <label className="block space-y-1">
                <span className="text-xs font-medium text-muted-foreground">
                  Email
                </span>
                <input
                  type="email"
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="optional@example.com"
                />
              </label>
              <label className="block space-y-1">
                <span className="text-xs font-medium text-muted-foreground">
                  Phone
                </span>
                <input
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="Optional"
                />
              </label>
              <Button
                type="submit"
                className="w-full"
                disabled={submitting || unreachable}
              >
                {submitting ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-1" />
                ) : (
                  <Plus className="h-4 w-4 mr-1" />
                )}
                Create customer
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle className="text-lg">Customers</CardTitle>
            <CardDescription>
              {loading
                ? "Loading…"
                : `${customers.length} customer${customers.length === 1 ? "" : "s"}`}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground py-8 justify-center">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading customers…
              </div>
            ) : customers.length === 0 ? (
              <div className="rounded-md border border-dashed p-8 text-center space-y-2">
                <p className="text-sm text-muted-foreground">
                  {unreachable
                    ? "No connection to DMS API."
                    : "No customers yet. Create one or seed DMS."}
                </p>
                <p className="text-xs text-muted-foreground font-mono">
                  ./scripts/demo_up.sh
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left text-muted-foreground">
                      <th className="py-2 pr-3 font-medium">ID</th>
                      <th className="py-2 pr-3 font-medium">Name</th>
                      <th className="py-2 pr-3 font-medium">Company</th>
                      <th className="py-2 pr-3 font-medium">Email</th>
                      <th className="py-2 pr-3 font-medium">Phone</th>
                      <th className="py-2 font-medium">Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {customers.map((c, i) => (
                      <tr
                        key={`${c.id ?? c.email ?? i}`}
                        className="border-b last:border-0"
                      >
                        <td className="py-2 pr-3 font-mono text-xs">
                          {c.id ?? "—"}
                        </td>
                        <td className="py-2 pr-3 font-medium">{c.name || "—"}</td>
                        <td className="py-2 pr-3 text-muted-foreground">
                          {c.company || "—"}
                        </td>
                        <td className="py-2 pr-3">{c.email || "—"}</td>
                        <td className="py-2 pr-3">{c.phone || "—"}</td>
                        <td className="py-2 text-muted-foreground text-xs">
                          {formatWhen(c.created_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
