/**
 * Workflow Progress Component
 * Implements workflow-centric design with Romanian freight forwarding stages
 */

import React from 'react';
import { Badge } from '@/shared/components/ui/badge';

export type WorkflowStage = 
  | 'draft'
  | 'document_uploaded'
  | 'ai_processing'
  | 'validation_required'
  | 'validated'
  | 'pricing_calculated'
  | 'confirmed'
  | 'subcontractor_assigned'
  | 'in_transit'
  | 'customs_clearance'
  | 'delivered'
  | 'invoiced'
  | 'paid'
  | 'completed'
  | 'cancelled';

interface WorkflowProgressProps {
  currentStage: WorkflowStage;
  completedStages: WorkflowStage[];
  className?: string;
}

const WORKFLOW_STAGES: Array<{
  key: WorkflowStage;
  label: string;
  description: string;
  group: 'preparation' | 'processing' | 'execution' | 'completion';
}> = [
  {
    key: 'draft',
    label: 'Draft',
    description: 'Order creation started',
    group: 'preparation'
  },
  {
    key: 'document_uploaded',
    label: 'Document Upload',
    description: 'Transport documents uploaded',
    group: 'preparation'
  },
  {
    key: 'ai_processing',
    label: 'AI Processing',
    description: 'Extracting order details',
    group: 'processing'
  },
  {
    key: 'validation_required',
    label: 'Validation',
    description: 'Manual review required',
    group: 'processing'
  },
  {
    key: 'validated',
    label: 'Validated',
    description: 'Order details confirmed',
    group: 'processing'
  },
  {
    key: 'pricing_calculated',
    label: 'Pricing',
    description: 'Romanian VAT calculated',
    group: 'processing'
  },
  {
    key: 'confirmed',
    label: 'Confirmed',
    description: 'Order ready for execution',
    group: 'execution'
  },
  {
    key: 'subcontractor_assigned',
    label: 'Assignment',
    description: 'Subcontractor selected',
    group: 'execution'
  },
  {
    key: 'in_transit',
    label: 'In Transit',
    description: 'Shipment in progress',
    group: 'execution'
  },
  {
    key: 'customs_clearance',
    label: 'Customs',
    description: 'EU border processing',
    group: 'execution'
  },
  {
    key: 'delivered',
    label: 'Delivered',
    description: 'Shipment completed',
    group: 'completion'
  },
  {
    key: 'invoiced',
    label: 'Invoiced',
    description: 'Invoice generated',
    group: 'completion'
  },
  {
    key: 'paid',
    label: 'Paid',
    description: 'Payment received',
    group: 'completion'
  },
  {
    key: 'completed',
    label: 'Completed',
    description: 'Order finalized',
    group: 'completion'
  }
];

const GROUP_COLORS = {
  preparation: 'bg-blue-100 text-blue-800 border-blue-200',
  processing: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  execution: 'bg-orange-100 text-orange-800 border-orange-200',
  completion: 'bg-green-100 text-green-800 border-green-200'
};

export const WorkflowProgress: React.FC<WorkflowProgressProps> = ({
  currentStage,
  completedStages,
  className = ''
}) => {
  const getStageStatus = (stage: WorkflowStage): 'completed' | 'current' | 'pending' => {
    if (completedStages.includes(stage)) return 'completed';
    if (stage === currentStage) return 'current';
    return 'pending';
  };

  const getStageIcon = (status: 'completed' | 'current' | 'pending'): string => {
    switch (status) {
      case 'completed': return '✅';
      case 'current': return '🔄';
      case 'pending': return '⏳';
    }
  };

  const groupStages = (group: string) => 
    WORKFLOW_STAGES.filter(stage => stage.group === group);

  return (
    <div className={`workflow-progress ${className}`}>
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">
          Progress Comandă Transport
        </h3>
        <p className="text-sm text-gray-600">
          Urmăriți stadiile comenzii dvs. de transport marfă
        </p>
      </div>

      <div className="space-y-6">
        {(['preparation', 'processing', 'execution', 'completion'] as const).map(group => (
          <div key={group} className="workflow-group">
            <div className="flex items-center mb-3">
              <Badge 
                variant="outline" 
                className={`${GROUP_COLORS[group]} font-medium`}
              >
                {group === 'preparation' && 'Pregătire'}
                {group === 'processing' && 'Procesare'}
                {group === 'execution' && 'Execuție'}
                {group === 'completion' && 'Finalizare'}
              </Badge>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
              {groupStages(group).map(stage => {
                const status = getStageStatus(stage.key);
                const isActive = status === 'current';
                const isCompleted = status === 'completed';
                
                return (
                  <div
                    key={stage.key}
                    className={`
                      p-3 rounded-lg border-2 transition-all duration-200
                      ${isActive 
                        ? 'border-blue-500 bg-blue-50 shadow-md' 
                        : isCompleted
                        ? 'border-green-500 bg-green-50'
                        : 'border-gray-200 bg-gray-50'
                      }
                    `}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-lg">
                        {getStageIcon(status)}
                      </span>
                      {isActive && (
                        <Badge variant="default" className="text-xs">
                          Curent
                        </Badge>
                      )}
                    </div>
                    
                    <h4 className={`
                      font-semibold text-sm mb-1
                      ${isActive ? 'text-blue-900' : isCompleted ? 'text-green-900' : 'text-gray-700'}
                    `}>
                      {stage.label}
                    </h4>
                    
                    <p className={`
                      text-xs
                      ${isActive ? 'text-blue-700' : isCompleted ? 'text-green-700' : 'text-gray-500'}
                    `}>
                      {stage.description}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Next Actions */}
      <div className="mt-6 p-4 bg-gray-50 rounded-lg">
        <h4 className="font-semibold text-gray-900 mb-2">
          Acțiuni Disponibile
        </h4>
        <div className="flex flex-wrap gap-2">
          {getNextActions(currentStage).map((action, index) => (
            <Badge key={index} variant="secondary" className="cursor-pointer hover:bg-gray-200">
              {action}
            </Badge>
          ))}
        </div>
      </div>
    </div>
  );
};

function getNextActions(stage: WorkflowStage): string[] {
  const actions: Record<WorkflowStage, string[]> = {
    draft: ['Încarcă Document', 'Anulează'],
    document_uploaded: ['Procesează cu AI', 'Introducere Manuală'],
    ai_processing: ['Vezi Progresul'],
    validation_required: ['Validează Date', 'Editează Detalii'],
    validated: ['Calculează Prețul', 'Editează'],
    pricing_calculated: ['Confirmă Comanda', 'Ajustează Prețul'],
    confirmed: ['Asignează Subcontractor', 'Modifică'],
    subcontractor_assigned: ['Începe Transportul', 'Schimbă Asignarea'],
    in_transit: ['Urmărește Expedierea', 'Actualizează Status'],
    customs_clearance: ['Procesează Vama', 'Urmărește'],
    delivered: ['Generează Factură', 'Confirmă Livrarea'],
    invoiced: ['Înregistrează Plata', 'Trimite Memento'],
    paid: ['Finalizează Comanda', 'Generează Raport'],
    completed: ['Vezi Detalii', 'Duplică Comanda'],
    cancelled: ['Vezi Detalii', 'Reactivează']
  };
  
  return actions[stage] || ['Vezi Detalii'];
}

export default WorkflowProgress;
