'use client'

import { useCallback, useEffect, useState } from 'react'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { AlertCircle, Loader2, Package, RefreshCw, Upload } from 'lucide-react'
import {
  ApiError,
  importDmsCatalogCsv,
  isApiUnreachable,
  listDmsCatalog,
  type DmsCatalogPart,
  upsertDmsCatalog,
} from '@/lib/dms-api'

export default function CatalogPage() {
  const [parts, setParts] = useState<DmsCatalogPart[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [flash, setFlash] = useState<string | null>(null)
  const [q, setQ] = useState('')
  const [sku, setSku] = useState('')
  const [name, setName] = useState('')
  const [make, setMake] = useState('')
  const [listPrice, setListPrice] = useState('')
  const [csvText, setCsvText] = useState(
    'sku,name,make,list_price,CHI-N\nDEMO-SKU-1,Demo Brake Pad,Honda,49.99,5\n'
  )
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await listDmsCatalog(q || undefined)
      setParts(res.parts)
    } catch (e) {
      setParts([])
      setError(
        isApiUnreachable(e)
          ? 'API unreachable. Run ./scripts/demo_up.sh'
          : e instanceof Error
            ? e.message
            : 'Failed to load catalog'
      )
    } finally {
      setLoading(false)
    }
  }, [q])

  useEffect(() => {
    void load()
  }, [load])

  const onUpsert = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setFlash(null)
    setError(null)
    try {
      await upsertDmsCatalog({
        sku,
        name,
        make: make || undefined,
        list_price: listPrice ? Number(listPrice) : 0,
        location_qty: { 'CHI-N': 0 },
      })
      setFlash(`Saved ${sku}`)
      setSku('')
      setName('')
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  const onCsv = async () => {
    setBusy(true)
    setFlash(null)
    setError(null)
    try {
      const res = (await importDmsCatalogCsv(csvText)) as {
        upserted?: number
        errors?: string[]
      }
      setFlash(`Imported ${res.upserted ?? 0} rows`)
      if (res.errors?.length) setError(res.errors.join('; '))
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="container mx-auto max-w-6xl p-6 space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Package className="h-7 w-7" /> Catalog
          </h1>
          <p className="text-muted-foreground">
            SKU admin + CSV import into DMS (then reindex for AI search).
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
        </Button>
      </div>

      {error && (
        <div className="flex items-start gap-2 rounded border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          <AlertCircle className="h-4 w-4 mt-0.5" />
          <span>{error}</span>
        </div>
      )}
      {flash && (
        <div className="rounded border bg-muted/40 p-3 text-sm">{flash}</div>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Upsert SKU</CardTitle>
            <CardDescription>POST /api/v1/dms/catalog</CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-2" onSubmit={onUpsert}>
              <input
                className="w-full rounded border px-2 py-1.5 text-sm font-mono"
                placeholder="SKU"
                value={sku}
                onChange={(e) => setSku(e.target.value)}
                required
              />
              <input
                className="w-full rounded border px-2 py-1.5 text-sm"
                placeholder="Name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
              <div className="grid grid-cols-2 gap-2">
                <input
                  className="w-full rounded border px-2 py-1.5 text-sm"
                  placeholder="Make"
                  value={make}
                  onChange={(e) => setMake(e.target.value)}
                />
                <input
                  className="w-full rounded border px-2 py-1.5 text-sm"
                  placeholder="List price"
                  value={listPrice}
                  onChange={(e) => setListPrice(e.target.value)}
                />
              </div>
              <Button type="submit" size="sm" disabled={busy}>
                Save SKU
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Upload className="h-4 w-4" /> CSV import
            </CardTitle>
            <CardDescription>sku,name required; optional make,list_price,L1…</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <textarea
              className="w-full min-h-[140px] rounded border px-2 py-1.5 text-xs font-mono"
              value={csvText}
              onChange={(e) => setCsvText(e.target.value)}
            />
            <Button type="button" size="sm" disabled={busy} onClick={() => void onCsv()}>
              Import CSV
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-2">
          <div>
            <CardTitle className="text-base">Parts</CardTitle>
            <CardDescription>{parts.length} shown</CardDescription>
          </div>
          <input
            className="rounded border px-2 py-1 text-sm"
            placeholder="Search…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground py-8 justify-center">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading…
            </div>
          ) : parts.length === 0 ? (
            <p className="text-sm text-muted-foreground py-6 text-center">No parts. Seed or import CSV.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="py-2 pr-3">SKU</th>
                    <th className="py-2 pr-3">Name</th>
                    <th className="py-2 pr-3">Make</th>
                    <th className="py-2 text-right">Price</th>
                  </tr>
                </thead>
                <tbody>
                  {parts.slice(0, 200).map((p) => (
                    <tr key={String(p.sku)} className="border-b last:border-0">
                      <td className="py-2 pr-3 font-mono text-xs">{p.sku}</td>
                      <td className="py-2 pr-3">{p.name}</td>
                      <td className="py-2 pr-3">
                        <Badge variant="secondary">{p.make || '—'}</Badge>
                      </td>
                      <td className="py-2 text-right tabular-nums">
                        {p.list_price != null ? `$${Number(p.list_price).toFixed(2)}` : '—'}
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
  )
}
