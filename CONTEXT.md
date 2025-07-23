# 🚚 Romanian Freight Forwarder Automation System

## 📋 Executive Summary

A comprehensive AI-powered logistics automation platform designed to eliminate manual overhead for Romanian freight forwarders. The system provides end-to-end automation from email order intake to payment reconciliation, with intelligent document processing, subcontractor management, and financial tracking.

**Key Metrics:**
- 90-95% automated order processing
- ~80% reduction in manual administrative work
- Real-time profit tracking and analytics
- Complete audit trail and compliance management

---

## 🎯 Core Business Objectives

### Primary Goals
- **Eliminate Manual Data Entry**: AI-powered email and document parsing
- **Streamline Operations**: Automated subcontractor assignment and communication
- **Ensure Compliance**: EFACTURA validation and document archival
- **Maximize Profitability**: Real-time cost tracking and margin analysis
- **Reduce Errors**: Automated validation and cross-referencing

### Success Metrics
- Order processing time: < 5 minutes (from email to system)
- Document validation accuracy: > 95%
- Payment tracking automation: 100%
- User satisfaction: > 90% (internal dispatchers)

---

## 🏗️ System Architecture

### High-Level Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Email Agent   │    │  Core Backend   │    │   Web Frontend  │
│   (AI Parser)   │◄──►│   (FastAPI)     │◄──►│    (React)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Document Store │    │   PostgreSQL    │    │   File Storage  │
│   (S3/MinIO)    │    │   + PostGIS     │    │   (S3/MinIO)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Microservices Architecture
1. **Email Processing Service** - IMAP monitoring and AI parsing
2. **Order Management Service** - Core business logic and workflow
3. **Document Validation Service** - EFACTURA and POD validation
4. **Notification Service** - Email, SMS, and webhook notifications
5. **PDF Generation Service** - Dynamic document creation
6. **Payment Tracking Service** - Financial reconciliation and reminders
7. **Analytics Service** - Reporting and profit analysis

---

## 🔄 Complete Workflow Specification

### 1. Email Scanning & AI Document Processing

**Service**: Email Processing Service  
**Trigger**: IMAP polling every 30 seconds  
**AI Model**: Document understanding (GPT-4 Vision or Claude 3.5 Sonnet)

#### 1.1 Email Monitoring
```python
# Pseudo-implementation
class EmailMonitor:
    def scan_inbox(self):
        # Connect to IMAP server with OAuth2
        # Filter: PDF attachments, specific sender domains
        # Queue new emails for processing
        pass
```

#### 1.2 Document Extraction Pipeline
**Input**: PDF attachment  
**Output**: Structured order data

**Required Fields (Critical):**
- `client_company_name`: Company issuing the order
- `client_vat_number`: Tax identification
- `client_offered_price`: Total order value (EUR)
- `pickup_address`: Full address or postcode
- `delivery_address`: Full address or postcode

**Optional Fields (Enhancing):**
- `pickup_date_range`: Date window for pickup
- `delivery_date_range`: Date window for delivery
- `cargo_ldm`: Loading meters
- `cargo_weight_kg`: Weight in kilograms
- `cargo_pallets`: Number of pallets
- `special_requirements`: Temperature, hazmat, etc.
- `client_reference_number`: Internal client order ID

#### 1.3 AI Prompt Engineering
```
SYSTEM: You are an expert logistics document parser for Romanian freight forwarders.

TASK: Extract structured data from transport order PDFs with high accuracy.

CRITICAL REQUIREMENTS:
1. Client company name and VAT must be extracted precisely
2. Addresses should be geocoded and validated
3. Prices must include currency (assume EUR if not specified)
4. Date ranges should accommodate flexible pickup/delivery windows
5. Flag any ambiguous or missing critical information

OUTPUT FORMAT: Valid JSON matching the OrderData schema
ERROR HANDLING: Return confidence scores for each extracted field
```

#### 1.4 Post-Processing & Validation
- **Geocoding**: Validate addresses using PostGIS + external APIs
- **Business Validation**: Check VAT numbers against EU VIES database
- **Duplicate Detection**: Compare against existing orders (fuzzy matching)
- **Quality Scoring**: Confidence levels for each extracted field

#### 1.5 Error Handling
```python
class ProcessingError(Enum):
    MISSING_CRITICAL_FIELD = "critical_field_missing"
    INVALID_PDF_FORMAT = "pdf_unreadable"
    MULTIPLE_ORDERS_DETECTED = "manual_split_required"
    LOW_CONFIDENCE_EXTRACTION = "manual_review_required"
    GEOCODING_FAILED = "address_validation_failed"
```

### 2. Order Creation & Database Management

**Service**: Order Management Service  
**Database**: PostgreSQL with full ACID compliance

#### 2.1 Database Schema

```sql
-- Core Orders Table
CREATE TABLE orders (
    order_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Client Information
    client_company_name VARCHAR(255) NOT NULL,
    client_vat_number VARCHAR(50) NOT NULL,
    client_contact_email VARCHAR(255),
    client_payment_terms VARCHAR(100) DEFAULT '30 days after delivery',
    client_offered_price DECIMAL(10,2) NOT NULL,
    
    -- Route Information
    pickup_address TEXT NOT NULL,
    pickup_postcode VARCHAR(20),
    pickup_city VARCHAR(100),
    pickup_country VARCHAR(2) DEFAULT 'RO',
    pickup_coordinates GEOMETRY(POINT, 4326),
    pickup_date_start DATE,
    pickup_date_end DATE,
    
    delivery_address TEXT NOT NULL,
    delivery_postcode VARCHAR(20),
    delivery_city VARCHAR(100),
    delivery_country VARCHAR(2),
    delivery_coordinates GEOMETRY(POINT, 4326),
    delivery_date_start DATE,
    delivery_date_end DATE,
    
    -- Cargo Information
    cargo_ldm DECIMAL(5,2),
    cargo_weight_kg DECIMAL(8,2),
    cargo_pallets INTEGER,
    cargo_description TEXT,
    special_requirements TEXT,
    
    -- Subcontractor Information
    subcontractor_id UUID REFERENCES subcontractors(id),
    subcontractor_price DECIMAL(10,2),
    subcontractor_payment_terms VARCHAR(100),
    truck_plate VARCHAR(20),
    driver_contact VARCHAR(100),
    
    -- Financial Tracking
    profit_margin DECIMAL(10,2) GENERATED ALWAYS AS (client_offered_price - subcontractor_price) STORED,
    profit_percentage DECIMAL(5,2) GENERATED ALWAYS AS ((client_offered_price - subcontractor_price) / client_offered_price * 100) STORED,
    
    -- Status Management
    order_status order_status_enum DEFAULT 'pending',
    uit_code VARCHAR(50) UNIQUE, -- Unique Interaction Token
    
    -- Document References
    original_pdf_path VARCHAR(500),
    generated_order_pdf_path VARCHAR(500),
    invoice_pdf_path VARCHAR(500),
    pod_pdf_path VARCHAR(500),
    
    -- Metadata
    extraction_confidence DECIMAL(3,2),
    manual_review_required BOOLEAN DEFAULT FALSE,
    notes TEXT
);

-- Order Status Enum
CREATE TYPE order_status_enum AS ENUM (
    'pending',           -- Just created, awaiting subcontractor assignment
    'assigned',          -- Subcontractor assigned, order sent
    'in_transit',        -- Cargo picked up, in transit
    'awaiting_documents', -- Delivered, awaiting POD + invoice
    'documents_received', -- Documents uploaded, pending validation
    'documents_validated', -- All documents validated
    'client_invoiced',    -- Invoice sent to client
    'payment_received',   -- Client payment confirmed
    'subcontractor_paid', -- Subcontractor payment completed
    'completed',         -- Order fully completed
    'cancelled',         -- Order cancelled
    'disputed'           -- Payment or delivery dispute
);

-- Subcontractors Table
CREATE TABLE subcontractors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name VARCHAR(255) NOT NULL,
    vat_number VARCHAR(50) UNIQUE NOT NULL,
    contact_person VARCHAR(255),
    phone VARCHAR(50),
    email VARCHAR(255) NOT NULL,
    address TEXT,
    
    -- Performance Metrics
    total_orders INTEGER DEFAULT 0,
    successful_orders INTEGER DEFAULT 0,
    average_rating DECIMAL(3,2),
    
    -- Financial
    preferred_payment_terms VARCHAR(100),
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Document Validation Table
CREATE TABLE document_validations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID REFERENCES orders(order_id),
    document_type VARCHAR(50) NOT NULL, -- 'invoice', 'pod'
    file_path VARCHAR(500) NOT NULL,
    upload_timestamp TIMESTAMPTZ DEFAULT NOW(),
    
    -- Validation Results
    is_valid BOOLEAN,
    validation_errors JSONB,
    validation_timestamp TIMESTAMPTZ,
    
    -- Invoice-specific
    invoice_total DECIMAL(10,2),
    invoice_currency VARCHAR(3),
    invoice_number VARCHAR(100),
    is_efactura_compliant BOOLEAN,
    
    -- Metadata
    file_size_bytes INTEGER,
    file_hash VARCHAR(64),
    processed_by_user_id UUID
);
```

#### 2.2 Order Creation Logic
```python
@dataclass
class OrderCreationRequest:
    extracted_data: Dict[str, Any]
    confidence_scores: Dict[str, float]
    original_pdf_path: str
    processing_metadata: Dict[str, Any]

class OrderService:
    async def create_order(self, request: OrderCreationRequest) -> Order:
        # Validate critical fields
        self._validate_required_fields(request.extracted_data)
        
        # Geocode addresses
        pickup_coords = await self.geocoding_service.geocode(
            request.extracted_data['pickup_address']
        )
        delivery_coords = await self.geocoding_service.geocode(
            request.extracted_data['delivery_address']
        )
        
        # Generate UIT code
        uit_code = self._generate_uit_code()
        
        # Create order record
        order = Order(
            **request.extracted_data,
            pickup_coordinates=pickup_coords,
            delivery_coordinates=delivery_coords,
            uit_code=uit_code,
            extraction_confidence=min(request.confidence_scores.values()),
            manual_review_required=self._requires_manual_review(request)
        )
        
        # Save to database
        return await self.repository.save(order)
```

### 3. Subcontractor Assignment & Management

**Service**: Order Management Service  
**Interface**: Web Frontend with real-time updates

#### 3.1 Assignment Interface
```typescript
interface SubcontractorAssignmentModal {
  orderId: string;
  availableSubcontractors: Subcontractor[];
  route: {
    pickupLocation: Location;
    deliveryLocation: Location;
    estimatedDistance: number;
    estimatedDuration: string;
  };
  profitCalculator: {
    clientPrice: number;
    suggestedMargin: number;
    minimumMargin: number;
  };
}

interface SubcontractorAssignment {
  subcontractorId: string;
  agreedPrice: number;
  paymentTerms: string;
  truckPlate: string;
  driverContact: string;
  pickupDate: DateRange;
  deliveryDate: DateRange;
  specialInstructions?: string;
}
```

#### React Component Examples

