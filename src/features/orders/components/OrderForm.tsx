import React from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button, Input, Card, CardContent, CardHeader, Badge } from '@/shared/components/ui'
import { useCreateOrder, useUpdateOrder } from '../hooks/useOrders'
import type { Order, OrderCreateRequest, OrderUpdateRequest } from '../types'

// Validation schema
const orderSchema = z.object({
  client_company_name: z.string().min(1, 'Company name is required'),
  client_vat_number: z
    .string()
    .min(1, 'VAT number is required')
    .regex(/^RO\d{2,10}$/, 'Invalid Romanian VAT number (format: RO########)'),
  client_contact_email: z
    .string()
    .email('Invalid email address')
    .optional()
    .or(z.literal('')),
  client_offered_price: z
    .number()
    .min(1, 'Price must be greater than 0')
    .max(999999, 'Price too high'),
  pickup_address: z.string().min(1, 'Pickup address is required'),
  pickup_postcode: z.string().optional(),
  pickup_city: z.string().optional(),
  pickup_country: z.string().default('RO'),
  delivery_address: z.string().min(1, 'Delivery address is required'),
  delivery_postcode: z.string().optional(),
  delivery_city: z.string().optional(),
  delivery_country: z.string().default('RO'),
  cargo_ldm: z.number().min(0).max(100).optional(),
  cargo_weight_kg: z.number().min(0).max(40000).optional(),
  cargo_pallets: z.number().int().min(0).max(33).optional(),
  cargo_description: z.string().optional(),
  special_requirements: z.string().optional(),
})

type OrderFormData = z.infer<typeof orderSchema>

interface OrderFormProps {
  order?: Order
  onSuccess?: (order: Order) => void
  onCancel?: () => void
  className?: string
}

