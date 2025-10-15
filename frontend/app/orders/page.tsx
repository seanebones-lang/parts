import { Suspense } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ShoppingCart, FileText, DollarSign, Clock, CheckCircle, XCircle, Package } from 'lucide-react'

export default function OrdersPage() {
  return (
    <div className="container mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-foreground mb-2">
          Order Management
        </h1>
        <p className="text-xl text-muted-foreground">
          AI-powered order processing and management
        </p>
      </div>

      {/* Order Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Orders</CardTitle>
            <ShoppingCart className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">1,247</div>
            <p className="text-xs text-muted-foreground">
              +15.3% from last month
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending Orders</CardTitle>
            <Clock className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">23</div>
            <p className="text-xs text-muted-foreground">
              Awaiting processing
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Completed Today</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">89</div>
            <p className="text-xs text-muted-foreground">
              94% completion rate
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Revenue Today</CardTitle>
            <DollarSign className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">$12,450</div>
            <p className="text-xs text-muted-foreground">
              +8.2% from yesterday
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>
              Common order operations
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <Button className="w-full" variant="outline">
                <FileText className="h-4 w-4 mr-2" />
                Generate Quote
              </Button>
              <Button className="w-full" variant="outline">
                <Package className="h-4 w-4 mr-2" />
                Create Order
              </Button>
              <Button className="w-full" variant="outline">
                <DollarSign className="h-4 w-4 mr-2" />
                Create Invoice
              </Button>
              <Button className="w-full" variant="outline">
                <Clock className="h-4 w-4 mr-2" />
                Process Pending
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Order Status</CardTitle>
            <CardDescription>
              Current order distribution
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Pending</span>
                <Badge variant="secondary">23</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Confirmed</span>
                <Badge variant="default">45</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Processing</span>
                <Badge variant="default">12</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Shipped</span>
                <Badge variant="default">67</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Delivered</span>
                <Badge variant="default" className="bg-green-500">89</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Cancelled</span>
                <Badge variant="destructive">3</Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
            <CardDescription>
              Latest order updates
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center space-x-4">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <div className="flex-1">
                  <p className="text-sm font-medium">Order #ORD001 completed</p>
                  <p className="text-xs text-muted-foreground">2 minutes ago</p>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                <div className="flex-1">
                  <p className="text-sm font-medium">New order received</p>
                  <p className="text-xs text-muted-foreground">5 minutes ago</p>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
                <div className="flex-1">
                  <p className="text-sm font-medium">Order shipped</p>
                  <p className="text-xs text-muted-foreground">8 minutes ago</p>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
                <div className="flex-1">
                  <p className="text-sm font-medium">Invoice generated</p>
                  <p className="text-xs text-muted-foreground">12 minutes ago</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Orders */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Orders</CardTitle>
          <CardDescription>
            Latest customer orders and their status
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Sample Order 1 */}
            <div className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50">
              <div className="flex items-center space-x-4">
                <Package className="h-5 w-5 text-muted-foreground" />
                <div>
                  <p className="font-medium">Order #ORD001</p>
                  <p className="text-sm text-muted-foreground">John Smith • Honda Civic Brake Pads</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="default" className="bg-green-500">Delivered</Badge>
                    <span className="text-sm text-muted-foreground">$89.99</span>
                  </div>
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm text-muted-foreground">Nov 15, 2024</p>
                <Button size="sm" variant="outline">View Details</Button>
              </div>
            </div>

            {/* Sample Order 2 */}
            <div className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50">
              <div className="flex items-center space-x-4">
                <Package className="h-5 w-5 text-muted-foreground" />
                <div>
                  <p className="font-medium">Order #ORD002</p>
                  <p className="text-sm text-muted-foreground">Sarah Johnson • Toyota Camry Oil Filter</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="default">Shipped</Badge>
                    <span className="text-sm text-muted-foreground">$24.99</span>
                  </div>
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm text-muted-foreground">Nov 15, 2024</p>
                <Button size="sm" variant="outline">View Details</Button>
              </div>
            </div>

            {/* Sample Order 3 */}
            <div className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50">
              <div className="flex items-center space-x-4">
                <Package className="h-5 w-5 text-muted-foreground" />
                <div>
                  <p className="font-medium">Order #ORD003</p>
                  <p className="text-sm text-muted-foreground">Mike Davis • Ford F-150 Spark Plugs</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="secondary">Processing</Badge>
                    <span className="text-sm text-muted-foreground">$67.50</span>
                  </div>
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm text-muted-foreground">Nov 15, 2024</p>
                <Button size="sm" variant="outline">View Details</Button>
              </div>
            </div>

            {/* Sample Order 4 */}
            <div className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50">
              <div className="flex items-center space-x-4">
                <Package className="h-5 w-5 text-muted-foreground" />
                <div>
                  <p className="font-medium">Order #ORD004</p>
                  <p className="text-sm text-muted-foreground">Lisa Wilson • BMW 3 Series Air Filter</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="secondary">Pending</Badge>
                    <span className="text-sm text-muted-foreground">$45.00</span>
                  </div>
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm text-muted-foreground">Nov 15, 2024</p>
                <Button size="sm" variant="outline">View Details</Button>
              </div>
            </div>

            {/* Sample Order 5 */}
            <div className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50">
              <div className="flex items-center space-x-4">
                <Package className="h-5 w-5 text-muted-foreground" />
                <div>
                  <p className="font-medium">Order #ORD005</p>
                  <p className="text-sm text-muted-foreground">Robert Brown • Chevrolet Silverado Tires</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="destructive">Cancelled</Badge>
                    <span className="text-sm text-muted-foreground">$599.96</span>
                  </div>
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm text-muted-foreground">Nov 14, 2024</p>
                <Button size="sm" variant="outline">View Details</Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