```typescript
// OrderCard.tsx - Main order display component
import React, { useState } from 'react';
import { Order, OrderStatus } from '@/types/order';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { MapPin, Truck, Calendar, Euro } from 'lucide-react';

interface OrderCardProps {
  order: Order;
  onAssignSubcontractor: (orderId: string) => void;
  onViewDetails: (orderId: string) => void;
}

export const OrderCard: React.FC<OrderCardProps> = ({
  order,
  onAssignSubcontractor,
  onViewDetails
}) => {
  const [isLoading, setIsLoading] = useState(false);

  const getStatusColor = (status: OrderStatus): string => {
    const colors = {
      pending: 'bg-yellow-100 text-yellow-800',
      assigned: 'bg-blue-100 text-blue-800',
      in_transit: 'bg-purple-100 text-purple-800',
      awaiting_documents: 'bg-orange-100 text-orange-800',
      completed: 'bg-green-100 text-green-800',
      cancelled: 'bg-red-100 text-red-800'
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const handleAssignment = async () => {
    setIsLoading(true);
    try {
      await onAssignSubcontractor(order.order_id);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200 hover:shadow-lg transition-shadow">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">
            Order #{order.order_id.slice(0, 8)}
          </h3>
          <Badge className={getStatusColor(order.order_status)}>
            {order.order_status.replace('_', ' ').toUpperCase()}
          </Badge>
        </div>
        <div className="text-right">
          <p className="text-sm text-gray-500">Client Price</p>
          <p className="text-lg font-bold text-green-600 flex items-center">
            <Euro className="w-4 h-4 mr-1" />
            {order.client_offered_price.toLocaleString()}
          </p>
        </div>
      </div>

      <div className="space-y-3">
        <div className="flex items-center text-sm text-gray-600">
          <MapPin className="w-4 h-4 mr-2 text-gray-400" />
          <span className="font-medium">From:</span>
          <span className="ml-1">{order.pickup_city}, {order.pickup_postcode}</span>
        </div>
        
        <div className="flex items-center text-sm text-gray-600">
          <MapPin className="w-4 h-4 mr-2 text-gray-400" />
          <span className="font-medium">To:</span>
          <span className="ml-1">{order.delivery_city}, {order.delivery_postcode}</span>
        </div>

        {order.subcontractor_company && (
          <div className="flex items-center text-sm text-gray-600">
            <Truck className="w-4 h-4 mr-2 text-gray-400" />
            <span className="font-medium">Carrier:</span>
            <span className="ml-1">{order.subcontractor_company}</span>
          </div>
        )}

        <div className="flex items-center text-sm text-gray-600">
          <Calendar className="w-4 h-4 mr-2 text-gray-400" />
          <span className="font-medium">Pickup:</span>
          <span className="ml-1">{order.pickup_date_start || 'TBD'}</span>
        </div>
      </div>

      <div className="flex gap-2 mt-4 pt-4 border-t border-gray-100">
        <Button
          variant="outline"
          size="sm"
          onClick={() => onViewDetails(order.order_id)}
          className="flex-1"
        >
          View Details
        </Button>
        
        {order.order_status === 'pending' && (
          <Button
            onClick={handleAssignment}
            disabled={isLoading}
            size="sm"
            className="flex-1"
          >
            {isLoading ? 'Assigning...' : 'Assign Carrier'}
          </Button>
        )}
      </div>
    </div>
  );
};

// OrderForm.tsx - Create/Edit order form
import React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { OrderCreateRequest } from '@/types/order';

const orderSchema = z.object({
  client_company_name: z.string().min(1, 'Company name is required'),
  client_vat_number: z.string().min(1, 'VAT number is required'),
  client_contact_email: z.string().email('Valid email is required'),
  client_offered_price: z.number().min(1, 'Price must be greater than 0'),
  pickup_address: z.string().min(1, 'Pickup address is required'),
  pickup_postcode: z.string().min(1, 'Pickup postcode is required'),
  pickup_city: z.string().min(1, 'Pickup city is required'),
  delivery_address: z.string().min(1, 'Delivery address is required'),
  delivery_postcode: z.string().min(1, 'Delivery postcode is required'),
  delivery_city: z.string().min(1, 'Delivery city is required'),
  cargo_ldm: z.number().optional(),
  cargo_weight_kg: z.number().optional(),
  cargo_pallets: z.number().optional(),
  special_requirements: z.string().optional(),
});

interface OrderFormProps {
  initialData?: Partial<OrderCreateRequest>;
  onSubmit: (data: OrderCreateRequest) => Promise<void>;
  onCancel: () => void;
}

export const OrderForm: React.FC<OrderFormProps> = ({
  initialData,
  onSubmit,
  onCancel
}) => {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<OrderCreateRequest>({
    resolver: zodResolver(orderSchema),
    defaultValues: initialData,
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Company Name *
          </label>
          <input
            {...register('client_company_name')}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
          />
          {errors.client_company_name && (
            <p className="mt-1 text-sm text-red-600">
              {errors.client_company_name.message}
            </p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">
            VAT Number *
          </label>
          <input
            {...register('client_vat_number')}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
          />
          {errors.client_vat_number && (
            <p className="mt-1 text-sm text-red-600">
              {errors.client_vat_number.message}
            </p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Pickup Address *
          </label>
          <textarea
            {...register('pickup_address')}
            rows={3}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
          />
          {errors.pickup_address && (
            <p className="mt-1 text-sm text-red-600">
              {errors.pickup_address.message}
            </p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">
            Delivery Address *
          </label>
          <textarea
            {...register('delivery_address')}
            rows={3}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
          />
          {errors.delivery_address && (
            <p className="mt-1 text-sm text-red-600">
              {errors.delivery_address.message}
            </p>
          )}
        </div>
      </div>

      <div className="flex justify-end gap-3">
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Creating...' : 'Create Order'}
        </Button>
      </div>
    </form>
  );
};

// Dashboard.tsx - Main dashboard component
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { OrderCard } from '@/components/OrderCard';
import { DashboardMetrics } from '@/components/DashboardMetrics';
import { useOrders } from '@/hooks/useOrders';
import { useSubcontractorAssignment } from '@/hooks/useSubcontractorAssignment';

export const Dashboard: React.FC = () => {
  const { data: orders, isLoading } = useOrders();
  const { openAssignmentModal } = useSubcontractorAssignment();

  const handleAssignSubcontractor = (orderId: string) => {
    openAssignmentModal(orderId);
  };

  const handleViewDetails = (orderId: string) => {
    // Navigate to order details page
    window.location.href = `/orders/${orderId}`;
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <DashboardMetrics />
      
      <div className="mt-8">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Recent Orders</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {orders?.map((order) => (
            <OrderCard
              key={order.order_id}
              order={order}
              onAssignSubcontractor={handleAssignSubcontractor}
              onViewDetails={handleViewDetails}
            />
          ))}
        </div>
      </div>
    </div>
  );
};
```

#### 3.2 Smart Subcontractor Recommendation
```python
class SubcontractorRecommendationEngine:
    def recommend_subcontractors(self, order: Order) -> List[SubcontractorRecommendation]:
        # Factor in: route familiarity, past performance, pricing, availability
        candidates = self._get_qualified_subcontractors(order)
        
        recommendations = []
        for subcontractor in candidates:
            score = self._calculate_recommendation_score(
                subcontractor, order, 
                factors=['price', 'reliability', 'route_experience', 'availability']
            )
            
            estimated_price = self._estimate_pricing(subcontractor, order)
            
            recommendations.append(SubcontractorRecommendation(
                subcontractor=subcontractor,
                score=score,
                estimated_price=estimated_price,
                reasoning=self._generate_reasoning(subcontractor, order)
            ))
        
        return sorted(recommendations, key=lambda x: x.score, reverse=True)[:5]
```

#### 3.3 Order PDF Generation
```python
class OrderPDFGenerator:
    def generate_transport_order(self, order: Order, subcontractor: Subcontractor) -> bytes:
        template = self._load_template('transport_order_template.html')
        
        context = {
            'order': order,
            'subcontractor': subcontractor,
            'qr_code': self._generate_qr_code(order.uit_code),
            'tracking_url': f"{self.base_url}/track/{order.uit_code}",
            'upload_url': f"{self.base_url}/upload/{order.uit_code}",
            'generated_at': datetime.now().isoformat()
        }
        
        html_content = template.render(context)
        return self._html_to_pdf(html_content)
```

### 4. Document Upload & Validation Portal

**Service**: Document Validation Service  
**Interface**: Public portal accessible via UIT code

#### 4.1 Document Upload Interface
```python
class DocumentUploadEndpoint:
    @router.post("/upload/{uit_code}")
    async def upload_documents(
        self, 
        uit_code: str,
        invoice_file: UploadFile,
        pod_file: UploadFile,
        additional_files: List[UploadFile] = None
    ):
        # Validate UIT code
        order = await self._validate_uit_code(uit_code)
        
        # Store files securely
        invoice_path = await self._store_file(invoice_file, order.order_id, 'invoice')
        pod_path = await self._store_file(pod_file, order.order_id, 'pod')
        
        # Queue validation jobs
        await self.validation_queue.enqueue_validation(order.order_id, invoice_path, pod_path)
        
        return {"status": "uploaded", "validation_in_progress": True}
```

#### 4.2 EFACTURA Validation Engine
```python
class EFacturaValidator:
    def validate_invoice(self, file_path: str, expected_data: Dict) -> ValidationResult:
        # Parse XML structure
        xml_content = self._parse_xml(file_path)
        
        validations = []
        
        # Structure validation
        if not self._validate_xml_schema(xml_content):
            validations.append(ValidationError("Invalid EFACTURA XML schema"))
        
        # Business validation
        invoice_total = self._extract_total(xml_content)
        if abs(invoice_total - expected_data['agreed_price']) > 0.01:
            validations.append(ValidationError(
                f"Invoice total {invoice_total} doesn't match agreed price {expected_data['agreed_price']}"
            ))
        
        # VAT validation
        supplier_vat = self._extract_supplier_vat(xml_content)
        if supplier_vat != expected_data['subcontractor_vat']:
            validations.append(ValidationError("VAT number mismatch"))
        
        return ValidationResult(
            is_valid=len(validations) == 0,
            errors=validations,
            extracted_data=self._extract_invoice_data(xml_content)
        )
```

### 5. Client Invoicing & Communication

**Service**: PDF Generation Service + Notification Service

#### 5.1 Automated Invoice Generation
```python
class ClientInvoiceGenerator:
    async def generate_client_invoice(self, order: Order) -> InvoiceResult:
        # Calculate totals including any fees
        subtotal = order.client_offered_price
        vat_amount = subtotal * 0.19  # Romanian VAT rate
        total = subtotal + vat_amount
        
        invoice_data = {
            'invoice_number': self._generate_invoice_number(),
            'issue_date': date.today(),
            'due_date': self._calculate_due_date(order.client_payment_terms),
            'client': self._get_client_data(order),
            'order_details': self._format_order_details(order),
            'subtotal': subtotal,
            'vat_amount': vat_amount,
            'total': total,
            'payment_terms': order.client_payment_terms
        }
        
        # Generate PDF
        pdf_content = await self.pdf_generator.generate_invoice(invoice_data)
        
        # Attach supporting documents
        attachments = [
            ('pod.pdf', order.pod_pdf_path),
            ('transport_order.pdf', order.generated_order_pdf_path)
        ]
        
        # Send email
        await self.email_service.send_invoice(
            to=order.client_contact_email,
            invoice_pdf=pdf_content,
            attachments=attachments,
            invoice_data=invoice_data
        )
        
        return InvoiceResult(
            invoice_number=invoice_data['invoice_number'],
            pdf_path=pdf_path,
            sent_at=datetime.now()
        )
```

### 6. Payment Tracking & Reminders

**Service**: Payment Tracking Service  
**Trigger**: Daily cron job + real-time webhooks

#### 6.1 Payment Status Management
```python
class PaymentTracker:
    def check_overdue_payments(self) -> List[OverduePayment]:
        overdue_orders = self.repository.get_orders_by_status([
            'client_invoiced', 'subcontractor_paid'
        ])
        
        overdue_payments = []
        for order in overdue_orders:
            if self._is_overdue(order):
                overdue_payments.append(OverduePayment(
                    order=order,
                    days_overdue=self._calculate_days_overdue(order),
                    amount=order.client_offered_price,
                    reminder_level=self._get_reminder_level(order)
                ))
        
        return overdue_payments
    
    async def send_payment_reminders(self):
        overdue_payments = self.check_overdue_payments()
        
        for payment in overdue_payments:
            if payment.reminder_level == 'gentle':
                await self._send_gentle_reminder(payment)
            elif payment.reminder_level == 'firm':
                await self._send_firm_reminder(payment)
            elif payment.reminder_level == 'final':
                await self._send_final_notice(payment)
```

