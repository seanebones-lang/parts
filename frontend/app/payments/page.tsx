import { Suspense } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { CreditCard, DollarSign, TrendingUp, Clock, CheckCircle, AlertTriangle, Receipt } from 'lucide-react'

export default function PaymentsPage() {
  return (
    <div className="container mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-foreground mb-2">
          Payment Management
        </h1>
        <p className="text-xl text-muted-foreground">
          Stripe-powered payment processing and tracking
        </p>
      </div>

      {/* Payment Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Payments</CardTitle>
            <CreditCard className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">$45,230</div>
            <p className="text-xs text-muted-foreground">
              +12.5% from last month
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">96.8%</div>
            <p className="text-xs text-muted-foreground">
              Payment success rate
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending Payments</CardTitle>
            <Clock className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">$2,340</div>
            <p className="text-xs text-muted-foreground">
              15 invoices awaiting payment
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Failed Payments</CardTitle>
            <AlertTriangle className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">8</div>
            <p className="text-xs text-muted-foreground">
              Need attention
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Payment Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <Card>
          <CardHeader>
            <CardTitle>Payment Actions</CardTitle>
            <CardDescription>
              Common payment operations
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <Button className="w-full" variant="outline">
                <CreditCard className="h-4 w-4 mr-2" />
                Create Payment Link
              </Button>
              <Button className="w-full" variant="outline">
                <Receipt className="h-4 w-4 mr-2" />
                Process Refund
              </Button>
              <Button className="w-full" variant="outline">
                <Clock className="h-4 w-4 mr-2" />
                Send Reminder
              </Button>
              <Button className="w-full" variant="outline">
                <TrendingUp className="h-4 w-4 mr-2" />
                View Analytics
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Payment Methods</CardTitle>
            <CardDescription>
              Accepted payment types
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Credit Cards</span>
                <Badge variant="default" className="bg-green-500">Enabled</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Debit Cards</span>
                <Badge variant="default" className="bg-green-500">Enabled</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Apple Pay</span>
                <Badge variant="default" className="bg-green-500">Enabled</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Google Pay</span>
                <Badge variant="default" className="bg-green-500">Enabled</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Bank Transfer</span>
                <Badge variant="secondary">Coming Soon</Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent Payments</CardTitle>
            <CardDescription>
              Latest payment activity
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center space-x-4">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <div className="flex-1">
                  <p className="text-sm font-medium">Payment successful</p>
                  <p className="text-xs text-muted-foreground">$89.99 • 2 minutes ago</p>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <div className="flex-1">
                  <p className="text-sm font-medium">Payment successful</p>
                  <p className="text-xs text-muted-foreground">$245.50 • 5 minutes ago</p>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
                <div className="flex-1">
                  <p className="text-sm font-medium">Payment pending</p>
                  <p className="text-xs text-muted-foreground">$156.75 • 8 minutes ago</p>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                <div className="flex-1">
                  <p className="text-sm font-medium">Payment failed</p>
                  <p className="text-xs text-muted-foreground">$89.99 • 12 minutes ago</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Payment Analytics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <Card>
          <CardHeader>
            <CardTitle>Payment Success Rate</CardTitle>
            <CardDescription>
              Payment success trends over time
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Today</span>
                <span className="text-sm font-bold text-green-600">97.2%</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">This Week</span>
                <span className="text-sm font-bold text-green-600">96.8%</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">This Month</span>
                <span className="text-sm font-bold text-green-600">96.5%</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">All Time</span>
                <span className="text-sm font-bold text-green-600">96.1%</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Payment Volume</CardTitle>
            <CardDescription>
              Revenue and transaction volume
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Today</span>
                <span className="text-sm font-bold">$2,340</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">This Week</span>
                <span className="text-sm font-bold">$12,450</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">This Month</span>
                <span className="text-sm font-bold">$45,230</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Average Transaction</span>
                <span className="text-sm font-bold">$89.45</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Pending Payments */}
      <Card>
        <CardHeader>
          <CardTitle>Pending Payments</CardTitle>
          <CardDescription>
            Invoices awaiting payment with action options
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Sample Pending Payment 1 */}
            <div className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50">
              <div className="flex items-center space-x-4">
                <Receipt className="h-5 w-5 text-muted-foreground" />
                <div>
                  <p className="font-medium">Invoice #INV001</p>
                  <p className="text-sm text-muted-foreground">John Smith • Due: Nov 20, 2024</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="secondary">5 days overdue</Badge>
                    <span className="text-sm text-muted-foreground">$89.99</span>
                  </div>
                </div>
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="outline">Send Reminder</Button>
                <Button size="sm" variant="outline">Create Link</Button>
              </div>
            </div>

            {/* Sample Pending Payment 2 */}
            <div className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50">
              <div className="flex items-center space-x-4">
                <Receipt className="h-5 w-5 text-muted-foreground" />
                <div>
                  <p className="font-medium">Invoice #INV002</p>
                  <p className="text-sm text-muted-foreground">Sarah Johnson • Due: Nov 25, 2024</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="default">Due today</Badge>
                    <span className="text-sm text-muted-foreground">$245.50</span>
                  </div>
                </div>
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="outline">Send Reminder</Button>
                <Button size="sm" variant="outline">Create Link</Button>
              </div>
            </div>

            {/* Sample Pending Payment 3 */}
            <div className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50">
              <div className="flex items-center space-x-4">
                <Receipt className="h-5 w-5 text-muted-foreground" />
                <div>
                  <p className="font-medium">Invoice #INV003</p>
                  <p className="text-sm text-muted-foreground">Mike Davis • Due: Nov 30, 2024</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="default" className="bg-green-500">5 days remaining</Badge>
                    <span className="text-sm text-muted-foreground">$156.75</span>
                  </div>
                </div>
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="outline">Send Reminder</Button>
                <Button size="sm" variant="outline">Create Link</Button>
              </div>
            </div>

            {/* Sample Pending Payment 4 */}
            <div className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50">
              <div className="flex items-center space-x-4">
                <Receipt className="h-5 w-5 text-muted-foreground" />
                <div>
                  <p className="font-medium">Invoice #INV004</p>
                  <p className="text-sm text-muted-foreground">Lisa Wilson • Due: Dec 5, 2024</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="default" className="bg-blue-500">10 days remaining</Badge>
                    <span className="text-sm text-muted-foreground">$299.99</span>
                  </div>
                </div>
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="outline">Send Reminder</Button>
                <Button size="sm" variant="outline">Create Link</Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
