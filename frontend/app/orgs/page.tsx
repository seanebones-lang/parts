"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
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
  AlertCircle,
  Building2,
  Loader2,
  MapPin,
  RefreshCw,
  Shield,
} from "lucide-react";
import {
  type DmsLocation,
  type DmsOrg,
  ApiError,
  isApiUnreachable,
  listDmsOrgs,
  createDmsOrg,
  listDmsLocations,
  setDmsLocationOrg,
  getDmsAcl,
  setDmsAcl,
} from "@/lib/dms-api";

export default function OrgsPage() {
  const [orgs, setOrgs] = useState<DmsOrg[]>([]);
  const [locations, setLocations] = useState<DmsLocation[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [unreachable, setUnreachable] = useState(false);
  const [flash, setFlash] = useState<string | null>(null);

  const [orgCode, setOrgCode] = useState("");
  const [orgName, setOrgName] = useState("");

  const [locCode, setLocCode] = useState("");
  const [locOrgCode, setLocOrgCode] = useState("");

  const [aclUser, setAclUser] = useState("counter1");
  const [aclSelected, setAclSelected] = useState<string[]>([]);
  const [aclRestricted, setAclRestricted] = useState(false);

  const orgById = useMemo(() => {
    const m = new Map<string, DmsOrg>();
    for (const o of orgs) {
      if (o.id != null) m.set(String(o.id), o);
      if (o.code) m.set(String(o.code), o);
    }
    return m;
  }, [orgs]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setUnreachable(false);
    try {
      const [o, l] = await Promise.all([listDmsOrgs(), listDmsLocations()]);
      setOrgs(o.orgs);
      setLocations(l.locations);
      setLocCode((prev) => prev || (l.locations[0]?.code ? String(l.locations[0].code) : ""));
      setLocOrgCode((prev) => prev || (o.orgs[0]?.code ? String(o.orgs[0].code) : ""));
    } catch (e) {
      setOrgs([]);
      setLocations([]);
      if (isApiUnreachable(e) || (e instanceof ApiError && e.status === 404)) {
        setUnreachable(true);
        setError(
          e instanceof ApiError && e.status === 404
            ? "DMS API not loaded yet (404). Run ./scripts/demo_up.sh"
            : "API unreachable. Run ./scripts/demo_up.sh"
        );
      } else {
        setError(e instanceof Error ? e.message : "Failed to load orgs");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const loadAcl = async () => {
    setBusy("acl-load");
    setError(null);
    setFlash(null);
    try {
      if (!aclUser.trim()) throw new Error("user_key required");
      const acl = await getDmsAcl(aclUser.trim());
      setAclSelected(acl.location_codes ?? []);
      setAclRestricted(Boolean(acl.restricted));
      setFlash(
        acl.restricted
          ? `ACL for ${acl.user_key}: ${(acl.location_codes ?? []).join(", ") || "(empty)"}`
          : `ACL for ${acl.user_key}: unrestricted (all locations)`
      );
    } catch (e) {
      if (isApiUnreachable(e)) {
        setUnreachable(true);
        setError("API unreachable. Run ./scripts/demo_up.sh");
      } else {
        setError(e instanceof Error ? e.message : "Failed to load ACL");
      }
    } finally {
      setBusy(null);
    }
  };

  const onCreateOrg = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy("org");
    setFlash(null);
    setError(null);
    try {
      if (!orgCode.trim()) throw new Error("Org code required");
      await createDmsOrg({
        code: orgCode.trim().toUpperCase(),
        name: orgName.trim() || orgCode.trim().toUpperCase(),
      });
      setFlash(`Org ${orgCode.trim().toUpperCase()} saved`);
      setOrgCode("");
      setOrgName("");
      await load();
    } catch (err) {
      if (isApiUnreachable(err)) {
        setUnreachable(true);
        setError("API unreachable. Run ./scripts/demo_up.sh");
      } else {
        setError(err instanceof Error ? err.message : "Create org failed");
      }
    } finally {
      setBusy(null);
    }
  };

  const onAssignLoc = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy("loc");
    setFlash(null);
    setError(null);
    try {
      if (!locCode.trim() || !locOrgCode.trim()) {
        throw new Error("Location code and org code required");
      }
      await setDmsLocationOrg(locCode.trim(), locOrgCode.trim());
      setFlash(`Location ${locCode.trim()} → org ${locOrgCode.trim()}`);
      await load();
    } catch (err) {
      if (isApiUnreachable(err)) {
        setUnreachable(true);
        setError("API unreachable. Run ./scripts/demo_up.sh");
      } else {
        setError(err instanceof Error ? err.message : "Assign location failed");
      }
    } finally {
      setBusy(null);
    }
  };

  const onSaveAcl = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy("acl-save");
    setFlash(null);
    setError(null);
    try {
      if (!aclUser.trim()) throw new Error("user_key required");
      await setDmsAcl(aclUser.trim(), aclSelected);
      setAclRestricted(aclSelected.length > 0);
      setFlash(
        aclSelected.length
          ? `Saved ACL for ${aclUser.trim()}: ${aclSelected.join(", ")}`
          : `Cleared ACL for ${aclUser.trim()} (unrestricted)`
      );
    } catch (err) {
      if (isApiUnreachable(err)) {
        setUnreachable(true);
        setError("API unreachable. Run ./scripts/demo_up.sh");
      } else {
        setError(err instanceof Error ? err.message : "Save ACL failed");
      }
    } finally {
      setBusy(null);
    }
  };

  const toggleAclLoc = (code: string) => {
    setAclSelected((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    );
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="rounded-lg border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-950">
        <strong>Orgs &amp; location ACL</strong> — multi-rooftop foundation.
        Demo open desk uses admin role; production requires JWT with{" "}
        <code className="text-xs">orgs.manage</code> /{" "}
        <code className="text-xs">acl.manage</code>. Empty ACL = unrestricted.
      </div>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Building2 className="h-6 w-6" />
            Organizations
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Create orgs, assign locations, set inventory ACL by user_key
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          disabled={loading || !!busy}
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

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Create org</CardTitle>
            <CardDescription>POST /api/v1/dms/orgs</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={onCreateOrg} className="space-y-3">
              <div className="grid gap-2 sm:grid-cols-2">
                <label className="text-sm space-y-1">
                  <span className="text-muted-foreground">Code</span>
                  <input
                    className="w-full rounded-md border px-3 py-2 text-sm"
                    value={orgCode}
                    onChange={(e) => setOrgCode(e.target.value)}
                    placeholder="CHI"
                    disabled={!!busy || unreachable}
                  />
                </label>
                <label className="text-sm space-y-1">
                  <span className="text-muted-foreground">Name</span>
                  <input
                    className="w-full rounded-md border px-3 py-2 text-sm"
                    value={orgName}
                    onChange={(e) => setOrgName(e.target.value)}
                    placeholder="Chicago Group"
                    disabled={!!busy || unreachable}
                  />
                </label>
              </div>
              <Button type="submit" size="sm" disabled={!!busy || unreachable}>
                {busy === "org" ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-1" />
                ) : null}
                Save org
              </Button>
            </form>
            <div className="mt-4 space-y-2">
              <p className="text-xs font-medium text-muted-foreground">
                Orgs ({orgs.length})
              </p>
              {loading ? (
                <p className="text-sm text-muted-foreground">Loading…</p>
              ) : orgs.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No orgs yet. Create one or seed DMS first.
                </p>
              ) : (
                <ul className="space-y-1 text-sm">
                  {orgs.map((o) => (
                    <li
                      key={String(o.id ?? o.code)}
                      className="flex items-center gap-2 rounded border px-2 py-1.5"
                    >
                      <Badge variant="secondary">{o.code}</Badge>
                      <span>{o.name}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <MapPin className="h-4 w-4" />
              Assign location → org
            </CardTitle>
            <CardDescription>
              PUT /api/v1/dms/locations/{"{code}"}/org
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={onAssignLoc} className="space-y-3">
              <div className="grid gap-2 sm:grid-cols-2">
                <label className="text-sm space-y-1">
                  <span className="text-muted-foreground">Location</span>
                  <select
                    className="w-full rounded-md border px-3 py-2 text-sm bg-background"
                    value={locCode}
                    onChange={(e) => setLocCode(e.target.value)}
                    disabled={!!busy || unreachable || locations.length === 0}
                  >
                    {locations.length === 0 ? (
                      <option value="">No locations — seed DMS</option>
                    ) : (
                      locations.map((l) => (
                        <option key={String(l.id ?? l.code)} value={String(l.code)}>
                          {l.code}
                          {l.name ? ` — ${l.name}` : ""}
                        </option>
                      ))
                    )}
                  </select>
                </label>
                <label className="text-sm space-y-1">
                  <span className="text-muted-foreground">Org code</span>
                  <select
                    className="w-full rounded-md border px-3 py-2 text-sm bg-background"
                    value={locOrgCode}
                    onChange={(e) => setLocOrgCode(e.target.value)}
                    disabled={!!busy || unreachable || orgs.length === 0}
                  >
                    {orgs.length === 0 ? (
                      <option value="">Create an org first</option>
                    ) : (
                      orgs.map((o) => (
                        <option key={String(o.id ?? o.code)} value={String(o.code)}>
                          {o.code}
                          {o.name ? ` — ${o.name}` : ""}
                        </option>
                      ))
                    )}
                  </select>
                </label>
              </div>
              <Button
                type="submit"
                size="sm"
                disabled={!!busy || unreachable || !locations.length || !orgs.length}
              >
                {busy === "loc" ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-1" />
                ) : null}
                Assign
              </Button>
            </form>
            <div className="mt-4 space-y-2">
              <p className="text-xs font-medium text-muted-foreground">
                Locations ({locations.length})
              </p>
              {locations.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  Empty —{" "}
                  <Link href="/inventory" className="underline font-medium">
                    Seed DMS on Inventory
                  </Link>
                </p>
              ) : (
                <ul className="max-h-48 overflow-auto space-y-1 text-sm">
                  {locations.map((l) => {
                    const org =
                      l.org_id != null ? orgById.get(String(l.org_id)) : undefined;
                    return (
                      <li
                        key={String(l.id ?? l.code)}
                        className="flex flex-wrap items-center gap-2 rounded border px-2 py-1.5"
                      >
                        <span className="font-mono text-xs">{l.code}</span>
                        <span className="text-muted-foreground">{l.name}</span>
                        {org ? (
                          <Badge>{org.code}</Badge>
                        ) : (
                          <Badge variant="outline">no org</Badge>
                        )}
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Shield className="h-4 w-4" />
              User location ACL
            </CardTitle>
            <CardDescription>
              PUT /api/v1/dms/acl/{"{user_key}"} — empty selection clears ACL
              (unrestricted). Inventory accepts{" "}
              <code className="text-xs">user_key</code> or header{" "}
              <code className="text-xs">X-Parts-User</code>.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={onSaveAcl} className="space-y-4">
              <div className="flex flex-wrap items-end gap-2">
                <label className="text-sm space-y-1 min-w-[12rem] flex-1">
                  <span className="text-muted-foreground">user_key</span>
                  <input
                    className="w-full rounded-md border px-3 py-2 text-sm"
                    value={aclUser}
                    onChange={(e) => setAclUser(e.target.value)}
                    placeholder="counter1"
                    disabled={!!busy || unreachable}
                  />
                </label>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={!!busy || unreachable}
                  onClick={() => void loadAcl()}
                >
                  {busy === "acl-load" ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-1" />
                  ) : null}
                  Load ACL
                </Button>
                <Button type="submit" size="sm" disabled={!!busy || unreachable}>
                  {busy === "acl-save" ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-1" />
                  ) : null}
                  Save ACL
                </Button>
                <Badge variant={aclRestricted ? "default" : "outline"}>
                  {aclRestricted ? "restricted" : "unrestricted"}
                </Badge>
              </div>
              {locations.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No locations to assign. Seed DMS first.
                </p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {locations.map((l) => {
                    const code = String(l.code ?? "");
                    const on = aclSelected.includes(code);
                    return (
                      <button
                        key={code}
                        type="button"
                        onClick={() => toggleAclLoc(code)}
                        disabled={!!busy || unreachable}
                        className={
                          on
                            ? "rounded-md border border-sky-600 bg-sky-100 px-2 py-1 text-xs font-medium"
                            : "rounded-md border px-2 py-1 text-xs text-muted-foreground hover:bg-muted"
                        }
                      >
                        {code}
                      </button>
                    );
                  })}
                </div>
              )}
              <p className="text-xs text-muted-foreground">
                After save, open{" "}
                <Link href="/inventory" className="underline font-medium">
                  Inventory
                </Link>{" "}
                and filter by the same user_key.
              </p>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
