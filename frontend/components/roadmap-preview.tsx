import Link from 'next/link'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Settings2 } from 'lucide-react'

/** Integration / secondary module shell when provider keys or wiring incomplete. */
export function RoadmapPreview({
  title,
  description,
}: {
  title: string
  description?: string
}) {
  return (
    <div className="container mx-auto max-w-2xl p-6">
      <Card>
        <CardHeader>
          <div className="mb-2 flex items-center gap-2 text-slate-700">
            <Settings2 className="h-5 w-5" />
            <span className="text-xs font-semibold uppercase tracking-wide">
              System module
            </span>
          </div>
          <CardTitle>{title}</CardTitle>
          <CardDescription>
            {description ||
              'Configure provider credentials or finish service wiring to activate this module.'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Core operations live under <strong>Parts Search</strong>,{' '}
            <strong>Inventory</strong>, <strong>Orders</strong>, and{' '}
            <strong>Customers</strong>.
          </p>
          <div className="flex flex-wrap gap-2">
            <Button asChild>
              <Link href="/parts">Parts Search</Link>
            </Button>
            <Button asChild variant="outline">
              <Link href="/inventory">Inventory</Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
