import { Suspense } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { 
  CheckCircle, 
  AlertTriangle, 
  Clock, 
  Users, 
  TrendingUp, 
  Activity,
  Monitor,
  Brain,
  Mail,
  ShoppingCart,
  DollarSign,
  Star,
  FileText,
  Download
} from 'lucide-react'

export default function DeploymentPage() {
  return (
    <div className="container mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-foreground mb-2">
          Pilot Deployment Dashboard
        </h1>
        <p className="text-xl text-muted-foreground">
          Location 1 pilot deployment monitoring and management
        </p>
      </div>

      {/* Deployment Status Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Deployment Status</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">Active</div>
            <p className="text-xs text-muted-foreground">
              Deployed 14 days ago
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">System Health</CardTitle>
            <Monitor className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">99.8%</div>
            <p className="text-xs text-muted-foreground">
              Uptime • 145ms response time
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Staff Training</CardTitle>
            <Users className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">100%</div>
            <p className="text-xs text-muted-foreground">
              3/3 staff trained • 1 module pending
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Satisfaction Score</CardTitle>
            <Star className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">4.2/5</div>
            <p className="text-xs text-muted-foreground">
              Staff satisfaction rating
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Performance Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <Card>
          <CardHeader>
            <CardTitle>Performance Improvements</CardTitle>
            <CardDescription>Before vs After deployment metrics</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Email Response Time</span>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">2.5 hours →</span>
                  <span className="text-sm font-bold text-green-600">47 seconds</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Order Processing Time</span>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">30 min →</span>
                  <span className="text-sm font-bold text-green-600">4.8 minutes</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Processing Accuracy</span>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">85% →</span>
                  <span className="text-sm font-bold text-green-600">95.2%</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Manual Intervention</span>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">95% →</span>
                  <span className="text-sm font-bold text-green-600">12%</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Staff Efficiency Gains</CardTitle>
            <CardDescription>Time savings and productivity improvements</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Hours per Order</span>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">0.5h →</span>
                  <span className="text-sm font-bold text-green-600">0.1h</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Weekly Overtime</span>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">15h →</span>
                  <span className="text-sm font-bold text-green-600">2h</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Staff Satisfaction</span>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">3.2/5 →</span>
                  <span className="text-sm font-bold text-green-600">4.2/5</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Error Rate</span>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">8% →</span>
                  <span className="text-sm font-bold text-green-600">2.1%</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Training Progress */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle>Staff Training Progress</CardTitle>
          <CardDescription>Training completion status for Location 1 staff</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Completed Training Modules */}
            <div className="flex items-center justify-between p-4 border rounded-lg bg-green-50">
              <div className="flex items-center space-x-4">
                <CheckCircle className="h-5 w-5 text-green-500" />
                <div>
                  <p className="font-medium">System Overview</p>
                  <p className="text-sm text-muted-foreground">Completed by all staff • Nov 1, 2024</p>
                </div>
              </div>
              <Badge variant="default" className="bg-green-500">Completed</Badge>
            </div>

            <div className="flex items-center justify-between p-4 border rounded-lg bg-green-50">
              <div className="flex items-center space-x-4">
                <CheckCircle className="h-5 w-5 text-green-500" />
                <div>
                  <p className="font-medium">Email Management</p>
                  <p className="text-sm text-muted-foreground">Completed by all staff • Nov 2, 2024</p>
                </div>
              </div>
              <Badge variant="default" className="bg-green-500">Completed</Badge>
            </div>

            <div className="flex items-center justify-between p-4 border rounded-lg bg-green-50">
              <div className="flex items-center space-x-4">
                <CheckCircle className="h-5 w-5 text-green-500" />
                <div>
                  <p className="font-medium">Order Processing</p>
                  <p className="text-sm text-muted-foreground">Completed by all staff • Nov 3, 2024</p>
                </div>
              </div>
              <Badge variant="default" className="bg-green-500">Completed</Badge>
            </div>

            {/* In Progress Training */}
            <div className="flex items-center justify-between p-4 border rounded-lg bg-yellow-50">
              <div className="flex items-center space-x-4">
                <Clock className="h-5 w-5 text-yellow-500" />
                <div>
                  <p className="font-medium">Exception Handling</p>
                  <p className="text-sm text-muted-foreground">Completed by 2/3 staff • Next session: Nov 15, 2024</p>
                </div>
              </div>
              <Badge variant="default" className="bg-yellow-500">In Progress</Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Feedback and Issues */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <Card>
          <CardHeader>
            <CardTitle>Staff Feedback</CardTitle>
            <CardDescription>Feedback from Location 1 staff</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <h4 className="font-medium mb-2">Positive Feedback</h4>
                <ul className="text-sm text-muted-foreground space-y-1">
                  <li>• "System processes emails much faster than manual routing"</li>
                  <li>• "AI classification is very accurate"</li>
                  <li>• "Order processing is streamlined and efficient"</li>
                  <li>• "Real-time inventory updates are helpful"</li>
                </ul>
              </div>
              <div>
                <h4 className="font-medium mb-2">Areas for Improvement</h4>
                <ul className="text-sm text-muted-foreground space-y-1">
                  <li>• "Need better handling of complex multi-part orders"</li>
                  <li>• "Some email threads get lost in processing"</li>
                  <li>• "Would like more detailed error messages"</li>
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Reported Issues</CardTitle>
            <CardDescription>Current issues and their status</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 border rounded-lg">
                <div>
                  <p className="font-medium text-sm">Timeout on large orders</p>
                  <p className="text-xs text-muted-foreground">2-3 times per week • Medium severity</p>
                </div>
                <Badge variant="default" className="bg-orange-500">Investigating</Badge>
              </div>
              <div className="flex items-center justify-between p-3 border rounded-lg">
                <div>
                  <p className="font-medium text-sm">Email attachment processing</p>
                  <p className="text-xs text-muted-foreground">Once per week • Low severity</p>
                </div>
                <Badge variant="secondary">Known Issue</Badge>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* System Health Monitor */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle>System Health Monitor</CardTitle>
          <CardDescription>Real-time system status and performance</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <span className="text-sm font-medium">API Status</span>
              </div>
              <Badge variant="default" className="bg-green-500">Healthy</Badge>
            </div>
            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <span className="text-sm font-medium">Database</span>
              </div>
              <Badge variant="default" className="bg-green-500">Healthy</Badge>
            </div>
            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <span className="text-sm font-medium">AI Service</span>
              </div>
              <Badge variant="default" className="bg-green-500">Healthy</Badge>
            </div>
            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <span className="text-sm font-medium">Email Service</span>
              </div>
              <Badge variant="default" className="bg-green-500">Healthy</Badge>
            </div>
          </div>
          
          <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="text-center p-3 border rounded-lg">
              <p className="text-2xl font-bold text-green-600">99.8%</p>
              <p className="text-sm text-muted-foreground">System Uptime</p>
            </div>
            <div className="text-center p-3 border rounded-lg">
              <p className="text-2xl font-bold text-blue-600">145ms</p>
              <p className="text-sm text-muted-foreground">Avg Response Time</p>
            </div>
            <div className="text-center p-3 border rounded-lg">
              <p className="text-2xl font-bold text-purple-600">0.2%</p>
              <p className="text-sm text-muted-foreground">Error Rate</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Actions and Reports */}
      <Card>
        <CardHeader>
          <CardTitle>Actions & Reports</CardTitle>
          <CardDescription>Deployment management actions and report generation</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Button variant="outline" className="h-auto p-4 flex flex-col items-center space-y-2">
              <FileText className="h-6 w-6" />
              <span className="text-sm">Generate Pilot Report</span>
            </Button>
            <Button variant="outline" className="h-auto p-4 flex flex-col items-center space-y-2">
              <Download className="h-6 w-6" />
              <span className="text-sm">Export Metrics</span>
            </Button>
            <Button variant="outline" className="h-auto p-4 flex flex-col items-center space-y-2">
              <Users className="h-6 w-6" />
              <span className="text-sm">Schedule Training</span>
            </Button>
            <Button variant="outline" className="h-auto p-4 flex flex-col items-center space-y-2">
              <TrendingUp className="h-6 w-6" />
              <span className="text-sm">Performance Review</span>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
