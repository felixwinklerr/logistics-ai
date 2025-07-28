import React, { useState } from 'react'
import { Header } from './Header'
import { Sidebar } from './Sidebar'

interface PageLayoutProps {
  children: React.ReactNode
  showSidebar?: boolean
}

export const PageLayout: React.FC<PageLayoutProps> = ({ 
  children, 
  showSidebar = false 
}) => {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const handleMenuToggle = () => {
    setSidebarOpen(!sidebarOpen)
  }

  const handleSidebarClose = () => {
    setSidebarOpen(false)
  }

  if (showSidebar) {
    return (
      <div className="min-h-screen bg-slate-50">
        {/* Sidebar */}
        <Sidebar isOpen={sidebarOpen} onClose={handleSidebarClose} />
        
        {/* Main content area */}
        <div className="md:pl-72">
          <Header onMenuToggle={handleMenuToggle} />
          
          <main className="px-4 sm:px-6 lg:px-8 py-8">
            {children}
          </main>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <Header onMenuToggle={handleMenuToggle} />
      
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
    </div>
  )
}
