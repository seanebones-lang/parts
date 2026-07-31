import Link from 'next/link'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { MapPin, Search, Shield, Zap } from 'lucide-react'

export default function HomePage() {
  return (
    <div className="container mx-auto p-6">
      <div className="mb-6 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
        <strong className="font-semibold">Design-partner pilot.</strong> Live demo path is{' '}
        <Link href="/parts" className="font-semibold underline underline-offset-2">
          Parts Search
        </Link>
        — natural language lookup across locations with green / yellow / red confidence.
        Other menu items are <em>roadmap previews</em>, not live DMS data.
      </div>

      <div className="mb-10 grid gap-8 lg:grid-cols-2 lg:items-center">
        <div>
          <Badge className="mb-3" variant="secondary">
            NextEleven LLC
          </Badge>
          <h1 className="mb-3 text-4xl font-bold tracking-tight text-foreground">
            Counter-ready parts search for multi-location dealers
          </h1>
          <p className="mb-6 text-lg text-muted-foreground">
            Staff type what the customer says. The system ranks SKUs across your
            rooftops and lights confidence so a human stays in control.
          </p>
          <div className="flex flex-wrap gap-3">
            <Button asChild size="lg">
              <Link href="/parts">
                <Search className="mr-2 h-4 w-4" />
                Open Parts Search
              </Link>
            </Button>
            <Button asChild variant="outline" size="lg">
              <a href="http://127.0.0.1:8000/demo/scenarios" target="_blank" rel="noreferrer">
                Demo scenarios API
              </a>
            </Button>
          </div>
        </div>

        <Card className="border-slate-200 shadow-sm">
          <CardHeader>
            <CardTitle className="text-base">Try these in the room</CardTitle>
            <CardDescription>Pre-loaded demo catalog · no dealer DMS required</CardDescription>
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
            <CardTitle className="text-base">Multi-location</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Demo catalog spans 7 locations — same part, different stock and price.
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <Zap className="mb-2 h-5 w-5 text-slate-700" />
            <CardTitle className="text-base">Hybrid retrieval</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Dense + keyword fusion (RRF). Works offline for the pilot demo path.
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <Shield className="mb-2 h-5 w-5 text-slate-700" />
            <CardTitle className="text-base">Human in the loop</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Traffic-light confidence — green / yellow / red — not silent automation.
          </CardContent>
        </Card>
      </div>

      <Card className="border-dashed">
        <CardHeader>
          <CardTitle className="text-base">What we are not claiming today</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground space-y-1">
          <p>· Not a full DMS replacement or live OEM feed (yet).</p>
          <p>· Payments, shipping, and analytics pages are previews.</p>
          <p>· Production needs your catalog, auth, and network controls.</p>
        </CardContent>
      </Card>
    </div>
  )
}