### 7. Advanced Features

#### 7.1 Real-time Analytics Dashboard
```typescript
interface DashboardMetrics {
  totalOrders: number;
  ordersInProgress: number;
  totalRevenue: number;
  totalProfit: number;
  averageMargin: number;
  paymentOverdue: number;
  topSubcontractors: SubcontractorPerformance[];
  recentActivity: ActivityEvent[];
}

interface ActivityEvent {
  timestamp: Date;
  type: 'order_created' | 'order_assigned' | 'documents_uploaded' | 'payment_received';
  orderId: string;
  description: string;
  metadata: Record<string, any>;
}
```

#### 7.2 Audit Trail & Compliance
```python
class AuditLogger:
    def log_action(self, user_id: str, action: str, resource_id: str, changes: Dict):
        audit_entry = AuditEntry(
            user_id=user_id,
            action=action,
            resource_type='order',
            resource_id=resource_id,
            changes=changes,
            timestamp=datetime.now(),
            ip_address=self._get_client_ip(),
            user_agent=self._get_user_agent()
        )
        
        self.repository.save_audit_entry(audit_entry)
```

---

## 🛠️ Technical Implementation Guide

### **Optimal Tech Stack** ⭐ **Context7 Validated**

> **✅ Fully Validated**: This tech stack has been comprehensively validated using Context7 documentation analysis. All major technologies have high trust scores (8-10), extensive code examples (469-115,976 snippets), and align with current industry best practices.

#### **Backend: Python + FastAPI** 
```yaml
Language: Python 3.11+
Framework: FastAPI (async/await, auto-docs, Pydantic validation)
Database: PostgreSQL 15+ with PostGIS (geographic data + ACID compliance)
Cache/Session: Redis 7+ (sub-millisecond performance)
Message Queue: Celery + Redis (AI processing, email tasks)
File Storage: MinIO (S3-compatible, cost-effective for documents)
Email: IMAP/SMTP with OAuth2 (Gmail Business, Outlook)
PDF Processing: PyMuPDF + pdf-plumber (best Python PDF libraries)
AI/ML: OpenAI GPT-4 Vision + Claude 3.5 Sonnet (redundancy)
Validation: Pydantic v2 (type safety, JSON schema generation)
ORM: SQLAlchemy 2.0 + Alembic (modern async ORM)
Auth: FastAPI-Users + JWT (OAuth2, multi-provider support)
```

#### **Frontend: React 18 + TypeScript + Vite**
```yaml
Framework: React 18 (concurrent features, server components ready)
Language: TypeScript 5+ (strict mode, latest features)
Build Tool: Vite (fastest builds, great DX)
Styling: Tailwind CSS + shadcn/ui (modern, accessible components)
State Management: Zustand (simple, performant, TypeScript-first)
Data Fetching: TanStack Query v4 (caching, background updates)
Forms: React Hook Form + Zod (performance + validation)
Charts: Recharts (React-native charts, great TypeScript)
Maps: Mapbox GL JS (best performance for geographic data)
Date/Time: date-fns (tree-shakeable, immutable)
Notifications: Sonner (beautiful toast notifications)
Tables: TanStack Table (headless, powerful data tables)
```

#### **DevOps & Infrastructure**
```yaml
Containerization: Docker + Docker Compose (development)
Orchestration: Kubernetes (production, auto-scaling)
CI/CD: GitHub Actions (free, excellent integration)
Monitoring: Prometheus + Grafana (metrics, alerting)
Error Tracking: Sentry (best-in-class error monitoring)
Logging: Loguru (structured logging, Python-native)
Load Balancing: Traefik (automatic HTTPS, service discovery)
Secrets Management: HashiCorp Vault (production) / Docker secrets (dev)
Backup: PostgreSQL streaming replication + MinIO versioning
```

#### **Real-time & Communication**
```yaml
Real-time Updates: Server-Sent Events (SSE) - simpler than WebSockets
Email Service: Mailgun API (deliverability) + SMTP fallback
SMS Notifications: Twilio (payment reminders, urgent alerts)
Push Notifications: OneSignal (web push for dispatcher dashboard)
Webhooks: FastAPI background tasks (payment confirmations)
```

#### **AI & Document Processing** ⭐ **Validated & Optimized**
```yaml
Primary AI: OpenAI GPT-4 Vision (best document understanding - Context7 validated)
Backup AI: Anthropic Claude 3.5 Sonnet (redundancy, different strengths)
Fallback AI: Azure OpenAI (enterprise compliance, data residency)
OCR Preprocessing: Tesseract 5+ (open source, handles poor quality scans)
Image Processing: Pillow 10+ + OpenCV 4.8+ (image enhancement before AI)
PDF Libraries: PyMuPDF 1.23+ (fastest), pdf-plumber 0.10+ (layout analysis)
Document Storage: MinIO latest with versioning (immutable document history)
AI Framework: LangChain 0.1+ (optional - for advanced AI workflows)
Vector Storage: Redis Stack with RediSearch (for document similarity if needed)
```

#### **Testing & Quality**
```yaml
Backend Testing: pytest + pytest-asyncio + pytest-mock
Frontend Testing: Vitest + Testing Library + MSW (mock service worker)
E2E Testing: Playwright (multi-browser, reliable)
Load Testing: Locust (Python-based, easy to customize)
Code Quality: Black + isort + flake8 + mypy (Python), ESLint + Prettier (TS)
Security Scanning: Bandit (Python), npm audit (Node)
Coverage: Coverage.py (backend), Vitest coverage (frontend)
```

#### **Development Tools**
```yaml
IDE: VS Code with extensions (Python, TypeScript, Docker)
API Documentation: FastAPI auto-generated OpenAPI + Swagger UI
Database Tools: pgAdmin 4, DBeaver (development)
Redis GUI: RedisInsight (official Redis GUI)
Debugging: FastAPI debugger, React DevTools, Chrome DevTools
Performance: Django Debug Toolbar (dev), React Profiler
```

### **Technology Validation Summary** 📊

#### **Context7 Validation Results**
| Technology | Trust Score | Code Snippets | Status | Notes |
|------------|-------------|---------------|--------|-------|
| **FastAPI** | 9.9/10 | 1,039 | ✅ Excellent | Official source, async patterns validated |
| **React 18** | 10/10 | 2,053 | ✅ Outstanding | TypeScript integration confirmed |
| **PostgreSQL** | 8.4-9.6/10 | 289+ | ✅ Excellent | Multiple high-quality libraries |
| **Redis** | 10/10 | 115,976 | ✅ Outstanding | Most comprehensive documentation |
| **Celery** | 9.1/10 | 1,777 | ✅ Excellent | Battle-tested for background tasks |
| **Vite** | 8.3/10 | 671 | ✅ Excellent | Modern build tool, great performance |
| **Zustand** | 9.6/10 | 469 | ✅ Outstanding | Perfect for React state management |
| **TanStack Query** | 8/10 | 980 | ✅ Excellent | Industry standard for data fetching |

#### **Architecture Pattern Validation**
- ✅ **Project Structure**: Aligns with FastAPI official recommendations
- ✅ **Async Patterns**: Confirmed best practices for I/O-bound operations  
- ✅ **TypeScript Integration**: Follows React 18 type safety guidelines
- ✅ **Testing Strategy**: Matches pytest and Vitest recommendations
- ✅ **Database Design**: PostgreSQL + PostGIS patterns validated
- ✅ **Caching Strategy**: Redis usage patterns confirmed optimal

### **Project Structure** 📁

