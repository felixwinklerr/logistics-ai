import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card';
import { Button } from '@/shared/components/ui/button';
import { Package, Truck, Euro, Clock } from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();

  const handleCreateOrder = () => {
    navigate('/orders/new');
  };

  const metrics = [
    {
      title: 'Total Orders',
      value: '127',
      change: '+12%',
      icon: Package,
      color: 'text-blue-600',
      bgColor: 'bg-blue-100',
    },
    {
      title: 'Active Transports',
      value: '23',
      change: '+5%',
      icon: Truck,
      color: 'text-green-600',
      bgColor: 'bg-green-100',
    },
    {
      title: 'Monthly Revenue',
      value: '€45,230',
      change: '+18%',
      icon: Euro,
      color: 'text-emerald-600',
      bgColor: 'bg-emerald-100',
    },
    {
      title: 'Pending Orders',
      value: '8',
      change: '-3%',
      icon: Clock,
      color: 'text-amber-600',
      bgColor: 'bg-amber-100',
    },
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
            <p className="text-slate-600 mt-1">
              Overview of your freight forwarding operations
            </p>
          </div>
          <Button onClick={handleCreateOrder}>
            Create New Order
          </Button>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {metrics.map((metric) => {
            const Icon = metric.icon;
            return (
              <Card key={metric.title}>
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-slate-600">
                        {metric.title}
                      </p>
                      <p className="text-2xl font-bold text-slate-900 mt-1">
                        {metric.value}
                      </p>
                      <p className={`text-sm mt-1 ${
                        metric.change.startsWith('+') ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {metric.change} from last month
                      </p>
                    </div>
                    <div className={`p-3 rounded-full ${metric.bgColor}`}>
                      <Icon className={`w-6 h-6 ${metric.color}`} />
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Recent Activity */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Recent Orders</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between py-2 border-b border-slate-100">
                  <div>
                    <p className="font-medium text-slate-900">#12345678</p>
                    <p className="text-sm text-slate-600">Bucharest → Cluj-Napoca</p>
                  </div>
                  <div className="text-right">
                    <p className="font-medium text-emerald-600">€1,250</p>
                    <p className="text-sm text-slate-500">2 hours ago</p>
                  </div>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-slate-100">
                  <div>
                    <p className="font-medium text-slate-900">#12345679</p>
                    <p className="text-sm text-slate-600">Timișoara → Constanța</p>
                  </div>
                  <div className="text-right">
                    <p className="font-medium text-emerald-600">€850</p>
                    <p className="text-sm text-slate-500">4 hours ago</p>
                  </div>
                </div>
                <div className="flex items-center justify-between py-2">
                  <div>
                    <p className="font-medium text-slate-900">#12345680</p>
                    <p className="text-sm text-slate-600">Iași → Brașov</p>
                  </div>
                  <div className="text-right">
                    <p className="font-medium text-emerald-600">€1,100</p>
                    <p className="text-sm text-slate-500">6 hours ago</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Urgent Actions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex items-center gap-3 p-3 bg-red-50 border border-red-200 rounded-lg">
                  <Clock className="w-5 h-5 text-red-600" />
                  <div className="flex-1">
                    <p className="font-medium text-red-900">3 orders awaiting assignment</p>
                    <p className="text-sm text-red-700">Pending for 2+ days</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                  <Package className="w-5 h-5 text-amber-600" />
                  <div className="flex-1">
                    <p className="font-medium text-amber-900">5 documents awaiting validation</p>
                    <p className="text-sm text-amber-700">POD and invoices</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <Euro className="w-5 h-5 text-blue-600" />
                  <div className="flex-1">
                    <p className="font-medium text-blue-900">2 payments overdue</p>
                    <p className="text-sm text-blue-700">Client invoices pending</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}; 