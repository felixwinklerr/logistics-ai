/**
 * Enhanced Order Form Component
 * Implements workflow-centric design with Romanian business logic integration
 */

import React, { useState, useCallback, useEffect } from 'react';
import { Button } from '@/shared/components/ui/button';
import { Card } from '@/shared/components/ui/card';
import { Input } from '@/shared/components/ui/input';
import { Badge } from '@/shared/components/ui/badge';
import { WorkflowProgress, WorkflowStage } from './workflow/WorkflowProgress';
import { useOrderRealtime } from '../hooks/realtime/useOrderRealtime';
import { 
  romanianLocalization, 
  validateRomanianVAT, 
  validateRomanianPostalCode,
  validateRomanianCounty,
  formatRomanianCurrency,
  getLocalizedText 
} from '../services/romanian/localization';

interface OrderFormData {
  // Company Information
  companyName: string;
  vatNumber: string;
  registrationNumber: string;
  
  // Pickup Address
  pickupStreet: string;
  pickupNumber: string;
  pickupCity: string;
  pickupCounty: string;
  pickupPostalCode: string;
  
  // Delivery Address
  deliveryStreet: string;
  deliveryNumber: string;
  deliveryCity: string;
  deliveryCounty: string;
  deliveryPostalCode: string;
  
  // Cargo Information
  description: string;
  weight: number;
  volume: number;
  length: number;
  width: number;
  height: number;
  
  // Contact Information
  contactPerson: string;
  phone: string;
  email: string;
}

interface OrderFormProps {
  initialData?: Partial<OrderFormData>;
  onSubmit?: (data: OrderFormData) => void;
  onValidationChange?: (isValid: boolean) => void;
  mode?: 'create' | 'edit';
  orderId?: string;
}

interface ValidationErrors {
  [key: string]: string;
}

