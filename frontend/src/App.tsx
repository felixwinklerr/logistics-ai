import React from 'react'
import { RouterProvider } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'sonner'
import { router } from './app/router'
import { AuthProvider } from './shared/hooks/useAuth'

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30000, // 30 seconds
      retry: 1,
    },
  },
})

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <div className="min-h-screen bg-slate-50">
          <RouterProvider router={router} />
          <Toaster 
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: 'white',
                color: 'rgb(51, 65, 85)',
                border: '1px solid rgb(226, 232, 240)',
              },
            }}
          />
        </div>
      </AuthProvider>
    </QueryClientProvider>
  )
}
