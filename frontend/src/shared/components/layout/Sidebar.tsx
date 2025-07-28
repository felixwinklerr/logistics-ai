import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { 
  LayoutDashboard,
  Package,
  Truck,
  Users,
  BarChart3,
  Settings,
  HelpCircle,
  X,
  Wifi,
  WifiOff
} from 'lucide-react';
import { Button } from '@/shared/components/ui/button';
import { Badge } from '@/shared/components/ui/badge';
import { useRealtimeStatus } from '@/features/orders/hooks/useOrderRealtime';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

const navigation = [
  {
    name: 'Dashboard',
    href: '/dashboard',
    icon: LayoutDashboard,
    current: false,
  },
  {
    name: 'Orders',
    href: '/orders',
    icon: Package,
    current: false,
    badge: 'New',
  },
  {
    name: 'Subcontractors',
    href: '/subcontractors',
    icon: Truck,
    current: false,
  },
  {
    name: 'Analytics',
    href: '/analytics',
    icon: BarChart3,
    current: false,
  },
  {
    name: 'Team',
    href: '/team',
    icon: Users,
    current: false,
  },
];

const secondaryNavigation = [
  {
    name: 'Settings',
    href: '/settings',
    icon: Settings,
  },
  {
    name: 'Help',
    href: '/help',
    icon: HelpCircle,
  },
];

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const location = useLocation();
  const { isConnected, statusText, statusColor } = useRealtimeStatus();

  const isActive = (path: string) => {
    return location.pathname.startsWith(path);
  };

  const getStatusIcon = () => {
    return isConnected ? Wifi : WifiOff;
  };

  const StatusIcon = getStatusIcon();

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-50 bg-slate-900/80 backdrop-blur-sm md:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <div
        className={`fixed inset-y-0 left-0 z-50 w-72 bg-white shadow-xl transform transition-transform duration-300 ease-in-out md:translate-x-0 md:static md:inset-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex h-full flex-col">
          {/* Header */}
          <div className="flex h-16 items-center justify-between px-6 border-b border-slate-200">
            <div className="flex items-center space-x-2">
              <Truck className="h-8 w-8 text-blue-600" />
              <span className="text-lg font-bold text-slate-900">
                Romanian Freight
              </span>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="md:hidden"
            >
              <X className="h-5 w-5" />
            </Button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
            {navigation.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.href);
              
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  onClick={onClose}
                  className={`group flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
                    active
                      ? 'bg-blue-50 text-blue-700 border-r-2 border-blue-700'
                      : 'text-slate-700 hover:text-slate-900 hover:bg-slate-50'
                  }`}
                >
                  <Icon
                    className={`mr-3 h-5 w-5 flex-shrink-0 ${
                      active ? 'text-blue-500' : 'text-slate-400 group-hover:text-slate-500'
                    }`}
                  />
                  <span className="flex-1">{item.name}</span>
                  {item.badge && (
                    <Badge
                      variant="secondary"
                      className="ml-auto bg-blue-100 text-blue-800 text-xs"
                    >
                      {item.badge}
                    </Badge>
                  )}
                </Link>
              );
            })}

            {/* Divider */}
            <div className="my-6 border-t border-slate-200" />

            {/* Secondary navigation */}
            {secondaryNavigation.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.href);
              
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  onClick={onClose}
                  className={`group flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
                    active
                      ? 'bg-slate-100 text-slate-900'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                  }`}
                >
                  <Icon className="mr-3 h-5 w-5 flex-shrink-0 text-slate-400 group-hover:text-slate-500" />
                  {item.name}
                </Link>
              );
            })}
          </nav>

          {/* Real-time connection status */}
          <div className="border-t border-slate-200 p-4">
            <div className="flex items-center space-x-3">
              <div
                className={`flex items-center space-x-2 px-3 py-2 rounded-lg ${
                  statusColor === 'green'
                    ? 'bg-green-50 text-green-700'
                    : statusColor === 'yellow'
                    ? 'bg-yellow-50 text-yellow-700'
                    : 'bg-red-50 text-red-700'
                }`}
              >
                <StatusIcon className="h-4 w-4" />
                <span className="text-sm font-medium">{statusText}</span>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="border-t border-slate-200 p-4">
            <p className="text-xs text-slate-500 text-center">
              Romanian Freight Management System
            </p>
            <p className="text-xs text-slate-400 text-center mt-1">
              Version 1.0.0
            </p>
          </div>
        </div>
      </div>
    </>
  );
};

export default Sidebar; 