```
logistics-ai/
├── 📁 backend/                          # FastAPI backend service
│   ├── 📁 app/
│   │   ├── 📄 __init__.py
│   │   ├── 📄 main.py                   # FastAPI app initialization
│   │   ├── 📄 config.py                 # Settings & environment variables
│   │   ├── 📄 dependencies.py           # Dependency injection
│   │   │
│   │   ├── 📁 api/                      # API routes
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📁 v1/
│   │   │   │   ├── 📄 __init__.py
│   │   │   │   ├── 📄 orders.py         # Order management endpoints
│   │   │   │   ├── 📄 subcontractors.py # Subcontractor endpoints
│   │   │   │   ├── 📄 documents.py      # Document upload endpoints
│   │   │   │   ├── 📄 analytics.py      # Dashboard & reporting
│   │   │   │   ├── 📄 auth.py           # Authentication endpoints
│   │   │   │   └── 📄 webhooks.py       # External webhook handlers
│   │   │   └── 📁 internal/             # Internal service APIs
│   │   │       ├── 📄 email_processing.py
│   │   │       ├── 📄 document_validation.py
│   │   │       └── 📄 payment_tracking.py
│   │   │
│   │   ├── 📁 core/                     # Core business logic
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 security.py           # Auth & security utilities
│   │   │   ├── 📄 database.py           # Database connection
│   │   │   ├── 📄 cache.py              # Redis cache management
│   │   │   └── 📄 logging.py            # Structured logging setup
│   │   │
│   │   ├── 📁 models/                   # SQLAlchemy models
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 base.py               # Base model class
│   │   │   ├── 📄 orders.py             # Order model
│   │   │   ├── 📄 subcontractors.py     # Subcontractor model
│   │   │   ├── 📄 users.py              # User & auth models
│   │   │   ├── 📄 documents.py          # Document validation models
│   │   │   └── 📄 audit.py              # Audit trail models
│   │   │
│   │   ├── 📁 schemas/                  # Pydantic schemas
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 orders.py             # Order request/response schemas
│   │   │   ├── 📄 subcontractors.py     # Subcontractor schemas
│   │   │   ├── 📄 users.py              # User schemas
│   │   │   ├── 📄 documents.py          # Document schemas
│   │   │   └── 📄 common.py             # Shared schemas
│   │   │
│   │   ├── 📁 services/                 # Business logic services
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 order_service.py      # Order management logic
│   │   │   ├── 📄 email_service.py      # Email processing service
│   │   │   ├── 📄 ai_service.py         # AI document parsing
│   │   │   ├── 📄 validation_service.py # Document validation
│   │   │   ├── 📄 payment_service.py    # Payment tracking
│   │   │   ├── 📄 notification_service.py # Email/SMS notifications
│   │   │   ├── 📄 pdf_service.py        # PDF generation
│   │   │   ├── 📄 geocoding_service.py  # Address geocoding
│   │   │   └── 📄 analytics_service.py  # Business analytics
│   │   │
│   │   ├── 📁 repositories/             # Data access layer
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 base.py               # Base repository class
│   │   │   ├── 📄 order_repository.py   # Order data access
│   │   │   ├── 📄 subcontractor_repository.py
│   │   │   ├── 📄 user_repository.py
│   │   │   └── 📄 document_repository.py
│   │   │
│   │   ├── 📁 tasks/                    # Celery background tasks
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 celery_app.py         # Celery configuration
│   │   │   ├── 📄 email_tasks.py        # Email processing tasks
│   │   │   ├── 📄 document_tasks.py     # Document processing tasks
│   │   │   ├── 📄 payment_tasks.py      # Payment reminder tasks
│   │   │   └── 📄 cleanup_tasks.py      # Maintenance tasks
│   │   │
│   │   ├── 📁 utils/                    # Utility functions
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 date_utils.py         # Date/time utilities
│   │   │   ├── 📄 file_utils.py         # File handling utilities
│   │   │   ├── 📄 validation_utils.py   # Custom validators
│   │   │   ├── 📄 geo_utils.py          # Geographic utilities
│   │   │   └── 📄 encryption_utils.py   # Data encryption
│   │   │
│   │   └── 📁 middleware/               # Custom middleware
│   │       ├── 📄 __init__.py
│   │       ├── 📄 cors.py               # CORS configuration
│   │       ├── 📄 rate_limiting.py      # Rate limiting
│   │       ├── 📄 metrics.py            # Prometheus metrics
│   │       └── 📄 audit.py              # Audit logging
│   │
│   ├── 📁 migrations/                   # Alembic database migrations
│   │   ├── 📄 env.py
│   │   ├── 📄 script.py.mako
│   │   └── 📁 versions/
│   │       └── 📄 001_initial_schema.py
│   │
│   ├── 📁 tests/                        # Backend tests
│   │   ├── 📄 __init__.py
│   │   ├── 📄 conftest.py               # Pytest configuration
│   │   ├── 📁 unit/                     # Unit tests
│   │   │   ├── 📄 test_order_service.py
│   │   │   ├── 📄 test_ai_service.py
│   │   │   └── 📄 test_validation_service.py
│   │   ├── 📁 integration/              # Integration tests
│   │   │   ├── 📄 test_api_orders.py
│   │   │   ├── 📄 test_database.py
│   │   │   └── 📄 test_external_services.py
│   │   └── 📁 fixtures/                 # Test data
│   │       ├── 📄 sample_orders.json
│   │       └── 📁 sample_pdfs/
│   │
│   ├── 📁 templates/                    # PDF & email templates
│   │   ├── 📁 pdf/
│   │   │   ├── 📄 transport_order.html
│   │   │   ├── 📄 client_invoice.html
│   │   │   └── 📄 payment_reminder.html
│   │   └── 📁 email/
│   │       ├── 📄 order_notification.html
│   │       ├── 📄 payment_reminder.html
│   │       └── 📄 document_upload_confirmation.html
│   │
│   ├── 📄 requirements.txt              # Python dependencies
│   ├── 📄 requirements-dev.txt          # Development dependencies
│   ├── 📄 pyproject.toml               # Python project configuration
│   ├── 📄 alembic.ini                  # Database migration config
│   ├── 📄 Dockerfile                   # Production Docker image
│   ├── 📄 Dockerfile.dev               # Development Docker image
│   └── 📄 .env.example                 # Environment variables template
│
├── 📁 frontend/                         # React TypeScript frontend
│   ├── 📁 public/
│   │   ├── 📄 index.html
│   │   ├── 📄 manifest.json
│   │   └── 📁 icons/
│   │
│   ├── 📁 src/
│   │   ├── 📄 main.tsx                  # React app entry point
│   │   ├── 📄 App.tsx                   # Main app component
│   │   ├── 📄 index.css                 # Global styles
│   │   ├── 📄 vite-env.d.ts            # Vite type definitions
│   │   │
│   │   ├── 📁 components/               # Reusable UI components
│   │   │   ├── 📁 ui/                   # shadcn/ui components
│   │   │   │   ├── 📄 button.tsx
│   │   │   │   ├── 📄 input.tsx
│   │   │   │   ├── 📄 dialog.tsx
│   │   │   │   ├── 📄 table.tsx
│   │   │   │   └── 📄 toast.tsx
│   │   │   ├── 📁 forms/                # Form components
│   │   │   │   ├── 📄 OrderForm.tsx
│   │   │   │   ├── 📄 SubcontractorForm.tsx
│   │   │   │   └── 📄 DocumentUpload.tsx
│   │   │   ├── 📁 layout/               # Layout components
│   │   │   │   ├── 📄 Header.tsx
│   │   │   │   ├── 📄 Sidebar.tsx
│   │   │   │   ├── 📄 Footer.tsx
│   │   │   │   └── 📄 PageLayout.tsx
│   │   │   └── 📁 business/             # Business-specific components
│   │   │       ├── 📄 OrderCard.tsx
│   │   │       ├── 📄 OrderStatusBadge.tsx
│   │   │       ├── 📄 ProfitChart.tsx
│   │   │       └── 📄 RouteMap.tsx
│   │   │
│   │   ├── 📁 pages/                    # Page components
│   │   │   ├── 📄 Dashboard.tsx         # Main dashboard
│   │   │   ├── 📄 Orders.tsx            # Orders management
│   │   │   ├── 📄 OrderDetails.tsx      # Single order view
│   │   │   ├── 📄 Subcontractors.tsx    # Subcontractor management
│   │   │   ├── 📄 Analytics.tsx         # Business analytics
│   │   │   ├── 📄 Settings.tsx          # System settings
│   │   │   ├── 📄 Login.tsx             # Authentication
│   │   │   └── 📄 DocumentUpload.tsx    # Public upload portal
│   │   │
│   │   ├── 📁 hooks/                    # Custom React hooks
│   │   │   ├── 📄 useOrders.ts          # Order data management
│   │   │   ├── 📄 useSubcontractors.ts  # Subcontractor data
│   │   │   ├── 📄 useAuth.ts            # Authentication logic
│   │   │   ├── 📄 useRealtime.ts        # SSE real-time updates
│   │   │   ├── 📄 useLocalStorage.ts    # Local storage persistence
│   │   │   └── 📄 useDebounce.ts        # Input debouncing
│   │   │
│   │   ├── 📁 stores/                   # Zustand state stores
│   │   │   ├── 📄 orderStore.ts         # Order state management
│   │   │   ├── 📄 userStore.ts          # User/auth state
│   │   │   ├── 📄 uiStore.ts            # UI state (modals, loading)
│   │   │   └── 📄 settingsStore.ts      # Application settings
│   │   │
│   │   ├── 📁 services/                 # API service layer
│   │   │   ├── 📄 api.ts                # Main API client
│   │   │   ├── 📄 orderService.ts       # Order API calls
│   │   │   ├── 📄 subcontractorService.ts
│   │   │   ├── 📄 authService.ts        # Authentication API
│   │   │   ├── 📄 documentService.ts    # Document upload API
│   │   │   └── 📄 analyticsService.ts   # Analytics API
│   │   │
│   │   ├── 📁 types/                    # TypeScript type definitions
│   │   │   ├── 📄 api.ts                # API response types
│   │   │   ├── 📄 order.ts              # Order-related types
│   │   │   ├── 📄 user.ts               # User types
│   │   │   ├── 📄 common.ts             # Shared types
│   │   │   └── 📄 index.ts              # Type exports
│   │   │
│   │   ├── 📁 utils/                    # Utility functions
│   │   │   ├── 📄 formatters.ts         # Data formatting
│   │   │   ├── 📄 validators.ts         # Client-side validation
│   │   │   ├── 📄 constants.ts          # Application constants
│   │   │   ├── 📄 dateUtils.ts          # Date manipulation
│   │   │   └── 📄 mapUtils.ts           # Map-related utilities
│   │   │
│   │   └── 📁 lib/                      # External library configurations
│   │       ├── 📄 queryClient.ts        # TanStack Query setup
│   │       ├── 📄 axios.ts              # Axios configuration
│   │       └── 📄 mapbox.ts             # Mapbox configuration
│   │
│   ├── 📁 tests/                        # Frontend tests
│   │   ├── 📄 setup.ts                  # Test setup
│   │   ├── 📁 components/               # Component tests
│   │   │   ├── 📄 OrderCard.test.tsx
│   │   │   └── 📄 OrderForm.test.tsx
│   │   ├── 📁 pages/                    # Page tests
│   │   │   ├── 📄 Dashboard.test.tsx
│   │   │   └── 📄 Orders.test.tsx
│   │   ├── 📁 hooks/                    # Hook tests
│   │   │   └── 📄 useOrders.test.ts
│   │   └── 📁 e2e/                      # Playwright E2E tests
│   │       ├── 📄 order-workflow.spec.ts
│   │       └── 📄 auth.spec.ts
│   │
│   ├── 📄 package.json                  # Node.js dependencies
│   ├── 📄 package-lock.json
│   ├── 📄 tsconfig.json                # TypeScript configuration
│   ├── 📄 tsconfig.node.json          # Node-specific TS config
│   ├── 📄 vite.config.ts              # Vite build configuration
│   ├── 📄 tailwind.config.js          # Tailwind CSS config
│   ├── 📄 components.json             # shadcn/ui configuration
│   ├── 📄 vitest.config.ts            # Vitest test configuration
│   ├── 📄 playwright.config.ts        # Playwright E2E config
│   ├── 📄 Dockerfile                  # Production Docker image
│   ├── 📄 .env.example               # Environment variables
│   └── 📄 index.html                 # Main HTML template
│
├── 📁 infrastructure/                   # Infrastructure as Code
│   ├── 📁 docker/                      # Docker configurations
│   │   ├── 📄 docker-compose.yml       # Development environment
│   │   ├── 📄 docker-compose.prod.yml  # Production environment
│   │   └── 📄 docker-compose.test.yml  # Testing environment
│   │
│   ├── 📁 kubernetes/                  # Kubernetes manifests
│   │   ├── 📁 base/                    # Base configurations
│   │   │   ├── 📄 namespace.yaml
│   │   │   ├── 📄 backend-deployment.yaml
│   │   │   ├── 📄 frontend-deployment.yaml
│   │   │   ├── 📄 postgres-deployment.yaml
│   │   │   ├── 📄 redis-deployment.yaml
│   │   │   └── 📄 minio-deployment.yaml
│   │   ├── 📁 overlays/                # Environment-specific configs
│   │   │   ├── 📁 development/
│   │   │   ├── 📁 staging/
│   │   │   └── 📁 production/
│   │   └── 📄 kustomization.yaml
│   │
│   ├── 📁 terraform/                   # Infrastructure provisioning
│   │   ├── 📄 main.tf
│   │   ├── 📄 variables.tf
│   │   ├── 📄 outputs.tf
│   │   └── 📁 modules/
│   │       ├── 📁 database/
│   │       ├── 📁 storage/
│   │       └── 📁 networking/
│   │
│   └── 📁 monitoring/                  # Monitoring configurations
│       ├── 📄 prometheus.yml
│       ├── 📄 grafana-dashboard.json
│       ├── 📄 alertmanager.yml
│       └── 📁 dashboards/
│
├── 📁 scripts/                         # Development & deployment scripts
│   ├── 📄 setup.sh                    # Initial setup script
│   ├── 📄 dev.sh                      # Start development environment
│   ├── 📄 test.sh                     # Run all tests
│   ├── 📄 build.sh                    # Build production images
│   ├── 📄 deploy.sh                   # Deploy to production
│   ├── 📄 backup.sh                   # Database backup script
│   └── 📄 migrate.sh                  # Database migration script
│
├── 📁 docs/                           # Project documentation
│   ├── 📄 README.md                   # Project overview
│   ├── 📄 CONTRIBUTING.md             # Contribution guidelines
│   ├── 📄 DEPLOYMENT.md               # Deployment guide
│   ├── 📄 API.md                      # API documentation
│   ├── 📄 SECURITY.md                 # Security policies
│   ├── 📁 architecture/               # Architecture diagrams
│   ├── 📁 user-guides/               # User documentation
│   └── 📁 api-examples/              # API usage examples
│
├── 📁 tools/                          # Development tools & utilities
│   ├── 📄 load-test.py               # Load testing script
│   ├── 📄 data-migration.py          # Data migration utilities
│   ├── 📄 email-simulator.py         # Email testing tool
│   └── 📄 pdf-generator.py           # PDF testing utility
│
├── 📄 .gitignore                      # Git ignore patterns
├── 📄 .env.example                    # Environment variables template
├── 📄 docker-compose.yml              # Main docker compose file
├── 📄 Makefile                        # Development commands
├── 📄 README.md                       # Project documentation
├── 📄 CHANGELOG.md                    # Version history
├── 📄 LICENSE                         # Software license
└── 📄 pyproject.toml                  # Python project metadata
```

