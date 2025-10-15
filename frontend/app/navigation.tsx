import Link from 'next/link'
import { cn } from '@/lib/utils'

interface NavigationProps {
  className?: string
}

export function Navigation({ className }: NavigationProps) {
  const navItems = [
    { href: '/', label: 'Dashboard', icon: 'Dashboard' },
    { href: '/ai-agents', label: 'AI Agents', icon: 'AI' },
    { href: '/emails', label: 'Emails', icon: 'Email' },
    { href: '/orders', label: 'Orders', icon: 'Orders' },
    { href: '/inventory', label: 'Inventory', icon: 'Inventory' },
    { href: '/customers', label: 'Customers', icon: 'Customers' },
    { href: '/analytics', label: 'Analytics', icon: 'Analytics' },
  ]

  return (
    <nav className={cn("flex space-x-6", className)}>
      {navItems.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          className="flex items-center space-x-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
        >
          <span>{item.icon}</span>
          <span>{item.label}</span>
        </Link>
      ))}
    </nav>
  )
}
