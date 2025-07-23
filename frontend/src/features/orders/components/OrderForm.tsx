import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Building,
  MapPin,
  Package,
  ChevronLeft,
  ChevronRight,
  Save,
  X,
  AlertCircle,
  CheckCircle
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card';
import { Button } from '@/shared/components/ui/button';
import { Input } from '@/shared/components/ui/input';
import { 
  OrderCreateRequest, 
  OrderUpdateRequest,
  Order 
} from '@/features/orders/types';

// Romanian business validation patterns
export const VAT_REGEX = /^RO\d{2,10}$/;
export const POSTCODE_REGEX = /^\d{6}$/;

// Order form validation schema
const orderSchema = z.object({
  // Client Information - Step 1
  client_company_name: z.string()
    .min(2, 'Company name must be at least 2 characters')
    .max(100, 'Company name must be less than 100 characters'),
  client_vat_number: z.string()
    .regex(VAT_REGEX, 'VAT number must be in format: RO followed by 2-10 digits'),
  client_contact_email: z.string()
    .email('Please enter a valid email address'),
  client_offered_price: z.number()
    .min(1, 'Price must be greater than 0')
    .max(100000, 'Price cannot exceed €100,000'),
  client_payment_terms: z.string()
    .max(100, 'Payment terms must be less than 100 characters')
    .optional(),

  // Pickup Information - Step 2
  pickup_address: z.string()
    .min(5, 'Pickup address must be at least 5 characters')
    .max(200, 'Address must be less than 200 characters'),
  pickup_postcode: z.string()
    .regex(POSTCODE_REGEX, 'Romanian postcode must be exactly 6 digits'),
  pickup_city: z.string()
    .min(2, 'City name must be at least 2 characters')
    .max(50, 'City name must be less than 50 characters'),
  pickup_country: z.string()
    .length(2, 'Country code must be exactly 2 characters')
    .default('RO'),
  pickup_date_start: z.string()
    .optional(),
  pickup_date_end: z.string()
    .optional(),

  // Delivery Information - Step 3
  delivery_address: z.string()
    .min(5, 'Delivery address must be at least 5 characters')
    .max(200, 'Address must be less than 200 characters'),
  delivery_postcode: z.string()
    .regex(POSTCODE_REGEX, 'Romanian postcode must be exactly 6 digits'),
  delivery_city: z.string()
    .min(2, 'City name must be at least 2 characters')
    .max(50, 'City name must be less than 50 characters'),
  delivery_country: z.string()
    .length(2, 'Country code must be exactly 2 characters')
    .default('RO'),
  delivery_date_start: z.string()
    .optional(),
  delivery_date_end: z.string()
    .optional(),

  // Cargo Information - Step 4
  cargo_ldm: z.number()
    .min(0.1, 'LDM must be at least 0.1')
    .max(33, 'LDM cannot exceed 33 meters')
    .optional(),
  cargo_weight_kg: z.number()
    .min(1, 'Weight must be at least 1 kg')
    .max(40000, 'Weight cannot exceed 40,000 kg')
    .optional(),
  cargo_pallets: z.number()
    .min(1, 'Pallets must be at least 1')
    .max(33, 'Pallets cannot exceed 33')
    .optional(),
  cargo_description: z.string()
    .max(500, 'Description must be less than 500 characters')
    .optional(),
  special_requirements: z.string()
    .max(500, 'Special requirements must be less than 500 characters')
    .optional(),
});

type OrderFormData = z.infer<typeof orderSchema>;

interface OrderFormProps {
  order?: Order;
  onSubmit: (data: OrderCreateRequest | OrderUpdateRequest) => Promise<void>;
  onCancel: () => void;
  isLoading?: boolean;
}

