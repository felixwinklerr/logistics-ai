import React from 'react';
import { SubcontractorList } from '../components/SubcontractorList';

export const SubcontractorsPage: React.FC = () => {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">Subcontractors</h1>
        <p className="text-slate-600 mt-2">Manage your freight forwarding partners</p>
      </div>
      <SubcontractorList />
    </div>
  );
}; 