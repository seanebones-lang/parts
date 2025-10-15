import { Suspense } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Truck, Package, MapPin, Clock, CheckCircle, AlertTriangle, Download } from 'lucide-react'

export default function ShippingPage() {
  return (
    <div className="container mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-foreground mb-2">
          Shipping & Logistics
        </h1>
        <p className="text-xl text-muted-foreground">
          Multi-carrier shipping coordination and tracking
        </p>
      </div>

      {/* Shipping Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Shipments</CardTitle>
            <Truck className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">47</div>
            <p className="text-xs text-muted-foreground">
              In transit and pending
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Delivered Today</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">23</div>
            <p className="text-xs text-muted-foreground">
              Successfully delivered
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending Pickup</CardTitle>
            <Clock className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">8</div>
            <p className="text-xs text-muted-foreground">
              Awaiting carrier pickup
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Exceptions</CardTitle>
            <AlertTriangle className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">3</div>
            <p className="text-xs text-muted-foreground">
              Need attention
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Shipping Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <Card>
          <CardHeader>
            <CardTitle>Shipping Actions</CardTitle>
            <CardDescription>
              Common shipping operations
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <Button className="w-full" variant="outline">
                <Package className="h-4 w-4 mr-2" />
                Create Shipment
              </Button>
              <Button className="w-full" variant="outline">
                <Truck className="h-4 w-4 mr-2" />
                Get Shipping Rates
              </Button>
              <Button className="w-full" variant="outline">
                <Download className="h-4 w-4 mr-2" />
                Generate Label
              </Button>
              <Button className="w-full" variant="outline">
                <MapPin className="h-4 w-4 mr-2" />
                Track Package
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Carrier Performance</CardTitle>
            <CardDescription>
              Delivery performance by carrier
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">UPS</span>
                <div className="flex items-center gap-2">
                  <Badge variant="default" className="bg-brown-500">97.2%</Badge>
                  <span className="text-xs text-muted-foreground">on-time</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">FedEx</span>
                <div className="flex items-center gap-2">
                  <Badge variant="default" className="bg-purple-500">96.8%</Badge>
                  <span className="text-xs text-muted-foreground">on-time</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">USPS</span>
                <div className="flex items-center gap-2">
                  <Badge variant="default" className="bg-blue-500">95.5%</Badge>
                  <span className="text-xs text-muted-foreground">on-time</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">DHL</span>
                <div className="flex items-center gap-2">
                  <Badge variant="default" className="bg-red-500">98.1%</Badge>
                  <span className="text-xs text-muted-foreground">on-time</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
            <CardDescription>
              Latest shipping updates
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center space-x-4">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <div className="flex-1">
                  <p className="text-sm font-medium">Package delivered</p>
                  <p className="text-xs text-muted-foreground">1Z123456789 • 2 minutes ago</p>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                <div className="flex-1">
                  <p className="text-sm font-medium">Label generated</p>
                  <p className="text-xs text-muted-foreground">123456789FDX • 5 minutes ago</p>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
                <div className="flex-1">
                  <p className="text-sm font-medium">Package in transit</p>
                  <p className="text-xs text-muted-foreground">9400123456789 • 8 minutes ago</p>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                <div className="flex-1">
                  <p className="text-sm font-medium">Delivery exception</p>
                  <p className="text-xs text-muted-foreground">123456789DHL • 12 minutes ago</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Active Shipments */}
      <Card>
        <CardHeader>
          <CardTitle>Active Shipments</CardTitle>
          <CardDescription>
            Current shipments and their status
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Sample Shipment 1 */}
            <div className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50">
              <div className="flex items-center space-x-4">
                <Truck className="h-5 w-5 text-muted-foreground" />
                <div>
                  <p className="font-medium">1Z1234567890123456</p>
                  <p className="text-sm text-muted-foreground">John Smith • UPS Ground • 3 days</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="default" className="bg-blue-500">In Transit</Badge>
                    <span className="text-sm text-muted-foreground">Atlanta, GA</span>
                  </div>
                </div>
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="outline">Track</Button>
                <Button size="sm" variant="outline">Label</Button>
              </div>
            </div>

            {/* Sample Shipment 2 */}
            <div className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50">
              <div className="flex items-center space-x-4">
                <Truck className="h-5 w-5 text-muted-foreground" />
                <div>
                  <p className="font-medium">1234567890123456FDX</p>
                  <p className="text-sm text-muted-foreground">Sarah Johnson • FedEx 2Day • 2 days</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="default" className="bg-green-500">Delivered</Badge>
                    <span className="text-sm text-muted-foreground">New York, NY</span>
                  </div>
                </div>
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="outline">Track</Button>
                <Button size="sm" variant="outline">Label</Button>
              </div>
            </div>

            {/* Sample Shipment 3 */}
            <div className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50">
              <div className="flex items-center space-x-4">
                <Truck className="h-5 w-5 text-muted-foreground" />
                <div>
                  <p className="font-medium">9400123456789012345678</p>
                  <p className="text-sm text-muted-foreground">Mike Davis • USPS Priority • 2 days</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="default" className="bg-yellow-500">Out for Delivery</Badge>
                    <span className="text-sm text-muted-foreground">Miami, FL</span>
                  </div>
                </div>
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="outline">Track</Button>
                <Button size="sm" variant="outline">Label</Button>
              </div>
            </div>

            {/* Sample Shipment 4 */}
            <div className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50">
              <div className="flex items-center space-x-4">
                <Truck className="h-5 w-5 text-muted-foreground" />
                <div>
                  <p className="font-medium">1234567890123456DHL</p>
                  <p className="text-sm text-muted-foreground">Lisa Wilson • DHL Express • 1 day</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="destructive">Exception</Badge>
                    <span className="text-sm text-muted-foreground">Address Issue</span>
                  </div>
                </div>
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="outline">Track</Button>
                <Button size="sm" variant="outline">Resolve</Button>
              </div>
            </div>

            {/* Sample Shipment 5 */}
            <div className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50">
              <div className="flex items-center space-x-4">
                <Truck className="h-5 w-5 text-muted-foreground" />
                <div>
                  <p className="font-medium">1Z9876543210987654</p>
                  <p className="text-sm text-muted-foreground">Robert Brown • UPS Ground • 3 days</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="secondary">Label Created</Badge>
                    <span className="text-sm text-muted-foreground">Ready for pickup</span>
                  </div>
                </div>
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="outline">Schedule Pickup</Button>
                <Button size="sm" variant="outline">Label</Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
