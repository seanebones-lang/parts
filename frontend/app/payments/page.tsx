'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { CreditCard, ExternalLink, Loader2 } from 'lucide-react'
import { API_BASE_URL, getJson } from '@/lib/api'

type Integrations = {
  stripe_configured?: boolean
  easypost_configured?: boolean
  oem_feed_configured?: boolean
  auth_mode?: string
  [key: string]: unknown
}

export default function PaymentsPage() {
  const [info, setInfo] = useState<Integrations | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    ;(async () => {
      try {
        const data = await getJson<Integrations>('/api/v1/system/integrations')
        setInfo(data)
      } catch {
        try {
          const root = await getJson<Record<string, unknown>>('/')
          setInfo({
            auth_mode: String(root.auth_mode ?? ''),
            stripe_configured: false,
            easypost_configured: false,
          })
        } catch {
          setInfo(null)
        }
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const live = Boolean(info?.stripe_configured)

  return (
    <div className="container mx-auto max-w-3xl p-6">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Payments</h1>
          <p className="text-muted-foreground">
            Stripe payment intents and links — production module gated on API keys.
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

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <CreditCard className="h-4 w-4" />
            Stripe integration
          </CardTitle>
          <CardDescription>
            Set <code className="text-xs">STRIPE_SECRET_KEY</code> (and webhook secret) in the
            environment, then restart the API. Endpoints:{' '}
            <code className="text-xs">/api/v1/payments/*</code>
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          <p>
            When keys are present, create intents and payment links against invoices/orders from the
            DMS. Without keys the module stays idle — it does not fake card charges.
          </p>
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
    </div>
  )
}
