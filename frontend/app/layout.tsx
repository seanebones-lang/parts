import type { Metadata, Viewport } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { Navigation } from './navigation'
import { OfflineQueueBanner } from '@/components/offline-queue-banner'
import { PwaRegister } from '@/components/pwa-register'
import { getBrand } from '@/lib/demo-vertical'

const inter = Inter({ subsets: ['latin'] })

const brand = getBrand()

export const metadata: Metadata = {
  title: brand.documentTitle,
  description: brand.documentDescription,
  applicationName: brand.applicationName,
  manifest: '/manifest.webmanifest',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'default',
    title: brand.applicationName,
  },
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  themeColor: '#0f172a',
  viewportFit: 'cover',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="min-h-screen bg-background">
          <header className="border-b bg-white/80 backdrop-blur">
            <div className="container mx-auto px-6 py-4">
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-900 text-sm font-bold text-white">
                    {brand.mark}
                  </div>
                  <div>
                    <h1 className="text-lg font-bold leading-tight">{brand.title}</h1>
                    <p className="text-xs text-muted-foreground">
                      {brand.subtitle}
                    </p>
                  </div>
                </div>
                <Navigation />
              </div>
            </div>
          </header>
          <PwaRegister />
          <OfflineQueueBanner />
          <main>{children}</main>
        </div>
      </body>
    </html>
  )
}