export const OrderForm: React.FC<OrderFormProps> = ({ 
  initialData = {},
  onSubmit, 
  onValidationChange,
  mode = 'create',
  orderId
}) => {
  const [formData, setFormData] = useState<OrderFormData>({
    companyName: '',
    vatNumber: '',
    registrationNumber: '',
    pickupStreet: '',
    pickupNumber: '',
    pickupCity: '',
    pickupCounty: '',
    pickupPostalCode: '',
    deliveryStreet: '',
    deliveryNumber: '',
    deliveryCity: '',
    deliveryCounty: '',
    deliveryPostalCode: '',
    description: '',
    weight: 0,
    volume: 0,
    length: 0,
    width: 0,
    height: 0,
    contactPerson: '',
    phone: '',
    email: '',
    ...initialData
  });

  const [currentStep, setCurrentStep] = useState<'company' | 'addresses' | 'cargo' | 'contact' | 'review'>('company');
  const [validationErrors, setValidationErrors] = useState<ValidationErrors>({});
  const [isValidating, setIsValidating] = useState(false);
  const [romanianValidation, setRomanianValidation] = useState<any>(null);
  const [currentWorkflowStage] = useState<WorkflowStage>('draft');

  // Real-time integration for collaborative editing
  const {
    isConnected,
    activeUsers,
    broadcastEditing,
    stopEditing
  } = useOrderRealtime({
    orderId,
    enableCollaboration: mode === 'edit'
  });

  // Form validation using Romanian business rules
  const validateForm = useCallback(async () => {
    const errors: ValidationErrors = {};

    // Romanian VAT validation
    if (formData.vatNumber && !validateRomanianVAT(formData.vatNumber)) {
      errors.vatNumber = getLocalizedText('invalidVat', 'forms');
    }

    // Postal code validation
    if (formData.pickupPostalCode && !validateRomanianPostalCode(formData.pickupPostalCode)) {
      errors.pickupPostalCode = getLocalizedText('invalidPostalCode', 'forms');
    }
    if (formData.deliveryPostalCode && !validateRomanianPostalCode(formData.deliveryPostalCode)) {
      errors.deliveryPostalCode = getLocalizedText('invalidPostalCode', 'forms');
    }

    // County validation
    if (formData.pickupCounty && !validateRomanianCounty(formData.pickupCounty)) {
      errors.pickupCounty = getLocalizedText('invalidCounty', 'forms');
    }
    if (formData.deliveryCounty && !validateRomanianCounty(formData.deliveryCounty)) {
      errors.deliveryCounty = getLocalizedText('invalidCounty', 'forms');
    }

    // Required field validation
    if (!formData.companyName) {
      errors.companyName = getLocalizedText('required', 'forms');
    }

    setValidationErrors(errors);
    const isValid = Object.keys(errors).length === 0;
    onValidationChange?.(isValid);
    
    return isValid;
  }, [formData, onValidationChange]);

  // Handle field changes with real-time broadcasting
  const handleFieldChange = useCallback((field: keyof OrderFormData, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    
    // Broadcast editing status for collaboration
    if (mode === 'edit' && isConnected) {
      broadcastEditing(field);
    }
  }, [mode, isConnected, broadcastEditing]);

  // Handle field blur (stop editing broadcast)
  const handleFieldBlur = useCallback(() => {
    if (mode === 'edit' && isConnected) {
      stopEditing();
    }
  }, [mode, isConnected, stopEditing]);
      
  // Validate Romanian business data
  const validateRomanianData = useCallback(async () => {
    if (!formData.vatNumber || Object.keys(validationErrors).length > 0) {
      return;
    }

    setIsValidating(true);
    try {
      // This would call the Romanian validation API endpoint
      const response = await fetch('/api/v1/orders/validate/romanian', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      
      const result = await response.json();
      setRomanianValidation(result);
    } catch (error) {
      console.error('Romanian validation failed:', error);
    } finally {
      setIsValidating(false);
    }
  }, [formData, validationErrors]);

  // Progressive disclosure steps
  const steps = [
    {
      id: 'company',
      label: getLocalizedText('companyName', 'forms'),
      description: 'Informații despre companie și cod TVA',
      isComplete: formData.companyName && formData.vatNumber && !validationErrors.vatNumber
    },
    {
      id: 'addresses',
      label: 'Adrese Transport',
      description: 'Puncte de ridicare și livrare',
      isComplete: formData.pickupCity && formData.deliveryCity
    },
    {
      id: 'cargo',
      label: getLocalizedText('description', 'forms'),
      description: 'Detalii despre marfă și dimensiuni',
      isComplete: formData.description && formData.weight > 0
    },
    {
      id: 'contact',
      label: getLocalizedText('contactPerson', 'forms'),
      description: 'Persoana de contact și comunicare',
      isComplete: formData.contactPerson && formData.email
    },
    {
      id: 'review',
      label: 'Verificare Finală',
      description: 'Validare și confirmare comandă',
      isComplete: false
    }
  ];

  const currentStepIndex = steps.findIndex(step => step.id === currentStep);
  const completedSteps = steps.slice(0, currentStepIndex).filter(step => step.isComplete);

  // Form submission
  const handleSubmit = useCallback(async () => {
    const isValid = await validateForm();
    if (isValid) {
      onSubmit?.(formData);
    }
  }, [formData, validateForm, onSubmit]);

  // Auto-validation on form changes
  useEffect(() => {
    validateForm();
  }, [validateForm]);

  // Romanian validation trigger
  useEffect(() => {
    if (formData.vatNumber && !validationErrors.vatNumber) {
      const timer = setTimeout(validateRomanianData, 1000);
      return () => clearTimeout(timer);
    }
  }, [formData.vatNumber, validationErrors.vatNumber, validateRomanianData]);

  return (
    <div className="order-form-container max-w-4xl mx-auto p-6 space-y-6">
      {/* Workflow Progress */}
      <WorkflowProgress
        currentStage={currentWorkflowStage}
        completedStages={[]}
        className="mb-8"
      />

      {/* Collaboration Indicator */}
      {mode === 'edit' && activeUsers.length > 0 && (
        <Card className="p-4 bg-blue-50 border-blue-200">
          <div className="flex items-center gap-2">
            <Badge variant="secondary">👥 Colaborare Activă</Badge>
            <span className="text-sm text-blue-700">
              {activeUsers.length} utilizator{activeUsers.length > 1 ? 'i' : ''} 
              {activeUsers.length > 1 ? ' lucrează' : ' lucrează'} la această comandă
            </span>
          </div>
          {activeUsers.map(user => (
            <div key={user.userId} className="text-xs text-blue-600 mt-1">
              {user.username} {user.editingField && `editează ${user.editingField}`}
            </div>
          ))}
        </Card>
      )}

      {/* Step Progress */}
      <Card className="p-6">
        <div className="mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            {steps[currentStepIndex]?.label}
          </h2>
          <p className="text-gray-600">
            {steps[currentStepIndex]?.description}
          </p>
        </div>

        <div className="flex items-center space-x-4 mb-6">
          {steps.map((step, index) => (
            <div key={step.id} className="flex items-center">
              <div className={`
                w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium
                ${index < currentStepIndex 
                  ? 'bg-green-500 text-white' 
                  : index === currentStepIndex 
                  ? 'bg-blue-500 text-white' 
                  : 'bg-gray-200 text-gray-600'
                }
              `}>
                {index < currentStepIndex ? '✓' : index + 1}
              </div>
              {index < steps.length - 1 && (
                <div className={`
                  w-12 h-1 mx-2
                  ${index < currentStepIndex ? 'bg-green-500' : 'bg-gray-200'}
                `} />
              )}
            </div>
          ))}
          </div>

        {/* Progressive Form Content */}
        <div className="space-y-4">
          {renderFormStep(currentStep, formData, validationErrors, handleFieldChange, handleFieldBlur, romanianValidation)}
            </div>

        {/* Romanian Validation Status */}
        {romanianValidation && (
          <Card className="mt-6 p-4 bg-green-50 border-green-200">
            <h4 className="font-semibold text-green-900 mb-2">
              ✅ Validare Română Completă
            </h4>
            {romanianValidation.pricing && (
              <div className="text-sm text-green-700">
                <p>Preț calculat: {formatRomanianCurrency(romanianValidation.pricing.total_cost, 'RON')}</p>
                <p>TVA inclus: {formatRomanianCurrency(romanianValidation.pricing.vat_calculation.vat_amount, 'RON')}</p>
              </div>
            )}
          </Card>
        )}

        {/* Navigation */}
        <div className="flex justify-between mt-8">
                  <Button 
                    variant="outline" 
            onClick={() => {
              const prevStepIndex = Math.max(0, currentStepIndex - 1);
              setCurrentStep(steps[prevStepIndex].id as any);
            }}
            disabled={currentStepIndex === 0}
                  >
            ← Anterior
                  </Button>

          {currentStepIndex < steps.length - 1 ? (
                  <Button 
              onClick={() => {
                const nextStepIndex = Math.min(steps.length - 1, currentStepIndex + 1);
                setCurrentStep(steps[nextStepIndex].id as any);
              }}
              disabled={!steps[currentStepIndex].isComplete}
                  >
              Următorul →
                  </Button>
                ) : (
                  <Button 
              onClick={handleSubmit}
              disabled={Object.keys(validationErrors).length > 0 || isValidating}
                  >
              {isValidating ? 'Se validează...' : getLocalizedText('submit', 'forms')}
                  </Button>
                )}
              </div>
      </Card>
    </div>
  );
};

// Helper render functions
const renderFormStep = (
  currentStep: string,
  formData: OrderFormData,
  validationErrors: ValidationErrors,
  handleFieldChange: (field: keyof OrderFormData, value: any) => void,
  handleFieldBlur: () => void,
  romanianValidation: any
) => {
  switch (currentStep) {
    case 'company':
      return renderCompanyStep(formData, validationErrors, handleFieldChange, handleFieldBlur);
    case 'addresses':
      return renderAddressesStep(formData, validationErrors, handleFieldChange, handleFieldBlur);
    case 'cargo':
      return renderCargoStep(formData, handleFieldChange, handleFieldBlur);
    case 'contact':
      return renderContactStep(formData, handleFieldChange, handleFieldBlur);
    case 'review':
      return renderReviewStep(formData, romanianValidation);
    default:
      return null;
  }
};

const renderCompanyStep = (
  formData: OrderFormData,
  validationErrors: ValidationErrors,
  handleFieldChange: (field: keyof OrderFormData, value: any) => void,
  handleFieldBlur: () => void
) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          {getLocalizedText('companyName', 'forms')} *
        </label>
        <Input
          value={formData.companyName}
          onChange={(e) => handleFieldChange('companyName', e.target.value)}
          onBlur={handleFieldBlur}
          className={validationErrors.companyName ? 'border-red-500' : ''}
          placeholder="S.C. Exemplu Transport S.R.L."
        />
        {validationErrors.companyName && (
          <p className="text-red-500 text-sm mt-1">{validationErrors.companyName}</p>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          {getLocalizedText('vatNumber', 'forms')} *
        </label>
        <Input
          value={formData.vatNumber}
          onChange={(e) => handleFieldChange('vatNumber', e.target.value.toUpperCase())}
          onBlur={handleFieldBlur}
          className={validationErrors.vatNumber ? 'border-red-500' : ''}
          placeholder="RO12345678"
          maxLength={12}
        />
        {validationErrors.vatNumber && (
          <p className="text-red-500 text-sm mt-1">{validationErrors.vatNumber}</p>
        )}
        <p className="text-xs text-gray-500 mt-1">Format: RO + 2-10 cifre</p>
      </div>

      <div className="md:col-span-2">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          {getLocalizedText('registrationNumber', 'forms')}
        </label>
        <Input
          value={formData.registrationNumber}
          onChange={(e) => handleFieldChange('registrationNumber', e.target.value)}
          onBlur={handleFieldBlur}
          placeholder="J40/1234/2023"
        />
      </div>
    </div>
  );
};

const renderAddressesStep = (
  formData: OrderFormData,
  validationErrors: ValidationErrors,
  handleFieldChange: (field: keyof OrderFormData, value: any) => void,
  handleFieldBlur: () => void
) => {
  return (
    <div className="space-y-6">
      {/* Pickup Address */}
      <div>
        <h4 className="font-semibold text-gray-900 mb-4">📍 Adresa de Ridicare</h4>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {getLocalizedText('street', 'forms')} *
            </label>
            <Input
              value={formData.pickupStreet}
              onChange={(e) => handleFieldChange('pickupStreet', e.target.value)}
              onBlur={handleFieldBlur}
              placeholder="Strada Exemplu"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {getLocalizedText('number', 'forms')}
            </label>
            <Input
              value={formData.pickupNumber}
              onChange={(e) => handleFieldChange('pickupNumber', e.target.value)}
              onBlur={handleFieldBlur}
              placeholder="123A"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {getLocalizedText('city', 'forms')} *
            </label>
            <Input
              value={formData.pickupCity}
              onChange={(e) => handleFieldChange('pickupCity', e.target.value)}
              onBlur={handleFieldBlur}
              placeholder="București"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {getLocalizedText('county', 'forms')} *
        </label>
        <Input
              value={formData.pickupCounty}
              onChange={(e) => handleFieldChange('pickupCounty', e.target.value.toUpperCase())}
              onBlur={handleFieldBlur}
              className={validationErrors.pickupCounty ? 'border-red-500' : ''}
              placeholder="B"
              maxLength={2}
        />
            {validationErrors.pickupCounty && (
              <p className="text-red-500 text-sm mt-1">{validationErrors.pickupCounty}</p>
        )}
      </div>
      <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {getLocalizedText('postalCode', 'forms')} *
        </label>
        <Input
              value={formData.pickupPostalCode}
              onChange={(e) => handleFieldChange('pickupPostalCode', e.target.value)}
              onBlur={handleFieldBlur}
              className={validationErrors.pickupPostalCode ? 'border-red-500' : ''}
              placeholder="012345"
              maxLength={6}
        />
            {validationErrors.pickupPostalCode && (
              <p className="text-red-500 text-sm mt-1">{validationErrors.pickupPostalCode}</p>
        )}
      </div>
    </div>
  </div>

      {/* Delivery Address */}
      <div>
        <h4 className="font-semibold text-gray-900 mb-4">🎯 Adresa de Livrare</h4>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {getLocalizedText('street', 'forms')} *
          </label>
          <Input
              value={formData.deliveryStreet}
              onChange={(e) => handleFieldChange('deliveryStreet', e.target.value)}
              onBlur={handleFieldBlur}
              placeholder="Strada Destinație"
            />
        </div>
        <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {getLocalizedText('number', 'forms')}
          </label>
          <Input
              value={formData.deliveryNumber}
              onChange={(e) => handleFieldChange('deliveryNumber', e.target.value)}
              onBlur={handleFieldBlur}
              placeholder="456B"
            />
        </div>
        <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {getLocalizedText('city', 'forms')} *
          </label>
          <Input
              value={formData.deliveryCity}
              onChange={(e) => handleFieldChange('deliveryCity', e.target.value)}
              onBlur={handleFieldBlur}
              placeholder="Cluj-Napoca"
            />
      </div>
        <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {getLocalizedText('county', 'forms')} *
          </label>
          <Input
              value={formData.deliveryCounty}
              onChange={(e) => handleFieldChange('deliveryCounty', e.target.value.toUpperCase())}
              onBlur={handleFieldBlur}
              className={validationErrors.deliveryCounty ? 'border-red-500' : ''}
              placeholder="CJ"
              maxLength={2}
          />
            {validationErrors.deliveryCounty && (
              <p className="text-red-500 text-sm mt-1">{validationErrors.deliveryCounty}</p>
          )}
        </div>
        <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {getLocalizedText('postalCode', 'forms')} *
          </label>
          <Input
              value={formData.deliveryPostalCode}
              onChange={(e) => handleFieldChange('deliveryPostalCode', e.target.value)}
              onBlur={handleFieldBlur}
              className={validationErrors.deliveryPostalCode ? 'border-red-500' : ''}
              placeholder="400001"
              maxLength={6}
          />
            {validationErrors.deliveryPostalCode && (
              <p className="text-red-500 text-sm mt-1">{validationErrors.deliveryPostalCode}</p>
          )}
        </div>
      </div>
    </div>
  </div>
);
};

const renderCargoStep = (
  formData: OrderFormData,
  handleFieldChange: (field: keyof OrderFormData, value: any) => void,
  handleFieldBlur: () => void
) => {
  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          {getLocalizedText('description', 'forms')} *
        </label>
        <textarea
          className="w-full p-3 border border-gray-300 rounded-md"
          rows={3}
          value={formData.description}
          onChange={(e) => handleFieldChange('description', e.target.value)}
          onBlur={handleFieldBlur}
          placeholder="Descrierea mărfii transportate..."
        />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            {getLocalizedText('weight', 'forms')} *
          </label>
          <Input
            type="number"
            value={formData.weight}
            onChange={(e) => handleFieldChange('weight', parseFloat(e.target.value) || 0)}
            onBlur={handleFieldBlur}
            placeholder="1000"
            min="0"
            step="0.1"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            {getLocalizedText('volume', 'forms')}
          </label>
          <Input
            type="number"
            value={formData.volume}
            onChange={(e) => handleFieldChange('volume', parseFloat(e.target.value) || 0)}
            onBlur={handleFieldBlur}
            placeholder="10.5"
            min="0"
            step="0.1"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            {getLocalizedText('length', 'forms')}
          </label>
          <Input
            type="number"
            value={formData.length}
            onChange={(e) => handleFieldChange('length', parseFloat(e.target.value) || 0)}
            onBlur={handleFieldBlur}
            placeholder="240"
            min="0"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            {getLocalizedText('width', 'forms')}
          </label>
          <Input
            type="number"
            value={formData.width}
            onChange={(e) => handleFieldChange('width', parseFloat(e.target.value) || 0)}
            onBlur={handleFieldBlur}
            placeholder="240"
            min="0"
          />
      </div>
    </div>
  </div>
);
};

