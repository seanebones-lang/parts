import Link from 'next/link'
import { cn } from '@/lib/utils'

interface NavigationProps {
  className?: string
}

/** Primary nav — core system modules first. */
export function Navigation({ className }: NavigationProps) {
  const navItems: Array<{ href: string; label: string; core?: boolean }> = [
    { href: '/parts', label: 'Parts Search', core: true },
    { href: '/inventory', label: 'Inventory', core: true },
    { href: '/orders', label: 'Orders', core: true },
    { href: '/customers', label: 'Customers', core: true },
    { href: '/', label: 'Home' },
    { href: '/payments', label: 'Payments' },
    { href: '/shipping', label: 'Shipping' },
    { href: '/analytics', label: 'Analytics' },
    { href: '/ai-agents', label: 'Agents' },
  ]

  return (
    <nav className={cn('flex flex-wrap items-center gap-x-4 gap-y-2', className)}>
      {navItems.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          className={cn(
            'flex items-center gap-1.5 text-sm font-medium transition-colors',
            item.core
              ? 'font-semibold text-foreground underline-offset-4 hover:underline'
              : 'text-muted-foreground hover:text-foreground'
          )}
        >
          <span>{item.label}</span>
        </Link>
      ))}
    </nav>
  )
}
