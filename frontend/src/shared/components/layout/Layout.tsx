import React from 'react';
import { Outlet } from 'react-router-dom';
import { Header } from './Header';

export const Layout: React.FC = () => {
  return (
    <div className="min-h-screen bg-slate-50">
      <Header />
      <main className="flex-1">
        <Outlet />
      </main>
    </div>
  );
}; 