### **Key Structure Benefits**

#### 🎯 **Backend Architecture**
- **Clean Architecture**: Clear separation of concerns (API → Services → Repositories → Models)
- **Scalable**: Each service can be independently deployed and scaled
- **Testable**: Easy to mock dependencies and write comprehensive tests
- **Maintainable**: Code organization follows Python best practices

#### ⚛️ **Frontend Architecture**
- **Component-Driven**: Reusable UI components with shadcn/ui
- **Type Safety**: Full TypeScript coverage for robust development
- **Performance**: Optimized with Vite, code splitting, and lazy loading
- **State Management**: Zustand for simple, performant state handling

#### 🐳 **DevOps Ready**
- **Containerized**: Full Docker support for all environments
- **Kubernetes Ready**: Production-grade orchestration manifests
- **Infrastructure as Code**: Terraform for cloud resource management
- **Monitoring**: Built-in Prometheus metrics and Grafana dashboards

#### 🧪 **Testing Strategy**
- **Comprehensive Coverage**: Unit, integration, and E2E tests
- **Realistic Testing**: Fixtures with real PDF samples and data
- **Performance Testing**: Load testing with Locust
- **Security Testing**: Automated security scanning in CI/CD

### Environment Setup

#### Development Environment
```bash
# Clone repository
git clone <repository-url>
cd logistics-ai

# Setup Python environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Setup Node.js environment
cd frontend
npm install

# Setup Docker services
docker-compose up -d postgres redis minio

# Run database migrations
alembic upgrade head

# Start development servers
# Terminal 1: Backend
uvicorn app.main:app --reload --port 8000

# Terminal 2: Celery worker
celery -A app.tasks worker --loglevel=info

# Terminal 3: Frontend
cd frontend && npm run dev
```

#### Production Deployment
```yaml
# Kubernetes deployment example
apiVersion: apps/v1
kind: Deployment
metadata:
  name: logistics-ai-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: logistics-ai-backend
  template:
    metadata:
      labels:
        app: logistics-ai-backend
    spec:
      containers:
      - name: backend
        image: logistics-ai:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: database-url
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: openai-api-key
```

### API Documentation

#### Core Endpoints

```python
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from uuid import UUID

router = APIRouter(prefix="/api/v1", tags=["orders"])

# Orders API
@router.get("/orders", response_model=List[OrderResponse])
async def get_orders(
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    status_filter: Optional[OrderStatus] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None
) -> List[OrderResponse]:
    """List orders with pagination and filtering"""
    return await order_service.get_orders(
        skip=skip, limit=limit, status=status_filter, user=current_user
    )

@router.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)]
) -> OrderResponse:
    """Create a new order manually"""
    return await order_service.create_order(order_data, created_by=current_user)

@router.get("/orders/{order_id}", response_model=OrderDetailResponse)
async def get_order(
    order_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)]
) -> OrderDetailResponse:
    """Get detailed order information"""
    order = await order_service.get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@router.put("/orders/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: UUID,
    order_update: OrderUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)]
) -> OrderResponse:
    """Update an existing order"""
    return await order_service.update_order(order_id, order_update, updated_by=current_user)

@router.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_order(
    order_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)]
):
    """Cancel an order"""
    await order_service.cancel_order(order_id, cancelled_by=current_user)

# Subcontractors API
@router.get("/subcontractors", response_model=List[SubcontractorResponse])
async def get_subcontractors(
    skip: int = 0,
    limit: int = 50,
    active_only: bool = True,
    current_user: Annotated[User, Depends(get_current_user)] = None
) -> List[SubcontractorResponse]:
    """List subcontractors with filtering"""
    return await subcontractor_service.get_subcontractors(
        skip=skip, limit=limit, active_only=active_only
    )

@router.post("/subcontractors", response_model=SubcontractorResponse)
async def create_subcontractor(
    subcontractor_data: SubcontractorCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)]
) -> SubcontractorResponse:
    """Add new subcontractor"""
    return await subcontractor_service.create_subcontractor(subcontractor_data)

# Document Upload (Public - no authentication required)
public_router = APIRouter(prefix="/api/v1", tags=["documents"])

@public_router.post("/upload/{uit_code}")
async def upload_documents(
    uit_code: str,
    invoice_file: UploadFile = File(...),
    pod_file: UploadFile = File(...),
    additional_files: List[UploadFile] = File(None)
):
    """Upload documents using UIT code"""
    order = await order_service.get_order_by_uit_code(uit_code)
    if not order:
        raise HTTPException(status_code=404, detail="Invalid UIT code")
    
    result = await document_service.upload_documents(
        order_id=order.order_id,
        invoice_file=invoice_file,
        pod_file=pod_file,
        additional_files=additional_files or []
    )
    return {"message": "Documents uploaded successfully", "validation_id": result.validation_id}

@public_router.get("/track/{uit_code}")
async def track_order(uit_code: str):
    """Track order status using UIT code"""
    order = await order_service.get_order_by_uit_code(uit_code)
    if not order:
        raise HTTPException(status_code=404, detail="Invalid UIT code")
    
    return {
        "order_id": order.order_id,
        "status": order.order_status,
        "pickup_address": order.pickup_address,
        "delivery_address": order.delivery_address,
        "estimated_delivery": order.delivery_date_end,
        "last_updated": order.updated_at
    }

# Analytics API
analytics_router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

@analytics_router.get("/dashboard", response_model=DashboardMetrics)
async def get_dashboard_metrics(
    current_user: Annotated[User, Depends(get_current_user)]
) -> DashboardMetrics:
    """Get dashboard metrics"""
    return await analytics_service.get_dashboard_metrics()

@analytics_router.get("/reports")
async def generate_report(
    report_type: str = Query(..., description="Type of report to generate"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None
):
    """Generate analytical reports"""
    return await analytics_service.generate_report(
        report_type=report_type,
        start_date=start_date,
        end_date=end_date
    )

# Internal APIs (used by background services)
internal_router = APIRouter(prefix="/api/internal", tags=["internal"])

@internal_router.post("/orders/assign")
async def assign_subcontractor(
    assignment_data: SubcontractorAssignmentRequest,
    api_key: Annotated[str, Depends(verify_internal_api_key)]
):
    """Assign subcontractor to order (internal use)"""
    return await order_service.assign_subcontractor(assignment_data)

@internal_router.post("/orders/validate")
async def validate_documents(
    validation_request: DocumentValidationRequest,
    api_key: Annotated[str, Depends(verify_internal_api_key)]
):
    """Validate uploaded documents (internal use)"""
    return await validation_service.validate_documents(validation_request)
```

### Security Considerations

#### Authentication & Authorization
```python
# JWT-based authentication
class AuthService:
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        user = self.user_repository.get_by_username(username)
        if user and self.verify_password(password, user.hashed_password):
            return user
        return None
    
    def create_access_token(self, user: User) -> str:
        data = {"sub": user.id, "username": user.username, "roles": user.roles}
        return jwt.encode(data, self.secret_key, algorithm="HS256")

# Role-based access control
class RequireRole:
    def __init__(self, required_role: str):
        self.required_role = required_role
    
    def __call__(self, current_user: User = Depends(get_current_user)):
        if self.required_role not in current_user.roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
```

#### Data Protection
- **Encryption**: All sensitive data encrypted at rest (AES-256)
- **HTTPS**: TLS 1.3 for all communications
- **Input Validation**: Comprehensive validation for all inputs
- **SQL Injection Prevention**: Parameterized queries only
- **File Upload Security**: Virus scanning, type validation, size limits

#### GDPR Compliance
```python
class GDPRService:
    def anonymize_order_data(self, order_id: str):
        # Remove personal identifiers while keeping business data
        order = self.repository.get_order(order_id)
        order.client_contact_email = self._anonymize_email(order.client_contact_email)
        order.driver_contact = "ANONYMIZED"
        # Keep business data for accounting purposes
        
    def export_user_data(self, user_id: str) -> Dict:
        # Export all user-related data for GDPR requests
        return {
            'orders': self._get_user_orders(user_id),
            'audit_logs': self._get_user_audit_logs(user_id),
            'communications': self._get_user_communications(user_id)
        }
```

### Testing Strategy

#### Testing Examples

