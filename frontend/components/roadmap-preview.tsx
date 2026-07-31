import Link from 'next/link'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Construction } from 'lucide-react'

/** Honest placeholder for roadmap UI shells during dealership demos. */
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
          <div className="mb-2 flex items-center gap-2 text-amber-700">
            <Construction className="h-5 w-5" />
            <span className="text-xs font-semibold uppercase tracking-wide">Roadmap preview</span>
          </div>
          <CardTitle>{title}</CardTitle>
          <CardDescription>
            {description ||
              'This screen is a product shell for the pilot narrative — not connected to live dealership data.'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            The live demo path is <strong>Parts Search</strong>: natural-language lookup with
            multi-location ranking and traffic-light confidence.
          </p>
          <Button asChild>
            <Link href="/parts">Go to Parts Search</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
