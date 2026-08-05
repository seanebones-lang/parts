'use client'

import { useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Truck, ExternalLink, Loader2 } from 'lucide-react'
import { API_BASE_URL, ApiError } from '@/lib/api'
import {
  buyShippingLabel,
  getShippingConfig,
  getShippingRates,
  isCommerceUnreachable,
  type ShipAddress,
} from '@/lib/commerce-api'

type RateRow = {
  id?: string
  carrier?: string
  service?: string
  rate?: number
  currency?: string
  delivery_days?: number | null
}

const emptyAddr = (): ShipAddress => ({
  name: '',
  street1: '',
  city: '',
  state: '',
  zip: '',
  country: 'US',
})

export default function ShippingInner() {
  const params = useSearchParams()
  const [configured, setConfigured] = useState(false)
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [rates, setRates] = useState<RateRow[]>([])
  const [shipmentId, setShipmentId] = useState<string>('')
  const [label, setLabel] = useState<Record<string, unknown> | null>(null)
  const [orderId, setOrderId] = useState(params.get('order_id') || '')

  const [from, setFrom] = useState<ShipAddress>({
    name: 'Parts Counter',
    street1: '100 Dealer Way',
    city: 'Chicago',
    state: 'IL',
    zip: '60601',
    country: 'US',
  })
  const [to, setTo] = useState<ShipAddress>({
    ...emptyAddr(),
    name: 'Customer',
    street1: params.get('street1') || '',
    city: params.get('city') || '',
    state: params.get('state') || '',
    zip: params.get('zip') || '',
  })
  const [weight, setWeight] = useState('16')

  useEffect(() => {
    ;(async () => {
      try {
        const data = await getShippingConfig()
        setConfigured(Boolean(data.configured || data.live_ready))
        setMessage(String(data.message || ''))
      } catch (e) {
        setConfigured(false)
        setMessage(
          isCommerceUnreachable(e)
            ? 'API unreachable — run ./scripts/demo_up.sh'
            : e instanceof Error
              ? e.message
              : 'Failed to load shipping config'
        )
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  // Prefill customer email/name notes from DMS order when order_id present
  useEffect(() => {
    const oid = params.get('order_id') || orderId
    if (!oid) return
    ;(async () => {
      try {
        const base =
          (typeof process !== 'undefined' && process.env?.NEXT_PUBLIC_API_URL) ||
          API_BASE_URL
        const res = await fetch(`${base}/api/v1/dms/orders/${encodeURIComponent(oid)}`)
        if (!res.ok) return
        const data = (await res.json()) as {
          order?: {
            customer_name?: string
            customer_email?: string
            customer_company?: string
            notes?: string
          }
        }
        const ord = data.order || (data as { customer_name?: string })
        const name =
          (ord as { customer_name?: string }).customer_name ||
          (ord as { customer_company?: string }).customer_company ||
          ''
        if (name) {
          setTo((prev) => ({
            ...prev,
            name: prev.name && prev.name !== 'Customer' ? prev.name : name,
          }))
        }
        // keep street empty — dealers type real ship-to; no invented address
      } catch {
        /* ignore */
      }
    })()
  }, [params, orderId])

  const live = configured

  const onRates = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    setLabel(null)
    setRates([])
    try {
      const res = await getShippingRates({
        from_address: from,
        to_address: to,
        parcel: { weight: Number(weight) || 16 },
        order_id: orderId || undefined,
      })
      setShipmentId(String(res.shipment_id || ''))
      const list = Array.isArray(res.rates) ? (res.rates as RateRow[]) : []
      setRates(list)
      if (!list.length) setError('No rates returned (check addresses / EasyPost account)')
    } catch (err) {
      if (err instanceof ApiError) {
        const detail =
          typeof err.body === 'object' && err.body && 'detail' in (err.body as object)
            ? String((err.body as { detail?: unknown }).detail)
            : err.message
        setError(detail || err.message)
      } else {
        setError(err instanceof Error ? err.message : 'Rate shop failed')
      }
    } finally {
      setBusy(false)
    }
  }

  const onBuy = async (rateId: string) => {
    if (!shipmentId || !rateId) return
    setBusy(true)
    setError(null)
    try {
      const res = await buyShippingLabel({
        shipment_id: shipmentId,
        rate_id: rateId,
        order_id: orderId || undefined,
      })
      setLabel(res)
    } catch (err) {
      if (err instanceof ApiError) {
        const detail =
          typeof err.body === 'object' && err.body && 'detail' in (err.body as object)
            ? String((err.body as { detail?: unknown }).detail)
            : err.message
        setError(detail || err.message)
      } else {
        setError(err instanceof Error ? err.message : 'Label buy failed')
      }
    } finally {
      setBusy(false)
    }
  }

  const field = (
    label: string,
    value: string,
    onChange: (v: string) => void,
    placeholder?: string
  ) => (
    <label className="text-sm">
      {label}
      <input
        className="mt-1 w-full rounded border px-2 py-1.5"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
      />
    </label>
  )

  return (
    <div className="container mx-auto max-w-3xl p-6">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Shipping</h1>
          <p className="text-muted-foreground">
            EasyPost rates + labels for fulfilled orders — live only with API key.
            Order ID links a DMS shipment ledger (no fake labels).
          </p>
        </div>
        {loading ? (
          <Loader2 className="h-5 w-5 animate-spin" />
        ) : (
          <Badge variant={live ? 'default' : 'secondary'} className={live ? 'bg-green-600' : ''}>
            {live ? 'EasyPost configured' : 'Keys required'}
          </Badge>
        )}
      </div>

      <Card className="mb-4">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Truck className="h-4 w-4" />
            EasyPost integration
          </CardTitle>
          <CardDescription>
            Set <code className="text-xs">EASYPOST_API_KEY</code>. Without keys the module stays
            idle — no fake labels.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>{message || '—'}</p>
          <Button asChild variant="outline" size="sm">
            <a href={`${API_BASE_URL}/docs`} target="_blank" rel="noreferrer">
              API docs <ExternalLink className="ml-1 h-3 w-3" />
            </a>
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Rate shop + buy label</CardTitle>
          <CardDescription>
            <code className="text-xs">POST /api/v1/shipping/rates</code> then{' '}
            <code className="text-xs">/label</code>
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={onRates}>
            <label className="text-sm block">
              Order ID (optional)
              <input
                className="mt-1 w-full rounded border px-2 py-1.5"
                value={orderId}
                onChange={(e) => setOrderId(e.target.value)}
              />
            </label>
            <div>
              <p className="mb-2 text-sm font-medium">From</p>
              <div className="grid gap-2 sm:grid-cols-2">
                {field('Street', from.street1, (v) => setFrom({ ...from, street1: v }))}
                {field('City', from.city, (v) => setFrom({ ...from, city: v }))}
                {field('State', from.state, (v) => setFrom({ ...from, state: v }))}
                {field('ZIP', from.zip, (v) => setFrom({ ...from, zip: v }))}
              </div>
            </div>
            <div>
              <p className="mb-2 text-sm font-medium">To</p>
              <div className="grid gap-2 sm:grid-cols-2">
                {field('Street', to.street1, (v) => setTo({ ...to, street1: v }), 'required')}
                {field('City', to.city, (v) => setTo({ ...to, city: v }))}
                {field('State', to.state, (v) => setTo({ ...to, state: v }))}
                {field('ZIP', to.zip, (v) => setTo({ ...to, zip: v }))}
              </div>
            </div>
            {field('Parcel weight (oz)', weight, setWeight, '16')}
            {error && <p className="text-sm text-red-600">{error}</p>}
            <Button type="submit" disabled={busy || !live} size="sm">
              {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              {live ? 'Get rates' : 'Configure EasyPost first'}
            </Button>
          </form>

          {rates.length > 0 && (
            <div className="mt-4 space-y-2">
              <p className="text-sm font-medium">Rates {shipmentId ? `(shipment ${shipmentId})` : ''}</p>
              <ul className="space-y-2">
                {rates.map((r) => (
                  <li
                    key={String(r.id)}
                    className="flex flex-wrap items-center justify-between gap-2 rounded border px-3 py-2 text-sm"
                  >
                    <span>
                      {r.carrier} {r.service} — {r.currency || 'USD'} {r.rate}
                      {r.delivery_days != null ? ` · ${r.delivery_days}d` : ''}
                    </span>
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      disabled={busy || !r.id}
                      onClick={() => void onBuy(String(r.id))}
                    >
                      Buy label
                    </Button>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {label && (
            <div className="mt-4 rounded border bg-muted/40 p-3 text-xs font-mono break-all space-y-1">
              <div>tracking: {String(label.tracking_code || '—')}</div>
              <div>
                label:{' '}
                {label.label_url ? (
                  <a className="underline" href={String(label.label_url)} target="_blank" rel="noreferrer">
                    {String(label.label_url)}
                  </a>
                ) : (
                  '—'
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