const renderContactStep = (
  formData: OrderFormData,
  handleFieldChange: (field: keyof OrderFormData, value: any) => void,
  handleFieldBlur: () => void
) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          {getLocalizedText('contactPerson', 'forms')} *
        </label>
        <Input
          value={formData.contactPerson}
          onChange={(e) => handleFieldChange('contactPerson', e.target.value)}
          onBlur={handleFieldBlur}
          placeholder="Ion Popescu"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          {getLocalizedText('phone', 'forms')} *
        </label>
        <Input
          value={formData.phone}
          onChange={(e) => handleFieldChange('phone', e.target.value)}
          onBlur={handleFieldBlur}
          placeholder="+40 7XX XXX XXX"
        />
      </div>
      <div className="md:col-span-2">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          {getLocalizedText('email', 'forms')} *
        </label>
        <Input
          type="email"
          value={formData.email}
          onChange={(e) => handleFieldChange('email', e.target.value)}
          onBlur={handleFieldBlur}
          placeholder="contact@exemplu.ro"
        />
      </div>
    </div>
  );
};

const renderReviewStep = (formData: OrderFormData, romanianValidation: any) => {
  return (
    <div className="space-y-6">
      <h4 className="font-semibold text-gray-900">📋 Verificare Finală</h4>
      
      <div className="bg-gray-50 rounded-lg p-4 space-y-2">
        <div><strong>Companie:</strong> {formData.companyName}</div>
        <div><strong>TVA:</strong> {formData.vatNumber}</div>
        <div><strong>Transport:</strong> {formData.pickupCity} → {formData.deliveryCity}</div>
        <div><strong>Marfă:</strong> {formData.description}</div>
        <div><strong>Greutate:</strong> {formData.weight} kg</div>
        <div><strong>Contact:</strong> {formData.contactPerson} ({formData.email})</div>
    </div>

      {romanianValidation?.pricing && (
        <Card className="p-4 bg-blue-50">
          <h5 className="font-semibold mb-2">💰 Estimare Preț</h5>
          <div className="space-y-1 text-sm">
            <div>Cost de bază: {formatRomanianCurrency(romanianValidation.pricing.base_cost, 'RON')}</div>
            <div>TVA (19%): {formatRomanianCurrency(romanianValidation.pricing.vat_calculation.vat_amount, 'RON')}</div>
            <div className="font-semibold">
              Total: {formatRomanianCurrency(romanianValidation.pricing.total_cost, 'RON')}
        </div>
      </div>
        </Card>
      )}
  </div>
);
};

export default OrderForm;
