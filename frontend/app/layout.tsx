import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { Navigation } from './navigation'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Parts — Dealership Parts AI | NextEleven',
  description:
    'Multi-location dealership parts search with hybrid RAG and traffic-light confidence. Design-partner pilot.',
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
                    P
                  </div>
                  <div>
                    <h1 className="text-lg font-bold leading-tight">Parts</h1>
                    <p className="text-xs text-muted-foreground">
                      NextEleven · multi-location parts AI · pilot
                    </p>
                  </div>
                </div>
                <Navigation />
              </div>
            </div>
          </header>
          <main>{children}</main>
        </div>
      </body>
    </html>
  )
}
