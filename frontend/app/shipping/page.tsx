'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Truck, ExternalLink, Loader2 } from 'lucide-react'
import { API_BASE_URL, getJson } from '@/lib/api'

type Integrations = {
  easypost_configured?: boolean
  stripe_configured?: boolean
  [key: string]: unknown
}

export default function ShippingPage() {
  const [info, setInfo] = useState<Integrations | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    ;(async () => {
      try {
        const data = await getJson<Integrations>('/api/v1/system/integrations')
        setInfo(data)
      } catch {
        setInfo(null)
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const live = Boolean(info?.easypost_configured)

  return (
    <div className="container mx-auto max-w-3xl p-6">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Shipping</h1>
          <p className="text-muted-foreground">
            Labels and rates via EasyPost — production module gated on API keys.
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

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Truck className="h-4 w-4" />
            EasyPost integration
          </CardTitle>
          <CardDescription>
            Set <code className="text-xs">EASYPOST_API_KEY</code> and restart the API. Carrier
            services use the shipping coordinator and shipping service modules.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          <p>
            Without keys the module stays idle — no fake labels. With keys, rate shops and labels
            attach to fulfilled DMS orders.
          </p>
          <Button asChild variant="outline" size="sm">
            <a href={`${API_BASE_URL}/docs`} target="_blank" rel="noreferrer">
              API docs <ExternalLink className="ml-1 h-3 w-3" />
            </a>
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
