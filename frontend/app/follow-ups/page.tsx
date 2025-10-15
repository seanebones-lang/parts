import { Suspense } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Clock, CheckCircle, AlertTriangle, Mail, Phone, MessageSquare, TrendingUp, Calendar } from 'lucide-react'

export default function FollowUpsPage() {
  return (
    <div className="container mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-foreground mb-2">
          Follow-up Automation
        </h1>
        <p className="text-xl text-muted-foreground">
          Automated customer follow-ups and retention management
        </p>
      </div>

      {/* Follow-up Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending Follow-ups</CardTitle>
            <Clock className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">47</div>
            <p className="text-xs text-muted-foreground">
              Scheduled for next 24 hours
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
            <CardTitle className="text-sm font-medium">Response Rate</CardTitle>
            <TrendingUp className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">68%</div>
            <p className="text-xs text-muted-foreground">
              Customer response rate
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Satisfaction Score</CardTitle>
            <MessageSquare className="h-4 w-4 text-purple-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">4.2/5</div>
            <p className="text-xs text-muted-foreground">
              Average satisfaction
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Follow-up Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <Card>
          <CardHeader>
            <CardTitle>Follow-up Actions</CardTitle>
            <CardDescription>
              Common follow-up operations
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <Button className="w-full" variant="outline">
                <Clock className="h-4 w-4 mr-2" />
                Schedule Follow-up
              </Button>
              <Button className="w-full" variant="outline">
                <Mail className="h-4 w-4 mr-2" />
                Send Quote Reminder
              </Button>
              <Button className="w-full" variant="outline">
                <AlertTriangle className="h-4 w-4 mr-2" />
                Payment Reminder
              </Button>
              <Button className="w-full" variant="outline">
                <MessageSquare className="h-4 w-4 mr-2" />
                Satisfaction Survey
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Follow-up Types</CardTitle>
            <CardDescription>
              Current follow-up distribution
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Quote Follow-ups</span>
                <Badge variant="default">450</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Payment Reminders</span>
                <Badge variant="default">320</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Shipping Updates</span>
                <Badge variant="default">280</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Satisfaction Surveys</span>
                <Badge variant="default">200</Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
            <CardDescription>
              Latest follow-up activity
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center space-x-4">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <div className="flex-1">
                  <p className="text-sm font-medium">Quote follow-up sent</p>
                  <p className="text-xs text-muted-foreground">John Smith • 2 minutes ago</p>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                <div className="flex-1">
                  <p className="text-sm font-medium">Payment reminder sent</p>
                  <p className="text-xs text-muted-foreground">Sarah Johnson • 5 minutes ago</p>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
                <div className="flex-1">
                  <p className="text-sm font-medium">Satisfaction survey sent</p>
                  <p className="text-xs text-muted-foreground">Mike Davis • 8 minutes ago</p>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
                <div className="flex-1">
                  <p className="text-sm font-medium">Shipping update sent</p>
                  <p className="text-xs text-muted-foreground">Lisa Wilson • 12 minutes ago</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Follow-up Schedule */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle>Follow-up Schedule</CardTitle>
          <CardDescription>
            Upcoming and overdue follow-ups
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Sample Upcoming Follow-up 1 */}
            <div className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50">
              <div className="flex items-center space-x-4">
                <Clock className="h-5 w-5 text-yellow-500" />
                <div>
                  <p className="font-medium">Quote Follow-up</p>
                  <p className="text-sm text-muted-foreground">John Smith • Quote #Q000123 • Due in 2 hours</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="default" className="bg-yellow-500">Upcoming</Badge>
                    <span className="text-sm text-muted-foreground">High Priority</span>
                  </div>
                </div>
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="outline">Send Now</Button>
                <Button size="sm" variant="outline">Reschedule</Button>
              </div>
            </div>

            {/* Sample Upcoming Follow-up 2 */}
            <div className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50">
              <div className="flex items-center space-x-4">
                <AlertTriangle className="h-5 w-5 text-orange-500" />
                <div>
                  <p className="font-medium">Payment Reminder</p>
                  <p className="text-sm text-muted-foreground">Sarah Johnson • Invoice #INV000456 • Due in 4 hours</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="default" className="bg-orange-500">Due Today</Badge>
                    <span className="text-sm text-muted-foreground">Normal Priority</span>
                  </div>
                </div>
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="outline">Send Now</Button>
                <Button size="sm" variant="outline">Reschedule</Button>
              </div>
            </div>

            {/* Sample Overdue Follow-up */}
            <div className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50 bg-red-50">
              <div className="flex items-center space-x-4">
                <AlertTriangle className="h-5 w-5 text-red-500" />
                <div>
                  <p className="font-medium">Satisfaction Survey</p>
                  <p className="text-sm text-muted-foreground">Mike Davis • Order #ORD000789 • Overdue by 2 hours</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="destructive">Overdue</Badge>
                    <span className="text-sm text-muted-foreground">High Priority</span>
                  </div>
                </div>
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="outline">Send Now</Button>
                <Button size="sm" variant="outline">Cancel</Button>
              </div>
            </div>

            {/* Sample Completed Follow-up */}
            <div className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50 bg-green-50">
              <div className="flex items-center space-x-4">
                <CheckCircle className="h-5 w-5 text-green-500" />
                <div>
                  <p className="font-medium">Shipping Update</p>
                  <p className="text-sm text-muted-foreground">Lisa Wilson • Shipment #1Z123456 • Completed 1 hour ago</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="default" className="bg-green-500">Completed</Badge>
                    <span className="text-sm text-muted-foreground">Customer Responded</span>
                  </div>
                </div>
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="outline">View Details</Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Follow-up Effectiveness */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <Card>
          <CardHeader>
            <CardTitle>Follow-up Effectiveness</CardTitle>
            <CardDescription>
              Response rates and conversion metrics
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Quote Follow-ups</span>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold">72%</span>
                  <span className="text-xs text-muted-foreground">response rate</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Payment Reminders</span>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold">68%</span>
                  <span className="text-xs text-muted-foreground">response rate</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Satisfaction Surveys</span>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold">45%</span>
                  <span className="text-xs text-muted-foreground">completion rate</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Shipping Updates</span>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold">85%</span>
                  <span className="text-xs text-muted-foreground">open rate</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Response Types</CardTitle>
            <CardDescription>
              Customer response distribution
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Positive Responses</span>
                <div className="flex items-center gap-2">
                  <Badge variant="default" className="bg-green-500">45%</Badge>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Neutral Responses</span>
                <div className="flex items-center gap-2">
                  <Badge variant="default" className="bg-blue-500">23%</Badge>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Negative Responses</span>
                <div className="flex items-center gap-2">
                  <Badge variant="destructive">8%</Badge>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">No Response</span>
                <div className="flex items-center gap-2">
                  <Badge variant="secondary">24%</Badge>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Follow-up Templates */}
      <Card>
        <CardHeader>
          <CardTitle>Follow-up Templates</CardTitle>
          <CardDescription>
            Email templates for different follow-up types
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Quote Follow-up Template */}
            <div className="border rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-medium">Quote Follow-up</h4>
                <Badge variant="outline">24h, 3d, 1w</Badge>
              </div>
              <p className="text-sm text-muted-foreground mb-3">
                "Thank you for your interest in our parts and services. We've prepared a detailed quote for you..."
              </p>
              <div className="flex gap-2">
                <Button size="sm" variant="outline">Edit Template</Button>
                <Button size="sm" variant="outline">Preview</Button>
              </div>
            </div>

            {/* Payment Reminder Template */}
            <div className="border rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-medium">Payment Reminder</h4>
                <Badge variant="outline">Due, +3d, +7d</Badge>
              </div>
              <p className="text-sm text-muted-foreground mb-3">
                "This is a friendly reminder that payment is due for your recent order..."
              </p>
              <div className="flex gap-2">
                <Button size="sm" variant="outline">Edit Template</Button>
                <Button size="sm" variant="outline">Preview</Button>
              </div>
            </div>

            {/* Shipping Update Template */}
            <div className="border rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-medium">Shipping Update</h4>
                <Badge variant="outline">Shipped, In Transit, Delivered</Badge>
              </div>
              <p className="text-sm text-muted-foreground mb-3">
                "Great news! Your order has been shipped and is on its way to you..."
              </p>
              <div className="flex gap-2">
                <Button size="sm" variant="outline">Edit Template</Button>
                <Button size="sm" variant="outline">Preview</Button>
              </div>
            </div>

            {/* Satisfaction Survey Template */}
            <div className="border rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-medium">Satisfaction Survey</h4>
                <Badge variant="outline">3d post-delivery</Badge>
              </div>
              <p className="text-sm text-muted-foreground mb-3">
                "We hope you're enjoying your recent purchase! Your feedback is important to us..."
              </p>
              <div className="flex gap-2">
                <Button size="sm" variant="outline">Edit Template</Button>
                <Button size="sm" variant="outline">Preview</Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
