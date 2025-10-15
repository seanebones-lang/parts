import { Suspense } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Bot, Mail, MessageSquare, Users, Activity, Zap } from 'lucide-react'

export default function AIAgentsPage() {
  return (
    <div className="container mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-foreground mb-2">
          AI Agents Dashboard
        </h1>
        <p className="text-xl text-muted-foreground">
          Monitor and interact with the AI agent system
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* Active Agents */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bot className="h-5 w-5" />
              Active Agents
            </CardTitle>
            <CardDescription>
              Currently running AI agents
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Email Classifier</span>
                <Badge variant="default" className="bg-green-500">Active</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Customer Service</span>
                <Badge variant="default" className="bg-green-500">Active</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Supervisor</span>
                <Badge variant="default" className="bg-green-500">Active</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Parts Lookup</span>
                <Badge variant="secondary">Pending</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Pricing & Invoice</span>
                <Badge variant="secondary">Pending</Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Performance Metrics */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Performance Metrics
            </CardTitle>
            <CardDescription>
              Real-time agent performance
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <div className="text-2xl font-bold">94.2%</div>
                <p className="text-xs text-muted-foreground">Average Accuracy</p>
              </div>
              <div>
                <div className="text-2xl font-bold">1.2s</div>
                <p className="text-xs text-muted-foreground">Avg Response Time</p>
              </div>
              <div>
                <div className="text-2xl font-bold">847</div>
                <p className="text-xs text-muted-foreground">Emails Processed Today</p>
              </div>
              <div>
                <div className="text-2xl font-bold">$12.45</div>
                <p className="text-xs text-muted-foreground">AI Costs Today</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Agent Actions */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Zap className="h-5 w-5" />
              Quick Actions
            </CardTitle>
            <CardDescription>
              Test and interact with agents
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <Button className="w-full" variant="outline">
                <Mail className="h-4 w-4 mr-2" />
                Test Email Classification
              </Button>
              <Button className="w-full" variant="outline">
                <MessageSquare className="h-4 w-4 mr-2" />
                Test Customer Service
              </Button>
              <Button className="w-full" variant="outline">
                <Users className="h-4 w-4 mr-2" />
                Run Supervisor Workflow
              </Button>
              <Button className="w-full" variant="outline">
                <Activity className="h-4 w-4 mr-2" />
                View Agent Logs
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Recent Agent Activity</CardTitle>
            <CardDescription>
              Latest actions from AI agents
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center space-x-4">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <div className="flex-1">
                  <p className="text-sm font-medium">Email classified as parts_order</p>
                  <p className="text-xs text-muted-foreground">Confidence: 96% • 30 seconds ago</p>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                <div className="flex-1">
                  <p className="text-sm font-medium">Customer inquiry handled</p>
                  <p className="text-xs text-muted-foreground">Response sent • 2 minutes ago</p>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
                <div className="flex-1">
                  <p className="text-sm font-medium">Email routed to specialist</p>
                  <p className="text-xs text-muted-foreground">Parts lookup required • 5 minutes ago</p>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
                <div className="flex-1">
                  <p className="text-sm font-medium">Workflow completed</p>
                  <p className="text-xs text-muted-foreground">Customer notified • 8 minutes ago</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Agent Configuration</CardTitle>
            <CardDescription>
              Current system settings
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Primary LLM</span>
                <Badge variant="outline">Claude 3.5 Sonnet</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Fallback LLM</span>
                <Badge variant="outline">GPT-4 Turbo</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">LangGraph</span>
                <Badge variant="default" className="bg-green-500">Enabled</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Auto-escalation</span>
                <Badge variant="default" className="bg-green-500">Enabled</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Confidence Threshold</span>
                <span className="text-sm">85%</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
