'use client'

import { Suspense } from 'react'
import ShippingInner from './shipping-inner'

export default function ShippingPage() {
  return (
    <Suspense
      fallback={
        <div className="container mx-auto max-w-3xl p-6 text-sm text-muted-foreground">
          Loading shipping…
        </div>
      }
    >
      <ShippingInner />
    </Suspense>
  )
}