```python
# backend/tests/conftest.py - Test configuration and fixtures
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient

from app.main import app
from app.core.database import get_db, Base
from app.core.config import Settings, get_settings

# Test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://test:test@localhost/test_logistics"

# Create test engine and session
test_engine = create_async_engine(TEST_DATABASE_URL, echo=True)
TestAsyncSession = sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestAsyncSession() as session:
        yield session
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
def override_get_db(db_session: AsyncSession):
    """Override the get_db dependency."""
    async def _override_get_db():
        yield db_session
    return _override_get_db

@pytest.fixture
def test_settings() -> Settings:
    """Test configuration settings."""
    return Settings(
        database_url=TEST_DATABASE_URL,
        secret_key="test-secret-key",
        openai_api_key="test-openai-key",
        environment="testing"
    )

@pytest.fixture
async def async_client(
    override_get_db, test_settings
) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client."""
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = lambda: test_settings
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()

@pytest.fixture
def mock_order_data():
    """Sample order data for testing."""
    return {
        "client_company_name": "Test Logistics SRL",
        "client_vat_number": "RO12345678",
        "client_contact_email": "test@example.com",
        "client_offered_price": 1500.00,
        "pickup_address": "Str. Test 123, Bucuresti",
        "pickup_postcode": "010101",
        "pickup_city": "Bucuresti",
        "pickup_country": "RO",
        "delivery_address": "Str. Delivery 456, Cluj-Napoca",
        "delivery_postcode": "400001",
        "delivery_city": "Cluj-Napoca",
        "delivery_country": "RO",
        "cargo_ldm": 2.5,
        "cargo_weight_kg": 1000.0,
        "cargo_pallets": 4
    }

# backend/tests/unit/test_order_service.py - Unit tests
import pytest
from unittest.mock import Mock, AsyncMock
from uuid import uuid4

from app.services.order_service import OrderService
from app.models.orders import Order, OrderStatus
from app.schemas.orders import OrderCreateRequest, OrderResponse
from app.core.exceptions import ValidationError, NotFoundError

class TestOrderService:
    """Unit tests for OrderService."""
    
    @pytest.fixture
    def order_service(self):
        """Create OrderService with mocked dependencies."""
        mock_repo = Mock()
        mock_geocoding = Mock()
        mock_notification = Mock()
        
        return OrderService(
            repository=mock_repo,
            geocoding_service=mock_geocoding,
            notification_service=mock_notification
        )
    
    @pytest.fixture
    def valid_order_data(self, mock_order_data):
        """Valid order creation request."""
        return OrderCreateRequest(**mock_order_data)
    
    async def test_create_order_success(self, order_service, valid_order_data):
        """Test successful order creation."""
        # Arrange
        order_id = uuid4()
        order_service.repository.save = AsyncMock(return_value=Order(
            order_id=order_id,
            **valid_order_data.dict(),
            order_status=OrderStatus.PENDING
        ))
        order_service.geocoding_service.geocode = AsyncMock(return_value="POINT(0 0)")
        
        # Act
        result = await order_service.create_order(valid_order_data)
        
        # Assert
        assert result.order_id == order_id
        assert result.order_status == OrderStatus.PENDING
        assert result.client_company_name == valid_order_data.client_company_name
        order_service.repository.save.assert_called_once()
        order_service.geocoding_service.geocode.assert_called()
    
    async def test_create_order_missing_required_field(self, order_service):
        """Test validation of required fields."""
        # Arrange
        invalid_data = OrderCreateRequest(
            client_vat_number="RO12345678",
            # Missing client_company_name (required)
            client_offered_price=1000.00,
            pickup_address="Test Address",
            delivery_address="Test Delivery"
        )
        
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await order_service.create_order(invalid_data)
        
        assert "client_company_name" in str(exc_info.value)
    
    async def test_get_order_by_id_success(self, order_service):
        """Test successful order retrieval."""
        # Arrange
        order_id = uuid4()
        expected_order = Order(order_id=order_id, client_company_name="Test Company")
        order_service.repository.get_by_id = AsyncMock(return_value=expected_order)
        
        # Act
        result = await order_service.get_order_by_id(order_id)
        
        # Assert
        assert result == expected_order
        order_service.repository.get_by_id.assert_called_once_with(order_id)
    
    async def test_get_order_by_id_not_found(self, order_service):
        """Test order not found scenario."""
        # Arrange
        order_id = uuid4()
        order_service.repository.get_by_id = AsyncMock(return_value=None)
        
        # Act & Assert
        with pytest.raises(NotFoundError):
            await order_service.get_order_by_id(order_id)

# backend/tests/integration/test_api_orders.py - Integration tests
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orders import Order

class TestOrdersAPI:
    """Integration tests for Orders API endpoints."""
    
    async def test_create_order_api(
        self, async_client: AsyncClient, mock_order_data, db_session: AsyncSession
    ):
        """Test order creation via API."""
        # Act
        response = await async_client.post("/api/v1/orders", json=mock_order_data)
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["client_company_name"] == mock_order_data["client_company_name"]
        assert data["order_status"] == "pending"
        assert "order_id" in data
        
        # Verify database persistence
        order = await db_session.get(Order, data["order_id"])
        assert order is not None
        assert order.client_company_name == mock_order_data["client_company_name"]
    
    async def test_get_orders_list(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Test getting orders list with pagination."""
        # Arrange - Create test orders
        orders = [
            Order(client_company_name=f"Company {i}", client_offered_price=1000.0)
            for i in range(5)
        ]
        for order in orders:
            db_session.add(order)
        await db_session.commit()
        
        # Act
        response = await async_client.get("/api/v1/orders?limit=3")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert all("order_id" in order for order in data)
    
    async def test_get_order_details(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Test getting specific order details."""
        # Arrange
        order = Order(client_company_name="Test Company", client_offered_price=1500.0)
        db_session.add(order)
        await db_session.commit()
        await db_session.refresh(order)
        
        # Act
        response = await async_client.get(f"/api/v1/orders/{order.order_id}")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["order_id"] == str(order.order_id)
        assert data["client_company_name"] == "Test Company"
    
    async def test_get_order_not_found(self, async_client: AsyncClient):
        """Test getting non-existent order."""
        # Act
        fake_id = "550e8400-e29b-41d4-a716-446655440000"
        response = await async_client.get(f"/api/v1/orders/{fake_id}")
        
        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

# backend/tests/unit/test_ai_service.py - AI service tests
import pytest
from unittest.mock import Mock, patch, AsyncMock

from app.services.ai_service import AIDocumentParser
from app.schemas.ai import DocumentParsingResult

class TestAIDocumentParser:
    """Unit tests for AI document parsing service."""
    
    @pytest.fixture
    def ai_parser(self):
        """Create AI parser with mocked dependencies."""
        return AIDocumentParser(
            openai_client=Mock(),
            claude_client=Mock()
        )
    
    @patch('app.services.ai_service.extract_pdf_text')
    @patch('app.services.ai_service.extract_pdf_images')
    async def test_parse_document_success(
        self, mock_extract_images, mock_extract_text, ai_parser
    ):
        """Test successful document parsing."""
        # Arrange
        mock_extract_text.return_value = "Sample PDF text content"
        mock_extract_images.return_value = ["base64_image_data"]
        
        mock_openai_response = {
            "client_company_name": "Test Logistics SRL",
            "client_vat_number": "RO12345678",
            "client_offered_price": 1500.00,
            "pickup_address": "Bucuresti, Romania",
            "delivery_address": "Cluj-Napoca, Romania"
        }
        
        ai_parser.openai_client.parse_document = AsyncMock(
            return_value=mock_openai_response
        )
        
        # Act
        result = await ai_parser.parse_document("/path/to/test.pdf")
        
        # Assert
        assert isinstance(result, DocumentParsingResult)
        assert result.extracted_data["client_company_name"] == "Test Logistics SRL"
        assert result.confidence_scores["client_company_name"] >= 0.8
        mock_extract_text.assert_called_once()
        ai_parser.openai_client.parse_document.assert_called_once()
    
    async def test_parse_document_fallback_to_claude(self, ai_parser):
        """Test fallback to Claude when OpenAI fails."""
        # Arrange
        ai_parser.openai_client.parse_document = AsyncMock(
            side_effect=Exception("OpenAI API error")
        )
        ai_parser.claude_client.parse_document = AsyncMock(
            return_value={"client_company_name": "Test Company"}
        )
        
        # Act
        result = await ai_parser.parse_document("/path/to/test.pdf")
        
        # Assert
        assert result.extracted_data["client_company_name"] == "Test Company"
        ai_parser.claude_client.parse_document.assert_called_once()

# frontend/src/components/__tests__/OrderCard.test.tsx - Frontend tests
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import { OrderCard } from '../OrderCard';
import { Order, OrderStatus } from '@/types/order';

const mockOrder: Order = {
  order_id: '123e4567-e89b-12d3-a456-426614174000',
  client_company_name: 'Test Logistics SRL',
  client_offered_price: 1500.00,
  order_status: OrderStatus.PENDING,
  pickup_city: 'Bucuresti',
  pickup_postcode: '010101',
  delivery_city: 'Cluj-Napoca',
  delivery_postcode: '400001',
  pickup_date_start: '2024-01-15',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString()
};

describe('OrderCard', () => {
  const mockOnAssign = vi.fn();
  const mockOnViewDetails = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders order information correctly', () => {
    render(
      <OrderCard
        order={mockOrder}
        onAssignSubcontractor={mockOnAssign}
        onViewDetails={mockOnViewDetails}
      />
    );

    expect(screen.getByText(/Order #123e4567/)).toBeInTheDocument();
    expect(screen.getByText('PENDING')).toBeInTheDocument();
    expect(screen.getByText('€1,500')).toBeInTheDocument();
    expect(screen.getByText(/Bucuresti, 010101/)).toBeInTheDocument();
    expect(screen.getByText(/Cluj-Napoca, 400401/)).toBeInTheDocument();
  });

  it('shows assign button for pending orders', () => {
    render(
      <OrderCard
        order={mockOrder}
        onAssignSubcontractor={mockOnAssign}
        onViewDetails={mockOnViewDetails}
      />
    );

    const assignButton = screen.getByText('Assign Carrier');
    expect(assignButton).toBeInTheDocument();
    expect(assignButton).not.toBeDisabled();
  });

  it('hides assign button for non-pending orders', () => {
    const assignedOrder = { ...mockOrder, order_status: OrderStatus.ASSIGNED };
    
    render(
      <OrderCard
        order={assignedOrder}
        onAssignSubcontractor={mockOnAssign}
        onViewDetails={mockOnViewDetails}
      />
    );

    expect(screen.queryByText('Assign Carrier')).not.toBeInTheDocument();
  });

  it('calls onAssignSubcontractor when assign button is clicked', async () => {
    render(
      <OrderCard
        order={mockOrder}
        onAssignSubcontractor={mockOnAssign}
        onViewDetails={mockOnViewDetails}
      />
    );

    const assignButton = screen.getByText('Assign Carrier');
    fireEvent.click(assignButton);

    await waitFor(() => {
      expect(mockOnAssign).toHaveBeenCalledWith(mockOrder.order_id);
    });
  });

  it('calls onViewDetails when view details button is clicked', () => {
    render(
      <OrderCard
        order={mockOrder}
        onAssignSubcontractor={mockOnAssign}
        onViewDetails={mockOnViewDetails}
      />
    );

    const viewDetailsButton = screen.getByText('View Details');
    fireEvent.click(viewDetailsButton);

    expect(mockOnViewDetails).toHaveBeenCalledWith(mockOrder.order_id);
  });

  it('shows loading state during assignment', async () => {
    const slowAssign = vi.fn().mockImplementation(
      () => new Promise(resolve => setTimeout(resolve, 100))
    );

    render(
      <OrderCard
        order={mockOrder}
        onAssignSubcontractor={slowAssign}
        onViewDetails={mockOnViewDetails}
      />
    );

    const assignButton = screen.getByText('Assign Carrier');
    fireEvent.click(assignButton);

    expect(screen.getByText('Assigning...')).toBeInTheDocument();
    expect(assignButton).toBeDisabled();

    await waitFor(() => {
      expect(screen.getByText('Assign Carrier')).toBeInTheDocument();
    });
  });
});
```

#### Integration Tests
```python
class TestOrderWorkflow:
    async def test_complete_order_workflow(self):
        # Test end-to-end order workflow
        
        # 1. Create order from email
        email_data = self._load_test_email()
        order = await self.email_service.process_email(email_data)
        
        # 2. Assign subcontractor
        assignment = SubcontractorAssignment(
            subcontractor_id="test-subcontractor",
            agreed_price=Decimal("1500.00")
        )
        await self.order_service.assign_subcontractor(order.order_id, assignment)
        
        # 3. Upload documents
        documents = self._create_test_documents()
        await self.document_service.upload_documents(order.uit_code, documents)
        
        # 4. Validate documents
        validation_result = await self.validation_service.validate_order_documents(order.order_id)
        assert validation_result.is_valid
        
        # 5. Generate client invoice
        invoice = await self.invoice_service.generate_client_invoice(order.order_id)
        assert invoice.total == order.client_offered_price * 1.19  # Including VAT
```

### Performance & Scalability

#### Database Optimization
```sql
-- Critical indexes for performance
CREATE INDEX CONCURRENTLY idx_orders_status ON orders(order_status);
CREATE INDEX CONCURRENTLY idx_orders_created_at ON orders(created_at);
CREATE INDEX CONCURRENTLY idx_orders_client_vat ON orders(client_vat_number);
CREATE INDEX CONCURRENTLY idx_orders_pickup_postcode ON orders(pickup_postcode);
CREATE INDEX CONCURRENTLY idx_orders_delivery_postcode ON orders(delivery_postcode);

-- Spatial indexes for geographic queries
CREATE INDEX CONCURRENTLY idx_orders_pickup_location ON orders USING GIST(pickup_coordinates);
CREATE INDEX CONCURRENTLY idx_orders_delivery_location ON orders USING GIST(delivery_coordinates);

-- Partial indexes for active orders
CREATE INDEX CONCURRENTLY idx_active_orders ON orders(order_status, created_at) 
WHERE order_status NOT IN ('completed', 'cancelled');
```

#### Caching Strategy
```python
class CacheService:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.default_ttl = 3600  # 1 hour
    
    async def get_order(self, order_id: str) -> Optional[Order]:
        cache_key = f"order:{order_id}"
        cached_data = await self.redis.get(cache_key)
        
        if cached_data:
            return Order.parse_raw(cached_data)
        
        # Cache miss - fetch from database and cache
        order = await self.order_repository.get(order_id)
        if order:
            await self.redis.setex(cache_key, self.default_ttl, order.json())
        
        return order
    
    async def invalidate_order(self, order_id: str):
        await self.redis.delete(f"order:{order_id}")
```

