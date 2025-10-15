import { Suspense } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Search, Package, Filter, Download, Upload, Bot } from 'lucide-react'

export default function PartsPage() {
  return (
    <div className="container mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-foreground mb-2">
          Parts Catalog
        </h1>
        <p className="text-xl text-muted-foreground">
          AI-powered semantic search and parts management
        </p>
      </div>

      {/* Search Interface */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="h-5 w-5" />
            AI Parts Search
          </CardTitle>
          <CardDescription>
            Search parts using natural language - "brake pads for 2020 Honda Civic"
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex gap-4">
              <div className="flex-1">
                <input
                  type="text"
                  placeholder="Search for parts using natural language..."
                  className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              <Button className="px-8">
                <Bot className="h-4 w-4 mr-2" />
                AI Search
              </Button>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <select className="px-4 py-2 border rounded-lg">
                <option value="">All Makes</option>
                <option value="honda">Honda</option>
                <option value="toyota">Toyota</option>
                <option value="ford">Ford</option>
              </select>
              
              <select className="px-4 py-2 border rounded-lg">
                <option value="">All Models</option>
                <option value="civic">Civic</option>
                <option value="accord">Accord</option>
                <option value="cr-v">CR-V</option>
              </select>
              
              <select className="px-4 py-2 border rounded-lg">
                <option value="">All Years</option>
                <option value="2023">2023</option>
                <option value="2022">2022</option>
                <option value="2021">2021</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Search Results */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mb-8">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Filter className="h-5 w-5" />
              Filters
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium">Category</label>
                <select className="w-full mt-1 px-3 py-2 border rounded-md">
                  <option value="">All Categories</option>
                  <option value="brakes">Brakes</option>
                  <option value="engine">Engine</option>
                  <option value="tires">Tires</option>
                </select>
              </div>
              
              <div>
                <label className="text-sm font-medium">Manufacturer</label>
                <select className="w-full mt-1 px-3 py-2 border rounded-md">
                  <option value="">All Manufacturers</option>
                  <option value="brembo">Brembo</option>
                  <option value="fram">Fram</option>
                  <option value="ngk">NGK</option>
                </select>
              </div>
              
              <div>
                <label className="text-sm font-medium">Price Range</label>
                <div className="mt-1 space-y-2">
                  <input type="number" placeholder="Min" className="w-full px-3 py-2 border rounded-md" />
                  <input type="number" placeholder="Max" className="w-full px-3 py-2 border rounded-md" />
                </div>
              </div>
              
              <div>
                <label className="text-sm font-medium">Availability</label>
                <div className="mt-1 space-y-1">
                  <label className="flex items-center">
                    <input type="checkbox" className="mr-2" />
                    In Stock Only
                  </label>
                  <label className="flex items-center">
                    <input type="checkbox" className="mr-2" />
                    Cross-Location Available
                  </label>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="lg:col-span-3">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Search Results</CardTitle>
                  <CardDescription>
                    Found 247 parts matching your search
                  </CardDescription>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm">
                    <Download className="h-4 w-4 mr-2" />
                    Export
                  </Button>
                  <Button variant="outline" size="sm">
                    <Upload className="h-4 w-4 mr-2" />
                    Import
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {/* Sample Search Results */}
                <div className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50">
                  <div className="flex items-center space-x-4">
                    <Package className="h-8 w-8 text-muted-foreground" />
                    <div>
                      <p className="font-medium">Brake Pad Set - Front</p>
                      <p className="text-sm text-muted-foreground">Brembo • Part #BRK123 • Compatible with 2019-2023 Honda Civic</p>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant="default">In Stock</Badge>
                        <Badge variant="outline">Brakes</Badge>
                        <Badge variant="outline">Honda</Badge>
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-medium">$89.99</p>
                    <p className="text-sm text-muted-foreground">25 available</p>
                    <Button size="sm" className="mt-2">Add to Cart</Button>
                  </div>
                </div>

                <div className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50">
                  <div className="flex items-center space-x-4">
                    <Package className="h-8 w-8 text-muted-foreground" />
                    <div>
                      <p className="font-medium">Oil Filter</p>
                      <p className="text-sm text-muted-foreground">Fram • Part #FLT456 • Compatible with 2019-2023 Honda Civic</p>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant="default">In Stock</Badge>
                        <Badge variant="outline">Engine</Badge>
                        <Badge variant="outline">Honda</Badge>
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-medium">$12.99</p>
                    <p className="text-sm text-muted-foreground">50 available</p>
                    <Button size="sm" className="mt-2">Add to Cart</Button>
                  </div>
                </div>

                <div className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50">
                  <div className="flex items-center space-x-4">
                    <Package className="h-8 w-8 text-muted-foreground" />
                    <div>
                      <p className="font-medium">Spark Plug Set</p>
                      <p className="text-sm text-muted-foreground">NGK • Part #SPK789 • Compatible with 2019-2023 Honda Civic</p>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant="secondary">Low Stock</Badge>
                        <Badge variant="outline">Engine</Badge>
                        <Badge variant="outline">Honda</Badge>
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-medium">$24.99</p>
                    <p className="text-sm text-muted-foreground">3 available</p>
                    <Button size="sm" className="mt-2">Add to Cart</Button>
                  </div>
                </div>

                <div className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50">
                  <div className="flex items-center space-x-4">
                    <Package className="h-8 w-8 text-muted-foreground" />
                    <div>
                      <p className="font-medium">Tire 225/60R16</p>
                      <p className="text-sm text-muted-foreground">Michelin • Part #TIR012 • Compatible with 2019-2023 Honda Civic</p>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant="destructive">Out of Stock</Badge>
                        <Badge variant="outline">Tires</Badge>
                        <Badge variant="outline">Honda</Badge>
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-medium">$149.99</p>
                    <p className="text-sm text-muted-foreground">Available at other locations</p>
                    <Button size="sm" variant="outline" className="mt-2">Transfer Request</Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* AI Insights */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bot className="h-5 w-5" />
            AI Insights & Recommendations
          </CardTitle>
          <CardDescription>
            AI-powered analysis of your parts catalog and search patterns
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="p-4 bg-blue-50 rounded-lg">
              <h4 className="font-medium text-blue-900 mb-2">Popular Searches</h4>
              <ul className="text-sm text-blue-700 space-y-1">
                <li>• "brake pads honda civic" (47 searches)</li>
                <li>• "oil filter 2020" (32 searches)</li>
                <li>• "spark plugs toyota" (28 searches)</li>
              </ul>
            </div>
            
            <div className="p-4 bg-green-50 rounded-lg">
              <h4 className="font-medium text-green-900 mb-2">Compatibility Insights</h4>
              <ul className="text-sm text-green-700 space-y-1">
                <li>• 89% of Honda Civic parts are cross-compatible</li>
                <li>• Brake pads fit 2019-2023 model years</li>
                <li>• Oil filters compatible across all engines</li>
              </ul>
            </div>
            
            <div className="p-4 bg-yellow-50 rounded-lg">
              <h4 className="font-medium text-yellow-900 mb-2">Inventory Optimization</h4>
              <ul className="text-sm text-yellow-700 space-y-1">
                <li>• Consider stocking more brake pads</li>
                <li>• Oil filters have high turnover rate</li>
                <li>• Spark plugs need reordering soon</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
