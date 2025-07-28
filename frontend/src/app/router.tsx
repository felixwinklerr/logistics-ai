import { createBrowserRouter, Navigate } from 'react-router-dom';
import { Layout } from '@/shared/components/layout/Layout';
import { LoginPage } from '@/features/auth/pages/LoginPage';
import { DashboardPage } from '@/features/dashboard/pages/DashboardPage';
import { OrdersPage, OrderDetailsPage, OrderFormPage } from '@/features/orders/pages';
import { SubcontractorsPage } from '@/features/subcontractors/pages';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      {
        index: true,
        element: <Navigate to="/dashboard" replace />,
      },
      {
        path: 'dashboard',
        element: <DashboardPage />,
      },
      {
        path: 'orders',
        element: <OrdersPage />,
      },
      {
        path: 'orders/new',
        element: <OrderFormPage />,
      },
      {
        path: 'orders/:id',
        element: <OrderDetailsPage />,
      },
      {
        path: 'orders/:id/edit',
        element: <OrderFormPage />,
      },
      {
        path: 'subcontractors',
        element: <SubcontractorsPage />,
      },
    ],
  },
  {
    path: '/login',
    element: <LoginPage />,
  },
]);