#### Background Job Processing
```python
# Celery task definitions
@celery_app.task(bind=True, max_retries=3)
def process_email_attachment(self, email_id: str, attachment_path: str):
    try:
        # AI document processing (can take 30-60 seconds)
        result = ai_parser.parse_document(attachment_path)
        
        # Create order in database
        order = order_service.create_order(result)
        
        # Notify dispatcher
        notification_service.notify_new_order(order)
        
        return {"order_id": order.order_id, "status": "success"}
    
    except Exception as exc:
        # Retry with exponential backoff
        self.retry(countdown=60 * (self.request.retries + 1), exc=exc)

@celery_app.task
def send_payment_reminders():
    overdue_payments = payment_tracker.get_overdue_payments()
    for payment in overdue_payments:
        notification_service.send_payment_reminder(payment)

# Schedule periodic tasks
celery_app.conf.beat_schedule = {
    'check-payments': {
        'task': 'app.tasks.send_payment_reminders',
        'schedule': crontab(hour=9, minute=0),  # Daily at 9 AM
    },
    'process-emails': {
        'task': 'app.tasks.scan_emails',
        'schedule': 30.0,  # Every 30 seconds
    },
}
```

### Monitoring & Observability

#### Application Metrics
```python
from prometheus_client import Counter, Histogram, Gauge

# Custom metrics
orders_created_total = Counter('orders_created_total', 'Total orders created')
order_processing_duration = Histogram('order_processing_seconds', 'Order processing time')
active_orders_gauge = Gauge('active_orders', 'Number of active orders')

class MetricsMiddleware:
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            start_time = time.time()
            
            # Process request
            await self.app(scope, receive, send)
            
            # Record metrics
            duration = time.time() - start_time
            order_processing_duration.observe(duration)
        else:
            await self.app(scope, receive, send)
```

#### Health Checks
```python
@router.get("/health")
async def health_check():
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {}
    }
    
    # Check database
    try:
        await database.execute("SELECT 1")
        health_status["services"]["database"] = "healthy"
    except Exception:
        health_status["services"]["database"] = "unhealthy"
        health_status["status"] = "degraded"
    
    # Check Redis
    try:
        await redis.ping()
        health_status["services"]["redis"] = "healthy"
    except Exception:
        health_status["services"]["redis"] = "unhealthy"
        health_status["status"] = "degraded"
    
    # Check email connectivity
    try:
        await email_service.check_connection()
        health_status["services"]["email"] = "healthy"
    except Exception:
        health_status["services"]["email"] = "unhealthy"
        health_status["status"] = "degraded"
    
    status_code = 200 if health_status["status"] == "healthy" else 503
    return JSONResponse(content=health_status, status_code=status_code)
```

### Deployment & DevOps

#### Docker Configuration

```dockerfile
# backend/Dockerfile - Production FastAPI image
FROM python:3.11-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=app:app . .

USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```dockerfile
# frontend/Dockerfile - Production React image
FROM node:18-alpine AS build

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci --only=production

# Copy source code and build
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built assets
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

```yaml
# docker-compose.yml - Development environment
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://logistics:password@postgres:5432/logistics_db
      - REDIS_URL=redis://redis:6379
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - ./backend:/app
      - /app/venv
    depends_on:
      - postgres
      - redis
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports:
      - "3000:3000"
    environment:
      - VITE_API_BASE_URL=http://localhost:8000
    volumes:
      - ./frontend:/app
      - /app/node_modules
    command: npm run dev

  postgres:
    image: postgis/postgis:15-3.3
    environment:
      - POSTGRES_DB=logistics_db
      - POSTGRES_USER=logistics
      - POSTGRES_PASSWORD=password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backend/migrations/init.sql:/docker-entrypoint-initdb.d/init.sql

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

  minio:
    image: minio/minio:latest
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=minioadmin123
    volumes:
      - minio_data:/data
    command: server /data --console-address ":9001"

  celery-worker:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    environment:
      - DATABASE_URL=postgresql://logistics:password@postgres:5432/logistics_db
      - REDIS_URL=redis://redis:6379
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./backend:/app
    depends_on:
      - postgres
      - redis
    command: celery -A app.tasks worker --loglevel=info

  celery-beat:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    environment:
      - DATABASE_URL=postgresql://logistics:password@postgres:5432/logistics_db
      - REDIS_URL=redis://redis:6379
    volumes:
      - ./backend:/app
    depends_on:
      - postgres
      - redis
    command: celery -A app.tasks beat --loglevel=info

volumes:
  postgres_data:
  redis_data:
  minio_data:
```

```yaml
# docker-compose.prod.yml - Production environment
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - SECRET_KEY=${SECRET_KEY}
      - ENVIRONMENT=production
    restart: unless-stopped
    depends_on:
      - postgres
      - redis

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "80:80"
      - "443:443"
    restart: unless-stopped
    depends_on:
      - backend

  postgres:
    image: postgis/postgis:15-3.3
    environment:
      - POSTGRES_DB=${DB_NAME}
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    restart: unless-stopped

  celery-worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    restart: unless-stopped
    depends_on:
      - postgres
      - redis
    command: celery -A app.tasks worker --loglevel=info

volumes:
  postgres_data:
  redis_data:
```

```nginx
# frontend/nginx.conf - Production nginx configuration
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    sendfile        on;
    keepalive_timeout  65;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;

    server {
        listen 80;
        server_name localhost;
        root /usr/share/nginx/html;
        index index.html;

        # Security headers
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";

        # Handle React routing
        location / {
            try_files $uri $uri/ /index.html;
        }

        # API proxy
        location /api/ {
            proxy_pass http://backend:8000/api/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Static assets caching
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
}
```

#### CI/CD Pipeline

```yaml
# .github/workflows/ci-cd.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  test-backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgis/postgis:15-3.3
        env:
          POSTGRES_PASSWORD: test_password
          POSTGRES_USER: test_user
          POSTGRES_DB: test_logistics
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
        cache: 'pip'
    
    - name: Install dependencies
      working-directory: ./backend
      run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run linting
      working-directory: ./backend
      run: |
        flake8 app/ --count --select=E9,F63,F7,F82 --show-source --statistics
        black --check app/
        isort --check-only app/
        mypy app/
    
    - name: Run tests
      working-directory: ./backend
      env:
        DATABASE_URL: postgresql://test_user:test_password@localhost:5432/test_logistics
        REDIS_URL: redis://localhost:6379
        SECRET_KEY: test-secret-key-for-ci
        OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
      run: |
        pytest tests/ -v --cov=app --cov-report=xml --cov-report=html
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./backend/coverage.xml
        flags: backend

  test-frontend:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Node.js
      uses: actions/setup-node@v4
      with:
        node-version: '18'
        cache: 'npm'
        cache-dependency-path: frontend/package-lock.json
    
    - name: Install dependencies
      working-directory: ./frontend
      run: npm ci
    
    - name: Run linting
      working-directory: ./frontend
      run: |
        npm run lint
        npm run type-check
    
    - name: Run tests
      working-directory: ./frontend
      run: npm test -- --coverage
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./frontend/coverage/coverage-final.json
        flags: frontend

  security-scan:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        scan-ref: '.'
        format: 'sarif'
        output: 'trivy-results.sarif'
    
    - name: Upload Trivy scan results to GitHub Security tab
      uses: github/codeql-action/upload-sarif@v2
      with:
        sarif_file: 'trivy-results.sarif'

  build-and-push:
    needs: [test-backend, test-frontend, security-scan]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' || github.ref == 'refs/heads/develop'
    
    permissions:
      contents: read
      packages: write

    strategy:
      matrix:
        service: [backend, frontend]

    steps:
    - uses: actions/checkout@v4
    
    - name: Log in to Container Registry
      uses: docker/login-action@v3
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    
    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v5
      with:
        images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-${{ matrix.service }}
        tags: |
          type=ref,event=branch
          type=ref,event=pr
          type=sha
    
    - name: Build and push Docker image
      uses: docker/build-push-action@v5
      with:
        context: ./${{ matrix.service }}
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}

  deploy-staging:
    needs: build-and-push
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/develop'
    environment: staging
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Deploy to staging
      run: |
        echo "Deploying to staging environment"
        # Add your staging deployment commands here
        # kubectl apply -f k8s/staging/
        # helm upgrade --install logistics-ai-staging ./helm-chart

  deploy-production:
    needs: build-and-push
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Deploy to production
      run: |
        echo "Deploying to production environment"
        # Add your production deployment commands here
        # kubectl apply -f k8s/production/
        # helm upgrade --install logistics-ai ./helm-chart

  lighthouse-ci:
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
    - uses: actions/checkout@v4
    
    - name: Run Lighthouse CI
      uses: treosh/lighthouse-ci-action@v10
      with:
        configPath: './.lighthouserc.json'
        uploadArtifacts: true
        temporaryPublicStorage: true
```

#### Environment Variables & Configuration

```bash
# .env.example - Template for environment variables
# Copy this file to .env and fill in your values

# === APPLICATION SETTINGS ===
ENVIRONMENT=development
SECRET_KEY=your-super-secret-key-change-this-in-production
DEBUG=true
API_BASE_URL=http://localhost:8000

# === DATABASE CONFIGURATION ===
DATABASE_URL=postgresql://logistics:password@localhost:5432/logistics_db
DB_HOST=localhost
DB_PORT=5432
DB_NAME=logistics_db
DB_USER=logistics
DB_PASSWORD=password

# === REDIS CONFIGURATION ===
REDIS_URL=redis://localhost:6379
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# === AI SERVICES ===
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_KEY=your-azure-openai-key
AZURE_OPENAI_VERSION=2023-12-01-preview

# === FILE STORAGE ===
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_BUCKET_NAME=logistics-documents
MINIO_SECURE=false

# === EMAIL CONFIGURATION ===
EMAIL_PROVIDER=gmail
EMAIL_HOST=imap.gmail.com
EMAIL_PORT=993
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
EMAIL_USE_SSL=true

# === AUTHENTICATION ===
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
JWT_ALGORITHM=HS256

# === EXTERNAL SERVICES ===
MAILGUN_API_KEY=your-mailgun-api-key
MAILGUN_DOMAIN=your-domain.com
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
TWILIO_PHONE_NUMBER=+1234567890

# === MONITORING & LOGGING ===
SENTRY_DSN=your-sentry-dsn
LOG_LEVEL=INFO
PROMETHEUS_ENABLED=true

# === GEOCODING ===
GOOGLE_MAPS_API_KEY=your-google-maps-api-key
MAPBOX_ACCESS_TOKEN=your-mapbox-token

# === ROMANIAN SERVICES ===
ANAF_API_BASE_URL=https://webservicesp.anaf.ro
EFACTURA_ENDPOINT=https://api.anaf.ro/prod/FCTEL/rest
EFACTURA_TOKEN=your-efactura-token

# === DEVELOPMENT TOOLS ===
VITE_API_BASE_URL=http://localhost:8000
VITE_MAPBOX_TOKEN=your-mapbox-token
VITE_SENTRY_DSN=your-frontend-sentry-dsn
```

```yaml
# .env.production - Production environment template
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=${SECRET_KEY}
API_BASE_URL=https://your-domain.com

# Database (use managed service in production)
DATABASE_URL=${DATABASE_URL}

# Redis (use managed service in production)
REDIS_URL=${REDIS_URL}

# AI Services
OPENAI_API_KEY=${OPENAI_API_KEY}
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}

# File Storage (use S3 or managed MinIO)
MINIO_ENDPOINT=${S3_ENDPOINT}
MINIO_ACCESS_KEY=${S3_ACCESS_KEY}
MINIO_SECRET_KEY=${S3_SECRET_KEY}
MINIO_BUCKET_NAME=logistics-prod-documents
MINIO_SECURE=true

# Email Production Settings
EMAIL_HOST=${EMAIL_HOST}
EMAIL_USERNAME=${EMAIL_USERNAME}
EMAIL_PASSWORD=${EMAIL_PASSWORD}

# Monitoring
SENTRY_DSN=${SENTRY_DSN}
LOG_LEVEL=WARNING

# External Services
MAILGUN_API_KEY=${MAILGUN_API_KEY}
MAILGUN_DOMAIN=${MAILGUN_DOMAIN}
GOOGLE_MAPS_API_KEY=${GOOGLE_MAPS_API_KEY}
```