export const OrderForm: React.FC<OrderFormProps> = ({ 
  order, 
  onSubmit, 
  onCancel, 
  isLoading = false 
}) => {
  const [currentStep, setCurrentStep] = useState(1);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isValid },
    reset,
  } = useForm<OrderFormData>({
    resolver: zodResolver(orderSchema),
    defaultValues: {
      client_company_name: order?.client_company_name || '',
      client_vat_number: order?.client_vat_number || '',
      client_contact_email: order?.client_contact_email || '',
      client_offered_price: order?.client_offered_price || 0,
      client_payment_terms: order?.client_payment_terms || '',
      pickup_address: order?.pickup_address || '',
      pickup_postcode: order?.pickup_postcode || '',
      pickup_city: order?.pickup_city || '',
      pickup_country: order?.pickup_country || 'RO',
      pickup_date_start: order?.pickup_date_start || '',
      pickup_date_end: order?.pickup_date_end || '',
      delivery_address: order?.delivery_address || '',
      delivery_postcode: order?.delivery_postcode || '',
      delivery_city: order?.delivery_city || '',
      delivery_country: order?.delivery_country || 'RO',
      delivery_date_start: order?.delivery_date_start || '',
      delivery_date_end: order?.delivery_date_end || '',
      cargo_ldm: order?.cargo_ldm || undefined,
      cargo_weight_kg: order?.cargo_weight_kg || undefined,
      cargo_pallets: order?.cargo_pallets || undefined,
      cargo_description: order?.cargo_description || '',
      special_requirements: order?.special_requirements || '',
    },
    mode: 'onChange'
  });

  const totalSteps = 4;
  const isLastStep = currentStep === totalSteps;
  const isFirstStep = currentStep === 1;

  const handleNext = () => {
    if (currentStep < totalSteps) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handlePrevious = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const onFormSubmit = async (data: OrderFormData) => {
    try {
      setSubmitError(null);
      
      // Convert form data to API format
      const submitData: OrderCreateRequest | OrderUpdateRequest = {
        ...data,
        // Ensure numeric fields are properly typed
        client_offered_price: Number(data.client_offered_price),
        cargo_ldm: data.cargo_ldm ? Number(data.cargo_ldm) : undefined,
        cargo_weight_kg: data.cargo_weight_kg ? Number(data.cargo_weight_kg) : undefined,
        cargo_pallets: data.cargo_pallets ? Number(data.cargo_pallets) : undefined,
      };

      await onSubmit(submitData);
      reset(); // Reset form after successful submission
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : 'An error occurred while saving the order');
    }
  };

  const handleCancel = () => {
    reset();
    setCurrentStep(1);
    setSubmitError(null);
    onCancel();
  };

  const renderStepContent = () => {
    switch (currentStep) {
      case 1:
        return <ClientInfoStep register={register} errors={errors} />;
      case 2:
        return <PickupInfoStep register={register} errors={errors} />;
      case 3:
        return <DeliveryInfoStep register={register} errors={errors} />;
      case 4:
        return <CargoInfoStep register={register} errors={errors} />;
      default:
        return null;
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-2xl">
              {order ? 'Edit Order' : 'Create New Order'}
            </CardTitle>
            <Button variant="outline" onClick={handleCancel} disabled={isLoading}>
              <X className="w-4 h-4 mr-2" />
              Cancel
            </Button>
          </div>
          
          {/* Progress Indicator */}
          <div className="mt-4">
            <div className="flex items-center justify-between text-sm text-slate-600 mb-2">
              <span>Step {currentStep} of {totalSteps}</span>
              <span>{Math.round((currentStep / totalSteps) * 100)}% Complete</span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-2">
              <div 
                className="bg-blue-600 h-2 rounded-full transition-all duration-300 ease-in-out"
                style={{ width: `${(currentStep / totalSteps) * 100}%` }}
              />
            </div>
          </div>

          {/* Step Labels */}
          <div className="flex justify-between mt-4 text-xs">
            <span className={currentStep >= 1 ? 'text-blue-600 font-medium' : 'text-slate-400'}>
              Client Info
            </span>
            <span className={currentStep >= 2 ? 'text-blue-600 font-medium' : 'text-slate-400'}>
              Pickup Details
            </span>
            <span className={currentStep >= 3 ? 'text-blue-600 font-medium' : 'text-slate-400'}>
              Delivery Details
            </span>
            <span className={currentStep >= 4 ? 'text-blue-600 font-medium' : 'text-slate-400'}>
              Cargo Info
            </span>
          </div>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit(onFormSubmit)} className="space-y-6">
            {/* Step Content */}
            <div className="min-h-[400px]">
              {renderStepContent()}
            </div>

            {/* Error Display */}
            {submitError && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-md">
                <div className="flex items-center">
                  <AlertCircle className="w-5 h-5 text-red-500 mr-2" />
                  <span className="text-red-700">{submitError}</span>
                </div>
              </div>
            )}

            {/* Navigation Buttons */}
            <div className="flex items-center justify-between pt-6 border-t border-slate-200">
              <div>
                {!isFirstStep && (
                  <Button 
                    type="button" 
                    variant="outline" 
                    onClick={handlePrevious}
                    disabled={isLoading}
                  >
                    <ChevronLeft className="w-4 h-4 mr-2" />
                    Previous
                  </Button>
                )}
              </div>

              <div className="flex space-x-3">
                {!isLastStep ? (
                  <Button 
                    type="button" 
                    onClick={handleNext}
                    disabled={isLoading}
                  >
                    Next
                    <ChevronRight className="w-4 h-4 ml-2" />
                  </Button>
                ) : (
                  <Button 
                    type="submit" 
                    disabled={!isValid || isLoading}
                    className="bg-blue-600 hover:bg-blue-700"
                  >
                    {isLoading ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                        {order ? 'Updating...' : 'Creating...'}
                      </>
                    ) : (
                      <>
                        <Save className="w-4 h-4 mr-2" />
                        {order ? 'Update Order' : 'Create Order'}
                      </>
                    )}
                  </Button>
                )}
              </div>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};

