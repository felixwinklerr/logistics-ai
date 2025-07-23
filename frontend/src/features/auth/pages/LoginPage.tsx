import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card';
import { Button } from '@/shared/components/ui/button';
import { Input } from '@/shared/components/ui/input';

export const LoginPage: React.FC = () => {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-100 px-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl font-bold text-slate-900">
            Login to Logistics AI
          </CardTitle>
          <p className="text-slate-600 mt-2">
            Romanian Freight Forwarder Management System
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Email
            </label>
            <Input 
              type="email" 
              placeholder="your@email.com"
              className="w-full"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Password
            </label>
            <Input 
              type="password" 
              placeholder="••••••••"
              className="w-full"
            />
          </div>
          <Button className="w-full">
            Sign In
          </Button>
          <p className="text-center text-sm text-slate-600">
            Demo credentials will be provided for testing
          </p>
        </CardContent>
      </Card>
    </div>
  );
}; 