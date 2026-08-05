'use client'

import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { CreditCard, ExternalLink, Loader2 } from 'lucide-react'
import { API_BASE_URL, ApiError } from '@/lib/api'
import {
  createOrderPaymentIntent,
  getPaymentConfig,
  isCommerceUnreachable,
} from '@/lib/commerce-api'

export default function PaymentsInner() {
  const params = useSearchParams()
  const [configured, setConfigured] = useState(false)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<Record<string, unknown> | null>(null)
  const [message, setMessage] = useState('')

  const [amount, setAmount] = useState(params.get('amount') || '')
  const [orderId, setOrderId] = useState(params.get('order_id') || '')
  const [email, setEmail] = useState(params.get('email') || '')
  const [currency, setCurrency] = useState('usd')

  useEffect(() => {
    ;(async () => {
      try {
        const data = await getPaymentConfig()
        setConfigured(Boolean(data.configured || data.live_ready))
        setMessage(String(data.message || ''))
      } catch (e) {
        setConfigured(false)
        setMessage(
          isCommerceUnreachable(e)
            ? 'API unreachable — run ./scripts/demo_up.sh'
            : e instanceof Error
              ? e.message
              : 'Failed to load payment config'
        )
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  // Prefill amount from DMS order when order_id is in the query string
  useEffect(() => {
    const oid = params.get('order_id')
    if (!oid || amount) return
    ;(async () => {
      try {
        const base =
          (typeof process !== 'undefined' && process.env?.NEXT_PUBLIC_API_URL) ||
          API_BASE_URL
        const res = await fetch(`${base}/api/v1/dms/orders/${encodeURIComponent(oid)}`)
        if (!res.ok) return
        const data = (await res.json()) as {
          order?: { total?: number; customer_email?: string }
          total?: number
        }
        const ord = data.order || data
        const t = Number((ord as { total?: number }).total)
        if (Number.isFinite(t) && t > 0) setAmount(String(t.toFixed(2)))
        const em = (ord as { customer_email?: string }).customer_email
        if (em && !email) setEmail(em)
      } catch {
        /* ignore — user can type amount */
      }
    })()
  }, [params, amount, email])

  const live = configured

  const onCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    setResult(null)
    try {
      const amt = Number(amount)
      if (!Number.isFinite(amt) || amt <= 0) throw new Error('Enter a valid amount > 0')
      const res = await createOrderPaymentIntent({
        amount: amt,
        currency,
        order_id: orderId || undefined,
        customer_email: email || undefined,
      })
      setResult(res)
    } catch (err) {
      if (err instanceof ApiError) {
        const detail =
          typeof err.body === 'object' && err.body && 'detail' in (err.body as object)
            ? String((err.body as { detail?: unknown }).detail)
            : err.message
        setError(detail || err.message)
      } else {
        setError(err instanceof Error ? err.message : 'Payment intent failed')
      }
    } finally {
      setSubmitting(false)
    }
  }

  const intent = useMemo(() => {
    const pi = result?.payment_intent
    return pi && typeof pi === 'object' ? (pi as Record<string, unknown>) : null
  }, [result])

  return (
    <div className="container mx-auto max-w-3xl p-6">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Payments</h1>
          <p className="text-muted-foreground">
            Stripe PaymentIntents for DMS orders — live only when keys are set.
          </p>
        </div>
        {loading ? (
          <Loader2 className="h-5 w-5 animate-spin" />
        ) : (
          <Badge variant={live ? 'default' : 'secondary'} className={live ? 'bg-green-600' : ''}>
            {live ? 'Stripe configured' : 'Keys required'}
          </Badge>
        )}
      </div>

      <Card className="mb-4">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <CreditCard className="h-4 w-4" />
            Stripe integration
          </CardTitle>
          <CardDescription>
            Set <code className="text-xs">STRIPE_SECRET_KEY</code> (optional publishable + webhook
            secret). Without keys this module stays idle — no fake charges.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>{message || '—'}</p>
          <div className="flex flex-wrap gap-2">
            <Button asChild variant="outline" size="sm">
              <a href={`${API_BASE_URL}/docs`} target="_blank" rel="noreferrer">
                API docs <ExternalLink className="ml-1 h-3 w-3" />
              </a>
            </Button>
            <Button asChild variant="outline" size="sm">
              <a href="/orders">Orders</a>
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Create order payment intent</CardTitle>
          <CardDescription>
            Calls <code className="text-xs">POST /api/v1/payments/order-intent</code>. Requires
            Stripe key on the API.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-3" onSubmit={onCreate}>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="text-sm">
                Amount (USD)
                <input
                  className="mt-1 w-full rounded border px-2 py-1.5"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder="89.50"
                  required
                />
              </label>
              <label className="text-sm">
                Currency
                <input
                  className="mt-1 w-full rounded border px-2 py-1.5"
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value)}
                />
              </label>
              <label className="text-sm">
                Order ID
                <input
                  className="mt-1 w-full rounded border px-2 py-1.5"
                  value={orderId}
                  onChange={(e) => setOrderId(e.target.value)}
                  placeholder="DMS order id"
                />
              </label>
              <label className="text-sm">
                Customer email
                <input
                  className="mt-1 w-full rounded border px-2 py-1.5"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  type="email"
                  placeholder="optional"
                />
              </label>
            </div>
            {error && <p className="text-sm text-red-600">{error}</p>}
            {intent && (
              <div className="rounded border bg-muted/40 p-3 text-xs font-mono break-all">
                <div>id: {String(intent.id)}</div>
                <div>status: {String(intent.status)}</div>
                <div>client_secret: {String(intent.client_secret)}</div>
              </div>
            )}
            <Button type="submit" disabled={submitting || !live} size="sm">
              {submitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              {live ? 'Create PaymentIntent' : 'Configure Stripe first'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
