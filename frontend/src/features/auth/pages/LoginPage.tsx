import React, { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useNavigate } from 'react-router-dom';
import * as z from 'zod';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card';
import { Button } from '@/shared/components/ui/button';
import { Input } from '@/shared/components/ui/input';
import { useAuth } from '@/shared/hooks/useAuth';
import { Loader2, AlertCircle } from 'lucide-react';

// Validation schema for login form
const loginSchema = z.object({
  email: z
    .string()
    .min(1, 'Email is required')
    .email('Please enter a valid email address'),
  password: z
    .string()
    .min(1, 'Password is required')
    .min(3, 'Password must be at least 3 characters'),
});

type LoginFormData = z.infer<typeof loginSchema>;

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { login, isAuthenticated, isLoading, loginError, clearError } = useAuth();

  // Form setup with validation
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    reset,
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: '',
      password: '',
    },
  });

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard');
    }
  }, [isAuthenticated, navigate]);

  // Clear error when component mounts or form changes
  useEffect(() => {
    clearError();
  }, [clearError]);

  // Handle form submission
  const onSubmit = async (data: LoginFormData) => {
    try {
      clearError();
      await login(data.email, data.password);
      // Navigation will happen automatically via useEffect
    } catch (error) {
      // Error is handled by the auth store and displayed via loginError
      console.error('Login failed:', error);
    }
  };

  // Demo credentials helper
  const fillDemoCredentials = (role: 'admin' | 'dispatcher' | 'accountant' | 'viewer') => {
    const credentials = {
      admin: { email: 'admin@romanianfreight.com', password: 'admin123' },
      dispatcher: { email: 'dispatcher@romanianfreight.com', password: 'dispatch123' },
      accountant: { email: 'accountant@romanianfreight.com', password: 'account123' },
      viewer: { email: 'viewer@romanianfreight.com', password: 'viewer123' },
    };

    reset(credentials[role]);
  };

  const isFormLoading = isLoading || isSubmitting;

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-100 px-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl font-bold text-slate-900">
            Login to Romanian Freight
          </CardTitle>
          <p className="text-slate-600 mt-2">
            Professional Freight Forwarding Management System
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Error Display */}
          {loginError && (
            <div className="flex items-center gap-2 p-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded-md">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              <span>{loginError}</span>
            </div>
          )}

          {/* Login Form */}
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {/* Email Field */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">
                Email Address
              </label>
              <Input
                type="email"
                placeholder="your@email.com"
                className="w-full"
                disabled={isFormLoading}
                {...register('email')}
              />
              {errors.email && (
                <p className="text-sm text-red-600 mt-1">{errors.email.message}</p>
              )}
            </div>

            {/* Password Field */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">
                Password
              </label>
              <Input
                type="password"
                placeholder="••••••••"
                className="w-full"
                disabled={isFormLoading}
                {...register('password')}
              />
              {errors.password && (
                <p className="text-sm text-red-600 mt-1">{errors.password.message}</p>
              )}
            </div>

            {/* Submit Button */}
            <Button 
              type="submit" 
              className="w-full" 
              disabled={isFormLoading}
            >
              {isFormLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Signing In...
                </>
              ) : (
                'Sign In'
              )}
            </Button>
          </form>

          {/* Demo Credentials Section */}
          <div className="border-t pt-4">
            <p className="text-center text-sm text-slate-600 mb-3">
              Demo Credentials (Romanian Freight Forwarding Roles)
            </p>
            <div className="grid grid-cols-2 gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => fillDemoCredentials('admin')}
                disabled={isFormLoading}
                className="text-xs"
              >
                Admin User
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => fillDemoCredentials('dispatcher')}
                disabled={isFormLoading}
                className="text-xs"
              >
                Dispatcher
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => fillDemoCredentials('accountant')}
                disabled={isFormLoading}
                className="text-xs"
              >
                Accountant
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => fillDemoCredentials('viewer')}
                disabled={isFormLoading}
                className="text-xs"
              >
                Viewer
              </Button>
            </div>
          </div>

          {/* Romanian Context Footer */}
          <div className="text-center text-xs text-slate-500 pt-2">
            <p>Secure authentication for Romanian freight forwarding operations</p>
            <p>Role-based access: Admin • Dispatcher • Accountant • Viewer</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default LoginPage;
