import { Suspense } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  Area,
  AreaChart
} from 'recharts'
import { 
  TrendingUp, 
  Mail, 
  ShoppingCart, 
  DollarSign, 
  Package, 
  Users, 
  Clock, 
  CheckCircle,
  AlertTriangle,
  Brain,
  Activity
} from 'lucide-react'

export default function AnalyticsPage() {
  // Mock data for charts
  const emailVolumeData = [
    { date: '2024-11-01', count: 45 },
    { date: '2024-11-02', count: 52 },
    { date: '2024-11-03', count: 38 },
    { date: '2024-11-04', count: 61 },
    { date: '2024-11-05', count: 55 },
    { date: '2024-11-06', count: 48 },
    { date: '2024-11-07', count: 67 }
  ]

  const revenueData = [
    { date: '2024-11-01', revenue: 1850 },
    { date: '2024-11-02', revenue: 2200 },
    { date: '2024-11-03', revenue: 1650 },
    { date: '2024-11-04', revenue: 2800 },
    { date: '2024-11-05', revenue: 2400 },
    { date: '2024-11-06', revenue: 2100 },
    { date: '2024-11-07', revenue: 2950 }
  ]

  const agentPerformanceData = [
    { name: 'Email Classifier', success: 98.5, actions: 1250 },
    { name: 'Customer Service', success: 94.2, actions: 890 },
    { name: 'Parts Lookup', success: 96.8, actions: 2100 },
    { name: 'Inventory Manager', success: 97.1, actions: 450 },
    { name: 'Pricing & Invoice', success: 95.5, actions: 780 },
    { name: 'Payment Agent', success: 99.2, actions: 340 },
    { name: 'Shipping Coordinator', success: 93.8, actions: 520 },
    { name: 'Supplier Sourcing', success: 91.5, actions: 180 }
  ]

  const emailTypesData = [
    { name: 'Parts Orders', value: 45, color: '#8884d8' },
    { name: 'Quote Requests', value: 25, color: '#82ca9d' },
    { name: 'Shipping Inquiries', value: 15, color: '#ffc658' },
    { name: 'Customer Service', value: 10, color: '#ff7300' },
    { name: 'Other', value: 5, color: '#00ff00' }
  ]

  const monthlyRevenueData = [
    { month: '2024-06', revenue: 42000 },
    { month: '2024-07', revenue: 45000 },
    { month: '2024-08', revenue: 48000 },
    { month: '2024-09', revenue: 52000 },
    { month: '2024-10', revenue: 55000 },
    { month: '2024-11', revenue: 58000 }
  ]

  return (
    <div className="container mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-foreground mb-2">
          Analytics Dashboard
        </h1>
        <p className="text-xl text-muted-foreground">
          Comprehensive business intelligence and performance metrics
        </p>
      </div>

      {/* Key Metrics Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Emails Processed</CardTitle>
            <Mail className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">2,847</div>
            <p className="text-xs text-muted-foreground">
              <span className="text-green-600">+12.5%</span> from last month
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Orders Completed</CardTitle>
            <ShoppingCart className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">1,247</div>
            <p className="text-xs text-muted-foreground">
              <span className="text-green-600">+8.2%</span> from last month
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Revenue</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">$156,230</div>
            <p className="text-xs text-muted-foreground">
              <span className="text-green-600">+15.3%</span> from last month
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">AI Success Rate</CardTitle>
            <Brain className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">96.8%</div>
            <p className="text-xs text-muted-foreground">
              <span className="text-green-600">+2.1%</span> from last month
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Performance Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <Card>
          <CardHeader>
            <CardTitle>Email Processing</CardTitle>
            <CardDescription>Email volume and response metrics</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Processing Rate</span>
                <Badge variant="default" className="bg-green-500">94.2%</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Avg Response Time</span>
                <span className="text-sm font-bold">47 seconds</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">AI Classification</span>
                <Badge variant="default" className="bg-blue-500">95.2%</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Daily Volume</span>
                <span className="text-sm font-bold">407 emails</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Order Processing</CardTitle>
            <CardDescription>Order completion and automation metrics</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Completion Rate</span>
                <Badge variant="default" className="bg-green-500">94.2%</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Avg Processing Time</span>
                <span className="text-sm font-bold">4.8 minutes</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">AI Automation</span>
                <Badge variant="default" className="bg-purple-500">87%</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Avg Order Value</span>
                <span className="text-sm font-bold">$1,250</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Customer Experience</CardTitle>
            <CardDescription>Customer satisfaction and engagement</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Satisfaction Score</span>
                <Badge variant="default" className="bg-green-500">4.2/5</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Response Rate</span>
                <Badge variant="default" className="bg-blue-500">68%</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Repeat Customers</span>
                <Badge variant="default" className="bg-orange-500">65%</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">New Customers</span>
                <span className="text-sm font-bold">234 this month</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Email Volume Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Email Volume Trend</CardTitle>
            <CardDescription>Daily email processing volume</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={emailVolumeData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Area 
                  type="monotone" 
                  dataKey="count" 
                  stroke="#8884d8" 
                  fill="#8884d8" 
                  fillOpacity={0.3}
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Revenue Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Daily Revenue</CardTitle>
            <CardDescription>Revenue trends over time</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={revenueData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip formatter={(value) => [`$${value}`, 'Revenue']} />
                <Line 
                  type="monotone" 
                  dataKey="revenue" 
                  stroke="#82ca9d" 
                  strokeWidth={3}
                  dot={{ fill: '#82ca9d' }}
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Agent Performance Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Agent Performance</CardTitle>
            <CardDescription>AI agent success rates and action counts</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={400}>
              <BarChart data={agentPerformanceData} layout="horizontal">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" domain={[0, 100]} />
                <YAxis dataKey="name" type="category" width={120} />
                <Tooltip formatter={(value) => [`${value}%`, 'Success Rate']} />
                <Bar dataKey="success" fill="#8884d8" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Email Types Distribution */}
        <Card>
          <CardHeader>
            <CardTitle>Email Types Distribution</CardTitle>
            <CardDescription>Breakdown of email types processed</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={400}>
              <PieChart>
                <Pie
                  data={emailTypesData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={120}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {emailTypesData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Monthly Revenue Trend */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle>Monthly Revenue Trend</CardTitle>
          <CardDescription>Revenue growth over the last 6 months</CardDescription>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={monthlyRevenueData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis />
              <Tooltip formatter={(value) => [`$${value.toLocaleString()}`, 'Revenue']} />
              <Bar dataKey="revenue" fill="#82ca9d" />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Inventory and System Health */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <Card>
          <CardHeader>
            <CardTitle>Inventory Status</CardTitle>
            <CardDescription>Current inventory levels and alerts</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Total Items</span>
                <span className="text-sm font-bold">12,847</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Low Stock Items</span>
                <Badge variant="destructive">23</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Out of Stock</span>
                <Badge variant="destructive">8</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Inventory Value</span>
                <span className="text-sm font-bold">$2.3M</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Turnover Rate</span>
                <span className="text-sm font-bold">4.2x annually</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>System Health</CardTitle>
            <CardDescription>System performance and uptime metrics</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">System Uptime</span>
                <Badge variant="default" className="bg-green-500">99.8%</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">API Response Time</span>
                <span className="text-sm font-bold">145ms</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Error Rate</span>
                <Badge variant="default" className="bg-green-500">0.2%</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Active Agents</span>
                <span className="text-sm font-bold">10/13</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Queue Size</span>
                <span className="text-sm font-bold">47 pending</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Export and Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Reports & Export</CardTitle>
          <CardDescription>Generate detailed reports and export data</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Button variant="outline" className="h-auto p-4 flex flex-col items-center space-y-2">
              <TrendingUp className="h-6 w-6" />
              <span className="text-sm">Email Performance</span>
            </Button>
            <Button variant="outline" className="h-auto p-4 flex flex-col items-center space-y-2">
              <ShoppingCart className="h-6 w-6" />
              <span className="text-sm">Order Analysis</span>
            </Button>
            <Button variant="outline" className="h-auto p-4 flex flex-col items-center space-y-2">
              <Brain className="h-6 w-6" />
              <span className="text-sm">Agent Performance</span>
            </Button>
            <Button variant="outline" className="h-auto p-4 flex flex-col items-center space-y-2">
              <Package className="h-6 w-6" />
              <span className="text-sm">Inventory Report</span>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
