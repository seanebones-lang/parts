import { Suspense } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Search, DollarSign, Truck, Star, AlertTriangle, TrendingUp, Globe } from 'lucide-react'

export default function SourcingPage() {
  return (
    <div className="container mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-foreground mb-2">
          Parts Sourcing
        </h1>
        <p className="text-xl text-muted-foreground">
          Find parts from external suppliers when out of stock
        </p>
      </div>

      {/* Sourcing Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Suppliers</CardTitle>
            <Globe className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">5</div>
            <p className="text-xs text-muted-foreground">
              Rock Auto, AutoZone, O'Reilly's, NAPA, CarParts.com
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Parts Cataloged</CardTitle>
            <Search className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">12,847</div>
            <p className="text-xs text-muted-foreground">
              +234 this week
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Savings</CardTitle>
            <DollarSign className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">18.5%</div>
            <p className="text-xs text-muted-foreground">
              vs. list price
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
            <TrendingUp className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">94.2%</div>
            <p className="text-xs text-muted-foreground">
              Parts found when needed
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Sourcing Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <Card>
          <CardHeader>
            <CardTitle>Sourcing Actions</CardTitle>
            <CardDescription>
              Common sourcing operations
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <Button className="w-full" variant="outline">
                <Search className="h-4 w-4 mr-2" />
                Find Parts
              </Button>
              <Button className="w-full" variant="outline">
                <DollarSign className="h-4 w-4 mr-2" />
                Compare Prices
              </Button>
              <Button className="w-full" variant="outline">
                <Truck className="h-4 w-4 mr-2" />
                Check Availability
              </Button>
              <Button className="w-full" variant="outline">
                <AlertTriangle className="h-4 w-4 mr-2" />
                Update Catalogs
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Supplier Performance</CardTitle>
            <CardDescription>
              Supplier ratings and reliability
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Rock Auto</span>
                <div className="flex items-center gap-2">
                  <div className="flex">
                    {[...Array(5)].map((_, i) => (
                      <Star key={i} className={`h-3 w-3 ${i < 4 ? 'fill-yellow-400 text-yellow-400' : 'text-gray-300'}`} />
                    ))}
                  </div>
                  <span className="text-xs text-muted-foreground">4.2/5</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">AutoZone</span>
                <div className="flex items-center gap-2">
                  <div className="flex">
                    {[...Array(5)].map((_, i) => (
                      <Star key={i} className={`h-3 w-3 ${i < 4 ? 'fill-yellow-400 text-yellow-400' : 'text-gray-300'}`} />
                    ))}
                  </div>
                  <span className="text-xs text-muted-foreground">4.0/5</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">O'Reilly's</span>
                <div className="flex items-center gap-2">
                  <div className="flex">
                    {[...Array(5)].map((_, i) => (
                      <Star key={i} className={`h-3 w-3 ${i < 4 ? 'fill-yellow-400 text-yellow-400' : 'text-gray-300'}`} />
                    ))}
                  </div>
                  <span className="text-xs text-muted-foreground">3.8/5</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">NAPA</span>
                <div className="flex items-center gap-2">
                  <div className="flex">
                    {[...Array(5)].map((_, i) => (
                      <Star key={i} className={`h-3 w-3 ${i < 4 ? 'fill-yellow-400 text-yellow-400' : 'text-gray-300'}`} />
                    ))}
                  </div>
                  <span className="text-xs text-muted-foreground">4.5/5</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">CarParts.com</span>
                <div className="flex items-center gap-2">
                  <div className="flex">
                    {[...Array(5)].map((_, i) => (
                      <Star key={i} className={`h-3 w-3 ${i < 3 ? 'fill-yellow-400 text-yellow-400' : 'text-gray-300'}`} />
                    ))}
                  </div>
                  <span className="text-xs text-muted-foreground">3.6/5</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent Sourcing</CardTitle>
            <CardDescription>
              Latest parts sourcing activity
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center space-x-4">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <div className="flex-1">
                  <p className="text-sm font-medium">Brake pads found</p>
                  <p className="text-xs text-muted-foreground">Rock Auto • $89.99 • 2 minutes ago</p>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                <div className="flex-1">
                  <p className="text-sm font-medium">Oil filter sourced</p>
                  <p className="text-xs text-muted-foreground">AutoZone • $24.99 • 5 minutes ago</p>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
                <div className="flex-1">
                  <p className="text-sm font-medium">Price comparison</p>
                  <p className="text-xs text-muted-foreground">Spark plugs • 5 suppliers • 8 minutes ago</p>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
                <div className="flex-1">
                  <p className="text-sm font-medium">Catalog updated</p>
                  <p className="text-xs text-muted-foreground">NAPA • 1,234 new parts • 12 minutes ago</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Price Comparison Example */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle>Recent Price Comparison</CardTitle>
          <CardDescription>
            Honda Civic brake pads - 2020 model
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Sample Price Comparison 1 */}
            <div className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50">
              <div className="flex items-center space-x-4">
                <div className="w-10 h-10 bg-red-500 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-sm">RA</span>
                </div>
                <div>
                  <p className="font-medium">Rock Auto</p>
                  <p className="text-sm text-muted-foreground">Brembo P85109N • In Stock • 3 days delivery</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="default" className="bg-green-500">Best Price</Badge>
                    <span className="text-xs text-muted-foreground">Rating: 4.2/5</span>
                  </div>
                </div>
              </div>
              <div className="text-right">
                <p className="text-2xl font-bold text-green-600">$89.99</p>
                <p className="text-sm text-muted-foreground">+ $12.95 shipping</p>
              </div>
            </div>

            {/* Sample Price Comparison 2 */}
            <div className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50">
              <div className="flex items-center space-x-4">
                <div className="w-10 h-10 bg-blue-500 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-sm">AZ</span>
                </div>
                <div>
                  <p className="font-medium">AutoZone</p>
                  <p className="text-sm text-muted-foreground">Duralast Gold • In Stock • 2 days delivery</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="default" className="bg-blue-500">Fastest</Badge>
                    <span className="text-xs text-muted-foreground">Rating: 4.0/5</span>
                  </div>
                </div>
              </div>
              <div className="text-right">
                <p className="text-2xl font-bold">$124.99</p>
                <p className="text-sm text-muted-foreground">Free shipping</p>
              </div>
            </div>

            {/* Sample Price Comparison 3 */}
            <div className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50">
              <div className="flex items-center space-x-4">
                <div className="w-10 h-10 bg-orange-500 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-sm">OR</span>
                </div>
                <div>
                  <p className="font-medium">O'Reilly Auto Parts</p>
                  <p className="text-sm text-muted-foreground">BrakeBest Select • In Stock • 3 days delivery</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="secondary">Standard</Badge>
                    <span className="text-xs text-muted-foreground">Rating: 3.8/5</span>
                  </div>
                </div>
              </div>
              <div className="text-right">
                <p className="text-2xl font-bold">$98.99</p>
                <p className="text-sm text-muted-foreground">+ $9.99 shipping</p>
              </div>
            </div>

            {/* Sample Price Comparison 4 */}
            <div className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50">
              <div className="flex items-center space-x-4">
                <div className="w-10 h-10 bg-green-600 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-sm">NP</span>
                </div>
                <div>
                  <p className="font-medium">NAPA Auto Parts</p>
                  <p className="text-sm text-muted-foreground">NAPA Premium • Limited Stock • 2 days delivery</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="default" className="bg-green-600">Premium</Badge>
                    <span className="text-xs text-muted-foreground">Rating: 4.5/5</span>
                  </div>
                </div>
              </div>
              <div className="text-right">
                <p className="text-2xl font-bold">$149.99</p>
                <p className="text-sm text-muted-foreground">Free shipping</p>
              </div>
            </div>

            {/* Recommendation */}
            <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex items-start space-x-3">
                <TrendingUp className="h-5 w-5 text-blue-600 mt-0.5" />
                <div>
                  <h4 className="font-medium text-blue-900">AI Recommendation</h4>
                  <p className="text-sm text-blue-700 mt-1">
                    <strong>Rock Auto</strong> offers the best value at $89.99 with excellent ratings. 
                    AutoZone provides the fastest delivery if speed is critical. 
                    NAPA offers premium quality for customers who prioritize brand reputation.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Supplier Catalog Status */}
      <Card>
        <CardHeader>
          <CardTitle>Supplier Catalog Status</CardTitle>
          <CardDescription>
            Real-time catalog freshness and update status
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Sample Supplier Status 1 */}
            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div className="flex items-center space-x-4">
                <div className="w-10 h-10 bg-red-500 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-sm">RA</span>
                </div>
                <div>
                  <p className="font-medium">Rock Auto</p>
                  <p className="text-sm text-muted-foreground">45,231 parts cataloged</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="default" className="bg-green-500">Fresh</Badge>
                    <span className="text-xs text-muted-foreground">Updated 2 hours ago</span>
                  </div>
                </div>
              </div>
              <div className="text-right">
                <Button size="sm" variant="outline">Update Now</Button>
              </div>
            </div>

            {/* Sample Supplier Status 2 */}
            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div className="flex items-center space-x-4">
                <div className="w-10 h-10 bg-blue-500 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-sm">AZ</span>
                </div>
                <div>
                  <p className="font-medium">AutoZone</p>
                  <p className="text-sm text-muted-foreground">32,156 parts cataloged</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="secondary">Stale</Badge>
                    <span className="text-xs text-muted-foreground">Updated 2 days ago</span>
                  </div>
                </div>
              </div>
              <div className="text-right">
                <Button size="sm" variant="outline">Update Now</Button>
              </div>
            </div>

            {/* Sample Supplier Status 3 */}
            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div className="flex items-center space-x-4">
                <div className="w-10 h-10 bg-orange-500 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-sm">OR</span>
                </div>
                <div>
                  <p className="font-medium">O'Reilly Auto Parts</p>
                  <p className="text-sm text-muted-foreground">28,934 parts cataloged</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="default" className="bg-green-500">Fresh</Badge>
                    <span className="text-xs text-muted-foreground">Updated 4 hours ago</span>
                  </div>
                </div>
              </div>
              <div className="text-right">
                <Button size="sm" variant="outline">Update Now</Button>
              </div>
            </div>

            {/* Sample Supplier Status 4 */}
            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div className="flex items-center space-x-4">
                <div className="w-10 h-10 bg-green-600 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-sm">NP</span>
                </div>
                <div>
                  <p className="font-medium">NAPA Auto Parts</p>
                  <p className="text-sm text-muted-foreground">38,742 parts cataloged</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="default" className="bg-yellow-500">Updating</Badge>
                    <span className="text-xs text-muted-foreground">In progress</span>
                  </div>
                </div>
              </div>
              <div className="text-right">
                <Button size="sm" variant="outline" disabled>Updating...</Button>
              </div>
            </div>

            {/* Sample Supplier Status 5 */}
            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div className="flex items-center space-x-4">
                <div className="w-10 h-10 bg-purple-500 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-sm">CP</span>
                </div>
                <div>
                  <p className="font-medium">CarParts.com</p>
                  <p className="text-sm text-muted-foreground">21,567 parts cataloged</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="destructive">Error</Badge>
                    <span className="text-xs text-muted-foreground">Update failed</span>
                  </div>
                </div>
              </div>
              <div className="text-right">
                <Button size="sm" variant="outline">Retry</Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
