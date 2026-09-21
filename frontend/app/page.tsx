import Link from 'next/link'
import { redirect } from 'next/navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { MapPin, Search, Shield, Database, Truck, Mail } from 'lucide-react'
import { isTransmissionDemo } from '@/lib/demo-vertical'

export default function HomePage() {
  // JP presentation mode: land on the transmission counter, not the generic dealership home.
  if (isTransmissionDemo()) {
    redirect('/transmission')
  }

  return (
    <div className="container mx-auto p-6">
      <div className="mb-6 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900">
        <strong className="font-semibold">Parts</strong> — dealership parts system: AI counter
        search, multi-location DMS, and OEM/distributor feed ingest. Configure production auth and
        feeds for live rooftops.
      </div>

      <div className="mb-10 grid gap-8 lg:grid-cols-2 lg:items-center">
        <div>
          <Badge className="mb-3" variant="secondary">
            NextEleven LLC
          </Badge>
          <h1 className="mb-3 text-4xl font-bold tracking-tight text-foreground">
            Parts operating system for multi-location dealers
          </h1>
          <p className="mb-6 text-lg text-muted-foreground">
            Inbound email auto-answer with green/yellow/red desk grades, counter lookup,
            inventory, customers, and orders — hybrid AI ranking so staff stay in control.
          </p>
          <div className="flex flex-wrap gap-3">
            <Button asChild size="lg">
              <Link href="/emails">
                <Mail className="mr-2 h-4 w-4" />
                Email Desk
              </Link>
            </Button>
            <Button asChild variant="outline" size="lg">
              <Link href="/parts">
                <Search className="mr-2 h-4 w-4" />
                Parts Search
              </Link>
            </Button>
            <Button asChild variant="outline" size="lg">
              <Link href="/inventory">
                <Database className="mr-2 h-4 w-4" />
                Inventory
              </Link>
            </Button>
            <Button asChild variant="outline" size="lg">
              <Link href="/orders">Orders</Link>
            </Button>
          </div>
        </div>

        <Card className="border-slate-200 shadow-sm">
          <CardHeader>
            <CardTitle className="text-base">Counter examples</CardTitle>
            <CardDescription>Works against your DMS/OEM catalog after feed sync</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {[
              'brake pads for 2019 Honda Civic',
              'oil filter Toyota Camry 2020',
              'spark plugs NGK Civic',
              'front rotors 2018 Ford F-150',
              'battery group 51R Honda',
            ].map((q) => (
              <Link
                key={q}
                href={`/parts?q=${encodeURIComponent(q)}`}
                className="block rounded-md border bg-muted/40 px-3 py-2 font-mono text-xs hover:bg-muted"
              >
                {q}
              </Link>
            ))}
          </CardContent>
        </Card>
      </div>

      <div className="mb-8 grid grid-cols-1 gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <MapPin className="mb-2 h-5 w-5 text-slate-700" />
            <CardTitle className="text-base">Multi-location DMS</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Catalog, stock by rooftop, customers, and orders with stock reserve.
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <Search className="mb-2 h-5 w-5 text-slate-700" />
            <CardTitle className="text-base">Hybrid AI retrieval</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Dense + keyword fusion (RRF) over the live DMS catalog after reindex.
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <Truck className="mb-2 h-5 w-5 text-slate-700" />
            <CardTitle className="text-base">OEM / distributor feeds</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            File drop or HTTP feed (`OEM_FEED_URL`). Fails closed if the feed is down.
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Shield className="h-4 w-4" />
            Production configuration
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-1 text-sm text-muted-foreground">
          <p>
            · Set <code className="text-xs">AUTH_MODE=production</code>, strong{' '}
            <code className="text-xs">SECRET_KEY</code>, <code className="text-xs">DEBUG=false</code>.
          </p>
          <p>
            · Load catalog via <code className="text-xs">parrts dms sync-oem</code> (file or HTTP).
          </p>
          <p>
            · Enable Stripe / EasyPost with keys when you turn on payments and shipping.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
