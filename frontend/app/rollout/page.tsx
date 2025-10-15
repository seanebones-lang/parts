import { Suspense } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { 
  CheckCircle, 
  Clock, 
  AlertTriangle, 
  Users, 
  TrendingUp, 
  MapPin,
  Calendar,
  Target,
  BarChart3,
  Building2,
  Zap,
  Award
} from 'lucide-react'

export default function RolloutPage() {
  return (
    <div className="container mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-foreground mb-2">
          Multi-Location Rollout Dashboard
        </h1>
        <p className="text-xl text-muted-foreground">
          Enterprise deployment progress across all 7 dealership locations
        </p>
      </div>

      {/* Rollout Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Locations</CardTitle>
            <Building2 className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">7</div>
            <p className="text-xs text-muted-foreground">
              2 deployed • 1 in progress • 4 pending
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Rollout Progress</CardTitle>
            <Target className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">28.6%</div>
            <p className="text-xs text-muted-foreground">
              2 of 7 locations deployed
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Staff Trained</CardTitle>
            <Users className="h-4 w-4 text-purple-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">15/28</div>
            <p className="text-xs text-muted-foreground">
              53.6% training completion
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Enterprise Uptime</CardTitle>
            <Zap className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">99.7%</div>
            <p className="text-xs text-muted-foreground">
              Across all deployed locations
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Rollout Timeline */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle>Rollout Timeline & Status</CardTitle>
          <CardDescription>Deployment progress across all 7 locations</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Location 1 - Completed */}
            <div className="flex items-center justify-between p-4 border rounded-lg bg-green-50">
              <div className="flex items-center space-x-4">
                <CheckCircle className="h-5 w-5 text-green-500" />
                <div>
                  <p className="font-medium">Location 1 - Downtown</p>
                  <p className="text-sm text-muted-foreground">Deployed Nov 1, 2024 • Pilot completed successfully</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="default" className="bg-green-500">Operational</Badge>
                    <span className="text-sm text-muted-foreground">3/3 staff trained</span>
                  </div>
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm font-bold text-green-600">100%</p>
                <p className="text-xs text-muted-foreground">Complete</p>
              </div>
            </div>

            {/* Location 2 - In Progress */}
            <div className="flex items-center justify-between p-4 border rounded-lg bg-blue-50">
              <div className="flex items-center space-x-4">
                <Clock className="h-5 w-5 text-blue-500" />
                <div>
                  <p className="font-medium">Location 2 - Northside</p>
                  <p className="text-sm text-muted-foreground">Deploying • Scheduled Nov 22, 2024</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="default" className="bg-blue-500">In Progress</Badge>
                    <span className="text-sm text-muted-foreground">3/4 staff trained</span>
                  </div>
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm font-bold text-blue-600">75%</p>
                <p className="text-xs text-muted-foreground">Staff training</p>
              </div>
            </div>

            {/* Location 3 - Pre-deployment */}
            <div className="flex items-center justify-between p-4 border rounded-lg bg-yellow-50">
              <div className="flex items-center space-x-4">
                <AlertTriangle className="h-5 w-5 text-yellow-500" />
                <div>
                  <p className="font-medium">Location 3 - Southside</p>
                  <p className="text-sm text-muted-foreground">Pre-deployment • Scheduled Dec 6, 2024</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="default" className="bg-yellow-500">Preparing</Badge>
                    <span className="text-sm text-muted-foreground">1/4 staff trained</span>
                  </div>
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm font-bold text-yellow-600">25%</p>
                <p className="text-xs text-muted-foreground">System config</p>
              </div>
            </div>

            {/* Location 4 - Planning */}
            <div className="flex items-center justify-between p-4 border rounded-lg bg-gray-50">
              <div className="flex items-center space-x-4">
                <Calendar className="h-5 w-5 text-gray-500" />
                <div>
                  <p className="font-medium">Location 4 - Eastside</p>
                  <p className="text-sm text-muted-foreground">Planning • Scheduled Dec 20, 2024</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="secondary">Planning</Badge>
                    <span className="text-sm text-muted-foreground">0/4 staff trained</span>
                  </div>
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm font-bold text-gray-600">10%</p>
                <p className="text-xs text-muted-foreground">Initial planning</p>
              </div>
            </div>

            {/* Location 5 - Planning */}
            <div className="flex items-center justify-between p-4 border rounded-lg bg-gray-50">
              <div className="flex items-center space-x-4">
                <Calendar className="h-5 w-5 text-gray-500" />
                <div>
                  <p className="font-medium">Location 5 - Westside</p>
                  <p className="text-sm text-muted-foreground">Planning • Scheduled Jan 3, 2025</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="secondary">Planning</Badge>
                    <span className="text-sm text-muted-foreground">0/4 staff trained</span>
                  </div>
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm font-bold text-gray-600">5%</p>
                <p className="text-xs text-muted-foreground">Initial planning</p>
              </div>
            </div>

            {/* Location 6 - Planning */}
            <div className="flex items-center justify-between p-4 border rounded-lg bg-gray-50">
              <div className="flex items-center space-x-4">
                <Calendar className="h-5 w-5 text-gray-500" />
                <div>
                  <p className="font-medium">Location 6 - Central</p>
                  <p className="text-sm text-muted-foreground">Planning • Scheduled Jan 17, 2025</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="secondary">Planning</Badge>
                    <span className="text-sm text-muted-foreground">0/4 staff trained</span>
                  </div>
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm font-bold text-gray-600">0%</p>
                <p className="text-xs text-muted-foreground">Waiting</p>
              </div>
            </div>

            {/* Location 7 - Planning */}
            <div className="flex items-center justify-between p-4 border rounded-lg bg-gray-50">
              <div className="flex items-center space-x-4">
                <Calendar className="h-5 w-5 text-gray-500" />
                <div>
                  <p className="font-medium">Location 7 - Airport</p>
                  <p className="text-sm text-muted-foreground">Planning • Scheduled Jan 31, 2025</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="secondary">Planning</Badge>
                    <span className="text-sm text-muted-foreground">0/4 staff trained</span>
                  </div>
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm font-bold text-gray-600">0%</p>
                <p className="text-xs text-muted-foreground">Final deployment</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Enterprise Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <Card>
          <CardHeader>
            <CardTitle>Enterprise Performance</CardTitle>
            <CardDescription>Aggregated metrics across all locations</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Total Emails Processed</span>
                <span className="text-sm font-bold">8,247</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Total Orders Completed</span>
                <span className="text-sm font-bold">3,891</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Avg Response Time</span>
                <span className="text-sm font-bold">52 seconds</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Overall Satisfaction</span>
                <span className="text-sm font-bold">4.1/5</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">System Uptime</span>
                <span className="text-sm font-bold text-green-600">99.7%</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Rollout Impact</CardTitle>
            <CardDescription>Business impact from successful deployments</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Staff Reduction</span>
                <Badge variant="default" className="bg-green-500">60% reduction</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Response Time</span>
                <Badge variant="default" className="bg-blue-500">97% faster</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Order Processing</span>
                <Badge variant="default" className="bg-purple-500">84% faster</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Customer Satisfaction</span>
                <Badge variant="default" className="bg-yellow-500">+0.9 points</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Annual Savings</span>
                <span className="text-sm font-bold text-green-600">$750,000</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Deployment Milestones */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle>Deployment Milestones</CardTitle>
          <CardDescription>Key milestones and achievements</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="text-center p-4 border rounded-lg">
              <Award className="h-8 w-8 mx-auto mb-2 text-green-500" />
              <p className="font-medium">Pilot Success</p>
              <p className="text-sm text-muted-foreground">Location 1 exceeded all targets</p>
            </div>
            <div className="text-center p-4 border rounded-lg">
              <Users className="h-8 w-8 mx-auto mb-2 text-blue-500" />
              <p className="font-medium">Staff Training</p>
              <p className="text-sm text-muted-foreground">15 of 28 staff trained</p>
            </div>
            <div className="text-center p-4 border rounded-lg">
              <TrendingUp className="h-8 w-8 mx-auto mb-2 text-purple-500" />
              <p className="font-medium">Performance</p>
              <p className="text-sm text-muted-foreground">97% faster responses</p>
            </div>
            <div className="text-center p-4 border rounded-lg">
              <BarChart3 className="h-8 w-8 mx-auto mb-2 text-orange-500" />
              <p className="font-medium">ROI</p>
              <p className="text-sm text-muted-foreground">$750k annual savings</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Next Steps and Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Next Steps & Actions</CardTitle>
          <CardDescription>Upcoming deployment activities and recommendations</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="font-medium mb-3">Immediate Actions</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>• Complete Location 2 staff training by Nov 22</li>
                <li>• Begin Location 3 system configuration</li>
                <li>• Schedule Location 4 training sessions</li>
                <li>• Optimize system for multi-location load</li>
                <li>• Document lessons learned from Location 1</li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium mb-3">Recommendations</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>• Continue 2-week deployment intervals</li>
                <li>• Increase training resources for Locations 4-5</li>
                <li>• Implement cross-location knowledge sharing</li>
                <li>• Prepare for peak season scaling</li>
                <li>• Monitor system performance under load</li>
              </ul>
            </div>
          </div>
          
          <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
            <Button variant="outline" className="h-auto p-4 flex flex-col items-center space-y-2">
              <MapPin className="h-6 w-6" />
              <span className="text-sm">Start Location 3 Deployment</span>
            </Button>
            <Button variant="outline" className="h-auto p-4 flex flex-col items-center space-y-2">
              <Users className="h-6 w-6" />
              <span className="text-sm">Schedule Training</span>
            </Button>
            <Button variant="outline" className="h-auto p-4 flex flex-col items-center space-y-2">
              <BarChart3 className="h-6 w-6" />
              <span className="text-sm">Generate Rollout Report</span>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
