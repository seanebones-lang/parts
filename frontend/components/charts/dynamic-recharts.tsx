/**
 * Client-only Recharts helpers for Next.js App Router.
 * Recharts uses browser APIs and breaks during SSR/page-data collection
 * ("Super expression must either be null or a function").
 *
 * Prefer loading chart UIs via:
 *   dynamic(() => import('@/components/charts/...'), { ssr: false })
 */
'use client'

export {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'
