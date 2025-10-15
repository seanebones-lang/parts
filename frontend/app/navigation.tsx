import Link from 'next/link'
import { cn } from '@/lib/utils'

interface NavigationProps {
  className?: string
}

export function Navigation({ className }: NavigationProps) {
  const navItems = [
    { href: '/', label: 'Dashboard', icon: '📊' },
    { href: '/ai-agents', label: 'AI Agents', icon: '🤖' },
    { href: '/emails', label: 'Emails', icon: '📧' },
    { href: '/orders', label: 'Orders', icon: '📦' },
    { href: '/inventory', label: 'Inventory', icon: '📋' },
    { href: '/customers', label: 'Customers', icon: '👥' },
    { href: '/analytics', label: 'Analytics', icon: '📈' },
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
