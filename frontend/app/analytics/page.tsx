'use client'

import dynamic from 'next/dynamic'

const AnalyticsDashboard = dynamic(
  () => import('@/components/charts/analytics-dashboard'),
  {
    ssr: false,
    loading: () => (
      <div className="container mx-auto p-6">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-foreground mb-2">
            Analytics Dashboard
          </h1>
          <p className="text-xl text-muted-foreground">Loading charts…</p>
        </div>
        <div className="h-64 animate-pulse rounded-lg bg-muted" />
      </div>
    ),
  }
)

export default function AnalyticsPage() {
  return <AnalyticsDashboard />
}