export const OrderForm: React.FC<OrderFormProps> = ({
  order,
  onSuccess,
  onCancel,
  className = '',
}) => {
  const isEditing = !!order
  const createMutation = useCreateOrder()
  const updateMutation = useUpdateOrder()

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    watch,
    setValue,
  } = useForm<OrderFormData>({
    resolver: zodResolver(orderSchema),
    defaultValues: order ? {
      client_company_name: order.client_company_name,
      client_vat_number: order.client_vat_number,
      client_contact_email: order.client_contact_email || '',
      client_offered_price: order.client_offered_price,
      pickup_address: order.pickup_address,
      pickup_postcode: order.pickup_postcode || '',
      pickup_city: order.pickup_city || '',
      pickup_country: order.pickup_country || 'RO',
      delivery_address: order.delivery_address,
      delivery_postcode: order.delivery_postcode || '',
      delivery_city: order.delivery_city || '',
      delivery_country: order.delivery_country || 'RO',
      cargo_ldm: order.cargo_ldm || undefined,
      cargo_weight_kg: order.cargo_weight_kg || undefined,
      cargo_pallets: order.cargo_pallets || undefined,
      cargo_description: order.cargo_description || '',
      special_requirements: order.special_requirements || '',
    } : {
      pickup_country: 'RO',
      delivery_country: 'RO',
    },
  })

  const watchedPrice = watch('client_offered_price')

  const onSubmit = async (data: OrderFormData) => {
    try {
      if (isEditing && order) {
        const updateData: OrderUpdateRequest = {
          client_contact_email: data.client_contact_email || undefined,
          cargo_description: data.cargo_description || undefined,
          special_requirements: data.special_requirements || undefined,
        }
        const updatedOrder = await updateMutation.mutateAsync({
          orderId: order.order_id,
          data: updateData,
        })
        onSuccess?.(updatedOrder)
      } else {
        const createData: OrderCreateRequest = {
          client_company_name: data.client_company_name,
          client_vat_number: data.client_vat_number,
          client_contact_email: data.client_contact_email || undefined,
          client_offered_price: data.client_offered_price,
          pickup_address: data.pickup_address,
          pickup_postcode: data.pickup_postcode || undefined,
          pickup_city: data.pickup_city || undefined,
          pickup_country: data.pickup_country,
          delivery_address: data.delivery_address,
          delivery_postcode: data.delivery_postcode || undefined,
          delivery_city: data.delivery_city || undefined,
          delivery_country: data.delivery_country,
          cargo_ldm: data.cargo_ldm,
          cargo_weight_kg: data.cargo_weight_kg,
          cargo_pallets: data.cargo_pallets,
          cargo_description: data.cargo_description || undefined,
          special_requirements: data.special_requirements || undefined,
        }
        const newOrder = await createMutation.mutateAsync(createData)
        onSuccess?.(newOrder)
      }
    } catch (error) {
      // Error handling is done in the mutation hooks
      console.error('Form submission error:', error)
    }
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-xl font-semibold text-slate-900">
              {isEditing ? 'Edit Order' : 'Create New Order'}
            </h2>
            <p className="text-slate-600">
              {isEditing ? 'Update order information' : 'Enter order details for processing'}
            </p>
          </div>
          {isEditing && order && (
            <Badge className="bg-blue-100 text-blue-800">
              {order.order_status.replace('_', ' ').toUpperCase()}
            </Badge>
          )}
        </div>
      </CardHeader>

      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Client Information */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium text-slate-900 border-b border-slate-200 pb-2">
              Client Information
            </h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Company Name *
                </label>
                <Input
                  {...register('client_company_name')}
                  placeholder="e.g., ABC Logistics SRL"
                  disabled={isEditing}
                />
                {errors.client_company_name && (
                  <p className="mt-1 text-sm text-red-600">
                    {errors.client_company_name.message}
                  </p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  VAT Number *
                </label>
                <Input
                  {...register('client_vat_number')}
                  placeholder="RO12345678"
                  disabled={isEditing}
                />
                {errors.client_vat_number && (
                  <p className="mt-1 text-sm text-red-600">
                    {errors.client_vat_number.message}
                  </p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Contact Email
                </label>
                <Input
                  {...register('client_contact_email')}
                  type="email"
                  placeholder="contact@company.com"
                />
                {errors.client_contact_email && (
                  <p className="mt-1 text-sm text-red-600">
                    {errors.client_contact_email.message}
                  </p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Offered Price (EUR) *
                </label>
                <Input
                  {...register('client_offered_price', { valueAsNumber: true })}
                  type="number"
                  min="1"
                  max="999999"
                  step="0.01"
                  placeholder="1500.00"
                  disabled={isEditing}
                />
                {errors.client_offered_price && (
                  <p className="mt-1 text-sm text-red-600">
                    {errors.client_offered_price.message}
                  </p>
                )}
                {watchedPrice && (
                  <p className="mt-1 text-sm text-slate-500">
                    {new Intl.NumberFormat('ro-RO', {
                      style: 'currency',
                      currency: 'EUR',
                    }).format(watchedPrice)}
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Route Information */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium text-slate-900 border-b border-slate-200 pb-2">
              Route Information
            </h3>
            
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Pickup Location */}
              <div className="space-y-3">
                <h4 className="font-medium text-slate-800">Pickup Location</h4>
                
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Address *
                  </label>
                  <textarea
                    {...register('pickup_address')}
                    rows={3}
                    placeholder="Full pickup address"
                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-blue-500"
                    disabled={isEditing}
                  />
                  {errors.pickup_address && (
                    <p className="mt-1 text-sm text-red-600">
                      {errors.pickup_address.message}
                    </p>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">
                      City
                    </label>
                    <Input
                      {...register('pickup_city')}
                      placeholder="Bucuresti"
                      disabled={isEditing}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">
                      Postal Code
                    </label>
                    <Input
                      {...register('pickup_postcode')}
                      placeholder="010101"
                      disabled={isEditing}
                    />
                  </div>
                </div>
              </div>

              {/* Delivery Location */}
              <div className="space-y-3">
                <h4 className="font-medium text-slate-800">Delivery Location</h4>
                
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Address *
                  </label>
                  <textarea
                    {...register('delivery_address')}
                    rows={3}
                    placeholder="Full delivery address"
                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-blue-500"
                    disabled={isEditing}
                  />
                  {errors.delivery_address && (
                    <p className="mt-1 text-sm text-red-600">
                      {errors.delivery_address.message}
                    </p>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">
                      City
                    </label>
                    <Input
                      {...register('delivery_city')}
                      placeholder="Cluj-Napoca"
                      disabled={isEditing}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">
                      Postal Code
                    </label>
                    <Input
                      {...register('delivery_postcode')}
                      placeholder="400001"
                      disabled={isEditing}
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Cargo Information */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium text-slate-900 border-b border-slate-200 pb-2">
              Cargo Information
            </h3>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Loading Meters (LDM)
                </label>
                <Input
                  {...register('cargo_ldm', { valueAsNumber: true })}
                  type="number"
                  min="0"
                  max="100"
                  step="0.1"
                  placeholder="2.5"
                />
                {errors.cargo_ldm && (
                  <p className="mt-1 text-sm text-red-600">
                    {errors.cargo_ldm.message}
                  </p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Weight (kg)
                </label>
                <Input
                  {...register('cargo_weight_kg', { valueAsNumber: true })}
                  type="number"
                  min="0"
                  max="40000"
                  placeholder="1000"
                />
                {errors.cargo_weight_kg && (
                  <p className="mt-1 text-sm text-red-600">
                    {errors.cargo_weight_kg.message}
                  </p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Pallets
                </label>
                <Input
                  {...register('cargo_pallets', { valueAsNumber: true })}
                  type="number"
                  min="0"
                  max="33"
                  placeholder="4"
                />
                {errors.cargo_pallets && (
                  <p className="mt-1 text-sm text-red-600">
                    {errors.cargo_pallets.message}
                  </p>
                )}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Cargo Description
              </label>
              <textarea
                {...register('cargo_description')}
                rows={3}
                placeholder="Describe the cargo (optional)"
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Special Requirements
              </label>
              <textarea
                {...register('special_requirements')}
                rows={3}
                placeholder="Any special handling requirements (optional)"
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Form Actions */}
          <div className="flex justify-end gap-3 pt-6 border-t border-slate-200">
            {onCancel && (
              <Button type="button" variant="outline" onClick={onCancel}>
                Cancel
              </Button>
            )}
            <Button
              type="submit"
              disabled={isSubmitting}
              className="bg-blue-600 hover:bg-blue-700"
            >
              {isSubmitting
                ? (isEditing ? 'Updating...' : 'Creating...')
                : (isEditing ? 'Update Order' : 'Create Order')
              }
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
} 