// Step Components
const ClientInfoStep: React.FC<{
  register: any;
  errors: any;
}> = ({ register, errors }) => (
  <div className="space-y-6">
    <div className="flex items-center mb-4">
      <Building className="w-5 h-5 text-blue-600 mr-2" />
      <h3 className="text-lg font-semibold">Client Information</h3>
    </div>

    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          Company Name *
        </label>
        <Input
          {...register('client_company_name')}
          placeholder="Transport Company SRL"
          className={errors.client_company_name ? 'border-red-500' : ''}
        />
        {errors.client_company_name && (
          <p className="text-red-500 text-sm mt-1">{errors.client_company_name.message}</p>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          VAT Number *
        </label>
        <Input
          {...register('client_vat_number')}
          placeholder="RO12345678"
          className={errors.client_vat_number ? 'border-red-500' : ''}
        />
        {errors.client_vat_number && (
          <p className="text-red-500 text-sm mt-1">{errors.client_vat_number.message}</p>
        )}
        <p className="text-slate-500 text-xs mt-1">Format: RO followed by 2-10 digits</p>
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          Contact Email *
        </label>
        <Input
          {...register('client_contact_email')}
          type="email"
          placeholder="contact@company.ro"
          className={errors.client_contact_email ? 'border-red-500' : ''}
        />
        {errors.client_contact_email && (
          <p className="text-red-500 text-sm mt-1">{errors.client_contact_email.message}</p>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          Offered Price (EUR) *
        </label>
        <Input
          {...register('client_offered_price', { valueAsNumber: true })}
          type="number"
          step="0.01"
          min="1"
          max="100000"
          placeholder="1500.00"
          className={errors.client_offered_price ? 'border-red-500' : ''}
        />
        {errors.client_offered_price && (
          <p className="text-red-500 text-sm mt-1">{errors.client_offered_price.message}</p>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          Payment Terms
        </label>
        <Input
          {...register('client_payment_terms')}
          placeholder="30 days after delivery"
          className={errors.client_payment_terms ? 'border-red-500' : ''}
        />
        {errors.client_payment_terms && (
          <p className="text-red-500 text-sm mt-1">{errors.client_payment_terms.message}</p>
        )}
      </div>
    </div>
  </div>
);

const PickupInfoStep: React.FC<{
  register: any;
  errors: any;
}> = ({ register, errors }) => (
  <div className="space-y-6">
    <div className="flex items-center mb-4">
      <MapPin className="w-5 h-5 text-green-600 mr-2" />
      <h3 className="text-lg font-semibold">Pickup Information</h3>
    </div>

    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          Pickup Address *
        </label>
        <textarea
          {...register('pickup_address')}
          rows={3}
          placeholder="Strada Industriei 123, Sector 4"
          className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
            errors.pickup_address ? 'border-red-500' : 'border-slate-300'
          }`}
        />
        {errors.pickup_address && (
          <p className="text-red-500 text-sm mt-1">{errors.pickup_address.message}</p>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Postcode *
          </label>
          <Input
            {...register('pickup_postcode')}
            placeholder="123456"
            maxLength={6}
            className={errors.pickup_postcode ? 'border-red-500' : ''}
          />
          {errors.pickup_postcode && (
            <p className="text-red-500 text-sm mt-1">{errors.pickup_postcode.message}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            City *
          </label>
          <Input
            {...register('pickup_city')}
            placeholder="Bucuresti"
            className={errors.pickup_city ? 'border-red-500' : ''}
          />
          {errors.pickup_city && (
            <p className="text-red-500 text-sm mt-1">{errors.pickup_city.message}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Country
          </label>
          <Input
            {...register('pickup_country')}
            placeholder="RO"
            maxLength={2}
            className={errors.pickup_country ? 'border-red-500' : ''}
          />
          {errors.pickup_country && (
            <p className="text-red-500 text-sm mt-1">{errors.pickup_country.message}</p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Pickup Date From
          </label>
          <Input
            {...register('pickup_date_start')}
            type="date"
            className={errors.pickup_date_start ? 'border-red-500' : ''}
          />
          {errors.pickup_date_start && (
            <p className="text-red-500 text-sm mt-1">{errors.pickup_date_start.message}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Pickup Date To
          </label>
          <Input
            {...register('pickup_date_end')}
            type="date"
            className={errors.pickup_date_end ? 'border-red-500' : ''}
          />
          {errors.pickup_date_end && (
            <p className="text-red-500 text-sm mt-1">{errors.pickup_date_end.message}</p>
          )}
        </div>
      </div>
    </div>
  </div>
);

const DeliveryInfoStep: React.FC<{
  register: any;
  errors: any;
}> = ({ register, errors }) => (
  <div className="space-y-6">
    <div className="flex items-center mb-4">
      <MapPin className="w-5 h-5 text-orange-600 mr-2" />
      <h3 className="text-lg font-semibold">Delivery Information</h3>
    </div>

    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          Delivery Address *
        </label>
        <textarea
          {...register('delivery_address')}
          rows={3}
          placeholder="Bulevardul Magheru 456, Sector 1"
          className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
            errors.delivery_address ? 'border-red-500' : 'border-slate-300'
          }`}
        />
        {errors.delivery_address && (
          <p className="text-red-500 text-sm mt-1">{errors.delivery_address.message}</p>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Postcode *
          </label>
          <Input
            {...register('delivery_postcode')}
            placeholder="789012"
            maxLength={6}
            className={errors.delivery_postcode ? 'border-red-500' : ''}
          />
          {errors.delivery_postcode && (
            <p className="text-red-500 text-sm mt-1">{errors.delivery_postcode.message}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            City *
          </label>
          <Input
            {...register('delivery_city')}
            placeholder="Cluj-Napoca"
            className={errors.delivery_city ? 'border-red-500' : ''}
          />
          {errors.delivery_city && (
            <p className="text-red-500 text-sm mt-1">{errors.delivery_city.message}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Country
          </label>
          <Input
            {...register('delivery_country')}
            placeholder="RO"
            maxLength={2}
            className={errors.delivery_country ? 'border-red-500' : ''}
          />
          {errors.delivery_country && (
            <p className="text-red-500 text-sm mt-1">{errors.delivery_country.message}</p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Delivery Date From
          </label>
          <Input
            {...register('delivery_date_start')}
            type="date"
            className={errors.delivery_date_start ? 'border-red-500' : ''}
          />
          {errors.delivery_date_start && (
            <p className="text-red-500 text-sm mt-1">{errors.delivery_date_start.message}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Delivery Date To
          </label>
          <Input
            {...register('delivery_date_end')}
            type="date"
            className={errors.delivery_date_end ? 'border-red-500' : ''}
          />
          {errors.delivery_date_end && (
            <p className="text-red-500 text-sm mt-1">{errors.delivery_date_end.message}</p>
          )}
        </div>
      </div>
    </div>
  </div>
);

const CargoInfoStep: React.FC<{
  register: any;
  errors: any;
}> = ({ register, errors }) => (
  <div className="space-y-6">
    <div className="flex items-center mb-4">
      <Package className="w-5 h-5 text-purple-600 mr-2" />
      <h3 className="text-lg font-semibold">Cargo Information</h3>
    </div>

    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          LDM (Loading Meters)
        </label>
        <Input
          {...register('cargo_ldm', { valueAsNumber: true })}
          type="number"
          step="0.1"
          min="0.1"
          max="33"
          placeholder="2.4"
          className={errors.cargo_ldm ? 'border-red-500' : ''}
        />
        {errors.cargo_ldm && (
          <p className="text-red-500 text-sm mt-1">{errors.cargo_ldm.message}</p>
        )}
        <p className="text-slate-500 text-xs mt-1">Maximum: 33 meters</p>
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          Weight (kg)
        </label>
        <Input
          {...register('cargo_weight_kg', { valueAsNumber: true })}
          type="number"
          min="1"
          max="40000"
          placeholder="1000"
          className={errors.cargo_weight_kg ? 'border-red-500' : ''}
        />
        {errors.cargo_weight_kg && (
          <p className="text-red-500 text-sm mt-1">{errors.cargo_weight_kg.message}</p>
        )}
        <p className="text-slate-500 text-xs mt-1">Maximum: 40,000 kg</p>
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          Number of Pallets
        </label>
        <Input
          {...register('cargo_pallets', { valueAsNumber: true })}
          type="number"
          min="1"
          max="33"
          placeholder="4"
          className={errors.cargo_pallets ? 'border-red-500' : ''}
        />
        {errors.cargo_pallets && (
          <p className="text-red-500 text-sm mt-1">{errors.cargo_pallets.message}</p>
        )}
        <p className="text-slate-500 text-xs mt-1">Maximum: 33 pallets</p>
      </div>
    </div>

    <div>
      <label className="block text-sm font-medium text-slate-700 mb-1">
        Cargo Description
      </label>
      <textarea
        {...register('cargo_description')}
        rows={3}
        placeholder="Electronics, furniture, machinery..."
        className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
          errors.cargo_description ? 'border-red-500' : 'border-slate-300'
        }`}
      />
      {errors.cargo_description && (
        <p className="text-red-500 text-sm mt-1">{errors.cargo_description.message}</p>
      )}
    </div>

    <div>
      <label className="block text-sm font-medium text-slate-700 mb-1">
        Special Requirements
      </label>
      <textarea
        {...register('special_requirements')}
        rows={3}
        placeholder="Temperature controlled, fragile handling, security requirements..."
        className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
          errors.special_requirements ? 'border-red-500' : 'border-slate-300'
        }`}
      />
      {errors.special_requirements && (
        <p className="text-red-500 text-sm mt-1">{errors.special_requirements.message}</p>
      )}
    </div>

    <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
      <div className="flex items-start">
        <CheckCircle className="w-5 h-5 text-blue-500 mr-2 mt-0.5" />
        <div className="text-sm">
          <p className="font-medium text-blue-900">Ready to Submit</p>
          <p className="text-blue-700">
            Review all information and click "Create Order" to submit your transport request.
            You'll be able to edit the order details after creation if needed.
          </p>
        </div>
      </div>
    </div>
  </div>
);
