import { Suspense } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Package, TrendingDown, TrendingUp, AlertTriangle, CheckCircle, Clock } from 'lucide-react'

export default function InventoryPage() {
  return (
    <div className="container mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-foreground mb-2">
          Inventory Management
        </h1>
        <p className="text-xl text-muted-foreground">
          Multi-location inventory tracking and management
        </p>
      </div>

      {/* Location Selector */}
      <div className="mb-6">
        <Card>
          <CardHeader>
            <CardTitle>Select Location</CardTitle>
            <CardDescription>
              Choose a location to view and manage inventory
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
              {[
                "Downtown Dealership",
                "Westside Location", 
                "Eastside Branch",
                "Northside Auto",
                "Southside Parts",
                "Central Hub",
                "Metro Location"
              ].map((location, index) => (
                <Button
                  key={index}
                  variant={index === 0 ? "default" : "outline"}
                  className="h-auto p-4 flex flex-col items-center space-y-2"
                >
                  <Package className="h-6 w-6" />
                  <span className="text-sm text-center">{location}</span>
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Inventory Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Items</CardTitle>
            <Package className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">2,847</div>
            <p className="text-xs text-muted-foreground">
              +12 items this week
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">In Stock</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">2,654</div>
            <p className="text-xs text-muted-foreground">
              93.2% availability
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Low Stock</CardTitle>
            <AlertTriangle className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">45</div>
            <p className="text-xs text-muted-foreground">
              Need reordering
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Out of Stock</CardTitle>
            <TrendingDown className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">23</div>
            <p className="text-xs text-muted-foreground">
              Urgent reorder needed
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Inventory Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>
              Common inventory operations
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <Button className="w-full" variant="outline">
                <Package className="h-4 w-4 mr-2" />
                Receive Inventory
              </Button>
              <Button className="w-full" variant="outline">
                <TrendingUp className="h-4 w-4 mr-2" />
                Trigger Reorder
              </Button>
              <Button className="w-full" variant="outline">
                <Clock className="h-4 w-4 mr-2" />
                Transfer Stock
              </Button>
              <Button className="w-full" variant="outline">
                <AlertTriangle className="h-4 w-4 mr-2" />
                Low Stock Report
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
            <CardDescription>
              Latest inventory changes
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center space-x-4">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <div className="flex-1">
                  <p className="text-sm font-medium">Received brake pads</p>
                  <p className="text-xs text-muted-foreground">+25 units • 2 minutes ago</p>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                <div className="flex-1">
                  <p className="text-sm font-medium">Stock transferred</p>
                  <p className="text-xs text-muted-foreground">10 oil filters • 5 minutes ago</p>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
                <div className="flex-1">
                  <p className="text-sm font-medium">Reorder triggered</p>
                  <p className="text-xs text-muted-foreground">Spark plugs • 8 minutes ago</p>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                <div className="flex-1">
                  <p className="text-sm font-medium">Out of stock alert</p>
                  <p className="text-xs text-muted-foreground">Air filters • 12 minutes ago</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>AI Insights</CardTitle>
            <CardDescription>
              AI-powered inventory recommendations
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="p-3 bg-blue-50 rounded-lg">
                <p className="text-sm font-medium text-blue-900">Fast Movers</p>
                <p className="text-xs text-blue-700">Consider increasing reorder quantities for brake pads and oil filters</p>
              </div>
              <div className="p-3 bg-yellow-50 rounded-lg">
                <p className="text-sm font-medium text-yellow-900">Overstock Alert</p>
                <p className="text-xs text-yellow-700">15 items have excess inventory - consider transfers</p>
              </div>
              <div className="p-3 bg-green-50 rounded-lg">
                <p className="text-sm font-medium text-green-900">Optimization</p>
                <p className="text-xs text-green-700">Inventory levels are well-balanced for current demand</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Low Stock Items */}
      <Card>
        <CardHeader>
          <CardTitle>Low Stock Items</CardTitle>
          <CardDescription>
            Items that need immediate attention
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div className="flex items-center space-x-4">
                <Package className="h-5 w-5 text-muted-foreground" />
                <div>
                  <p className="font-medium">Brake Pads - Front</p>
                  <p className="text-sm text-muted-foreground">Brembo • Part #BRK123</p>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <Badge variant="destructive">2 in stock</Badge>
                <Button size="sm" variant="outline">Reorder</Button>
              </div>
            </div>
            
            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div className="flex items-center space-x-4">
                <Package className="h-5 w-5 text-muted-foreground" />
                <div>
                  <p className="font-medium">Oil Filter</p>
                  <p className="text-sm text-muted-foreground">Fram • Part #FLT456</p>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <Badge variant="secondary">5 in stock</Badge>
                <Button size="sm" variant="outline">Reorder</Button>
              </div>
            </div>
            
            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div className="flex items-center space-x-4">
                <Package className="h-5 w-5 text-muted-foreground" />
                <div>
                  <p className="font-medium">Spark Plugs</p>
                  <p className="text-sm text-muted-foreground">NGK • Part #SPK789</p>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <Badge variant="destructive">0 in stock</Badge>
                <Button size="sm" variant="default">Urgent Reorder</Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
