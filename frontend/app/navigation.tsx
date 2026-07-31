import Link from 'next/link'
import { cn } from '@/lib/utils'

interface NavigationProps {
  className?: string
}

/** Primary nav — Parts + DMS modules are Live; payments/shipping stay Preview. */
export function Navigation({ className }: NavigationProps) {
  const navItems: Array<{ href: string; label: string; live?: boolean }> = [
    { href: '/parts', label: 'Parts Search', live: true },
    { href: '/', label: 'Home' },
    { href: '/inventory', label: 'Inventory', live: true },
    { href: '/orders', label: 'Orders', live: true },
    { href: '/customers', label: 'Customers', live: true },
    { href: '/analytics', label: 'Analytics' },
    { href: '/ai-agents', label: 'AI Agents' },
    { href: '/payments', label: 'Payments' },
    { href: '/shipping', label: 'Shipping' },
  ]

  return (
    <nav className={cn('flex flex-wrap items-center gap-x-4 gap-y-2', className)}>
      {navItems.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          className={cn(
            'flex items-center gap-1.5 text-sm font-medium transition-colors',
            item.live
              ? 'text-foreground font-semibold underline-offset-4 hover:underline'
              : 'text-muted-foreground hover:text-foreground'
          )}
        >
          <span>{item.label}</span>
          {item.live ? (
            <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-emerald-800">
              Live
            </span>
          ) : item.href !== '/' ? (
            <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-muted-foreground">
              Preview
            </span>
          ) : null}
        </Link>
      ))}
    </nav>
  )
}
