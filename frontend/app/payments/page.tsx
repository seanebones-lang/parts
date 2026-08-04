'use client'

import { Suspense } from 'react'
import PaymentsInner from './payments-inner'

export default function PaymentsPage() {
  return (
    <Suspense
      fallback={
        <div className="container mx-auto max-w-3xl p-6 text-sm text-muted-foreground">
          Loading payments…
        </div>
      }
    >
      <PaymentsInner />
    </Suspense>
  )
}