---

## 🎯 Implementation Roadmap

### Phase 1: MVP (8-10 weeks)
**Core Features:**
- [ ] Email monitoring and PDF parsing (AI-powered)
- [ ] Basic order management (CRUD operations)
- [ ] Manual subcontractor assignment
- [ ] Simple document upload portal
- [ ] Basic invoice generation
- [ ] PostgreSQL database with core schema

**Deliverables:**
- Working backend API
- Basic React frontend
- Docker deployment setup
- Core workflow automation

### Phase 2: Enhanced Automation (6-8 weeks)
**Advanced Features:**
- [ ] EFACTURA validation engine
- [ ] Automated payment tracking
- [ ] Email notification system
- [ ] Analytics dashboard
- [ ] Subcontractor recommendation engine
- [ ] Advanced PDF generation with templates

**Deliverables:**
- Full workflow automation
- Production-ready deployment
- Monitoring and logging
- Performance optimization

### Phase 3: Enterprise Features (4-6 weeks)
**Enterprise Additions:**
- [ ] Multi-tenant support
- [ ] Advanced reporting and analytics
- [ ] API integrations (banking, ERP systems)
- [ ] Mobile app for subcontractors
- [ ] Advanced security features
- [ ] Audit trail and compliance tools

**Deliverables:**
- Scalable multi-tenant platform
- Mobile applications
- Enterprise integrations
- Compliance certification

---

## 📊 Success Metrics & KPIs

### Operational Metrics
- **Order Processing Time**: Target < 5 minutes from email to system
- **Automation Rate**: Target > 90% of orders processed automatically
- **Document Validation Accuracy**: Target > 95%
- **System Uptime**: Target > 99.5%

### Business Metrics
- **Cost Reduction**: Target 80% reduction in administrative overhead
- **Profit Margin Improvement**: Target 15% increase through better visibility
- **Payment Collection Time**: Target 20% reduction in collection period
- **Customer Satisfaction**: Target > 90% (internal users)

### Technical Metrics
- **API Response Time**: Target < 200ms for 95th percentile
- **Database Query Performance**: All queries < 100ms
- **Error Rate**: Target < 0.1% of requests
- **Test Coverage**: Target > 90%

---

## 🔒 Compliance & Security

### Data Protection
- **GDPR Compliance**: Full data protection and privacy controls
- **Data Encryption**: AES-256 encryption for sensitive data
- **Access Control**: Role-based permissions and audit logging
- **Backup Strategy**: Automated daily backups with 30-day retention

### Romanian Legal Requirements
- **EFACTURA Compliance**: Full support for Romanian electronic invoicing
- **VAT Handling**: Automated VAT calculation and reporting
- **Document Retention**: 7-year document archival as required by law
- **Financial Reporting**: Integration with Romanian accounting standards

### Security Measures
- **Authentication**: Multi-factor authentication for admin users
- **Authorization**: Granular permission system
- **Input Validation**: Comprehensive validation and sanitization
- **Regular Security Audits**: Quarterly penetration testing
- **Incident Response**: 24/7 monitoring and response procedures

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+ with pip
- Node.js 18+ with npm
- PostgreSQL 15+
- Redis 6+
- Docker & Docker Compose
- OpenAI API key or Azure OpenAI access

### Quick Start

```bash
# 1. Clone the repository
git clone <repository-url>
cd logistics-ai

# 2. Setup environment variables
cp .env.example .env
# Edit .env with your configuration (especially OPENAI_API_KEY)

# 3. Start services with Docker
docker-compose up -d

# 4. Install dependencies and run migrations
make setup

# 5. Start development servers
make dev

# 6. Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
# MinIO Console: http://localhost:9001 (minioadmin/minioadmin123)
```

### Automated Setup Script

```bash
#!/bin/bash
# scripts/setup.sh - Automated project setup

set -e

echo "🚚 Setting up Romanian Freight Forwarder Automation System..."

# Check if required tools are installed
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo "❌ $1 is not installed. Please install it first."
        exit 1
    fi
}

echo "Checking prerequisites..."
check_command docker
check_command docker-compose
check_command node
check_command python3
check_command make

# Setup environment variables
if [ ! -f .env ]; then
    echo "Setting up environment variables..."
    cp .env.example .env
    echo "✅ Created .env file from template"
    echo "⚠️  Please edit .env file with your API keys and configuration"
else
    echo "✅ .env file already exists"
fi

# Create required directories
echo "Creating required directories..."
mkdir -p backend/logs
mkdir -p backend/uploads
mkdir -p backend/static
mkdir -p frontend/public/uploads
echo "✅ Created directory structure"

# Setup Python virtual environment
if [ ! -d "backend/venv" ]; then
    echo "Setting up Python virtual environment..."
    cd backend
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install -r requirements-dev.txt
    cd ..
    echo "✅ Python environment setup complete"
else
    echo "✅ Python virtual environment already exists"
fi

# Setup Node.js dependencies
if [ ! -d "frontend/node_modules" ]; then
    echo "Installing Node.js dependencies..."
    cd frontend
    npm install
    cd ..
    echo "✅ Node.js dependencies installed"
else
    echo "✅ Node.js dependencies already installed"
fi

# Start Docker services
echo "Starting Docker services..."
docker-compose up -d postgres redis minio
echo "⏳ Waiting for services to be ready..."
sleep 10

# Run database migrations
echo "Running database migrations..."
cd backend
source venv/bin/activate
alembic upgrade head
cd ..
echo "✅ Database migrations complete"

# Create MinIO buckets
echo "Setting up MinIO buckets..."
docker-compose exec -T minio mc alias set local http://localhost:9000 minioadmin minioadmin123
docker-compose exec -T minio mc mb local/logistics-documents --ignore-existing
docker-compose exec -T minio mc policy set public local/logistics-documents
echo "✅ MinIO buckets created"

# Run initial tests
echo "Running initial tests..."
cd backend
source venv/bin/activate
pytest tests/unit/test_health.py -v
cd ../frontend
npm run test:unit -- --run
cd ..
echo "✅ Initial tests passed"

echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your API keys (especially OPENAI_API_KEY)"
echo "2. Run 'make dev' to start development servers"
echo "3. Visit http://localhost:3000 to see the application"
echo "4. Visit http://localhost:8000/docs to see the API documentation"
echo ""
echo "Useful commands:"
echo "  make dev          - Start development servers"
echo "  make test         - Run all tests"
echo "  make lint         - Run code linting"
echo "  make clean        - Clean up containers and volumes"
```

### Development Commands

```makefile
# Makefile - Development automation

.PHONY: help setup dev test lint clean build deploy

help: ## Show this help message
	@echo "Romanian Freight Forwarder Automation System"
	@echo "Available commands:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Initial project setup
	@./scripts/setup.sh

dev: ## Start development servers
	@echo "Starting development environment..."
	@docker-compose up -d postgres redis minio
	@echo "Starting backend server..."
	@cd backend && source venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
	@echo "Starting frontend server..."
	@cd frontend && npm run dev &
	@echo "Starting Celery worker..."
	@cd backend && source venv/bin/activate && celery -A app.tasks worker --loglevel=info &
	@echo "✅ All services started!"
	@echo "Frontend: http://localhost:3000"
	@echo "Backend: http://localhost:8000"
	@echo "API Docs: http://localhost:8000/docs"

stop: ## Stop all development servers
	@echo "Stopping all services..."
	@pkill -f "uvicorn app.main:app" || true
	@pkill -f "npm run dev" || true
	@pkill -f "celery -A app.tasks worker" || true
	@docker-compose stop
	@echo "✅ All services stopped!"

test: ## Run all tests
	@echo "Running backend tests..."
	@cd backend && source venv/bin/activate && pytest tests/ -v --cov=app
	@echo "Running frontend tests..."
	@cd frontend && npm run test:unit -- --run && npm run test:e2e

test-backend: ## Run backend tests only
	@cd backend && source venv/bin/activate && pytest tests/ -v --cov=app

test-frontend: ## Run frontend tests only
	@cd frontend && npm run test:unit -- --run

lint: ## Run code linting
	@echo "Linting backend code..."
	@cd backend && source venv/bin/activate && black app/ && isort app/ && flake8 app/ && mypy app/
	@echo "Linting frontend code..."
	@cd frontend && npm run lint && npm run type-check

format: ## Format code
	@echo "Formatting backend code..."
	@cd backend && source venv/bin/activate && black app/ && isort app/
	@echo "Formatting frontend code..."
	@cd frontend && npm run format

migration: ## Create new database migration
	@read -p "Enter migration name: " name; \
	cd backend && source venv/bin/activate && alembic revision --autogenerate -m "$$name"

migrate: ## Run database migrations
	@cd backend && source venv/bin/activate && alembic upgrade head

build: ## Build production images
	@echo "Building production images..."
	@docker-compose -f docker-compose.prod.yml build

deploy-staging: ## Deploy to staging
	@echo "Deploying to staging..."
	@docker-compose -f docker-compose.prod.yml up -d
	@echo "✅ Deployed to staging!"

deploy-production: ## Deploy to production
	@echo "Deploying to production..."
	@kubectl apply -f infrastructure/kubernetes/production/
	@echo "✅ Deployed to production!"

clean: ## Clean up containers and volumes
	@echo "Cleaning up..."
	@docker-compose down -v
	@docker system prune -f
	@echo "✅ Cleanup complete!"

logs: ## Show logs from all services
	@docker-compose logs -f

logs-backend: ## Show backend logs
	@docker-compose logs -f backend

logs-db: ## Show database logs
	@docker-compose logs -f postgres

shell-backend: ## Open backend shell
	@cd backend && source venv/bin/activate && python

shell-db: ## Open database shell
	@docker-compose exec postgres psql -U logistics logistics_db

backup-db: ## Backup database
	@docker-compose exec postgres pg_dump -U logistics logistics_db > backup_$(date +%Y%m%d_%H%M%S).sql
	@echo "✅ Database backup created!"

restore-db: ## Restore database from backup
	@read -p "Enter backup file path: " file; \
	docker-compose exec -T postgres psql -U logistics logistics_db < $$file

monitor: ## Open monitoring dashboard
	@echo "Opening monitoring services..."
	@open http://localhost:9090  # Prometheus
	@open http://localhost:3000  # Grafana
	@open http://localhost:9001  # MinIO Console
```

### Development Commands
```bash
# Run tests
make test

# Run linting
make lint

# Format code
make format

# Generate migration
make migration name="description"

# Deploy to staging
make deploy-staging

# Deploy to production
make deploy-production
```

---

## 📞 Support & Maintenance

### Documentation
- **API Documentation**: Auto-generated with OpenAPI/Swagger
- **User Manual**: Step-by-step operational guide
- **Developer Guide**: Technical implementation details
- **Troubleshooting**: Common issues and solutions

### Support Channels
- **Technical Support**: 24/7 monitoring with 4-hour response SLA
- **User Training**: Comprehensive onboarding and training programs
- **Feature Requests**: Quarterly roadmap reviews and feature prioritization
- **Bug Reports**: Issue tracking with severity-based response times

### Maintenance Schedule
- **Daily**: Automated backups and health checks
- **Weekly**: Performance monitoring and optimization
- **Monthly**: Security updates and dependency maintenance
- **Quarterly**: Feature releases and system upgrades

---

*This specification provides a comprehensive foundation for building a world-class freight forwarding automation system. The modular architecture, extensive testing strategy, and focus on security and compliance ensure the system will be reliable, scalable, and maintainable for years to come.*

