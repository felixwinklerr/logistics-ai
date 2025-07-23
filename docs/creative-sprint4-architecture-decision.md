# Sprint 4 Frontend Architecture Decision

## 🏗️ ARCHITECTURE DESIGN DECISION

### Selected: Hybrid Domain-Layer Architecture

**Rationale**: Provides optimal balance of domain separation, code reusability, and scalability for the Romanian Freight Forwarder system.

## 📁 DETAILED FOLDER STRUCTURE

```
frontend/src/
├── app/                          # Application configuration
│   ├── layout.tsx               # Root layout component
│   ├── providers.tsx            # Context providers (Query, Auth)
│   └── router.tsx               # Route configuration
│
├── features/                     # Domain-specific features
│   ├── orders/
│   │   ├── components/
│   │   │   ├── OrderCard.tsx           # ✅ Matches UI/UX decision
│   │   │   ├── OrderList.tsx           # Card grid layout
│   │   │   ├── OrderDetails.tsx        # Detailed view
│   │   │   ├── OrderForm.tsx           # Multi-step creation
│   │   │   └── SubcontractorAssignmentModal.tsx
│   │   ├── hooks/
│   │   │   ├── useOrders.ts            # TanStack Query integration
│   │   │   ├── useOrderActions.ts      # CRUD operations
│   │   │   └── useOrderRealtime.ts     # SSE integration
│   │   ├── services/
│   │   │   └── orderApi.ts             # API client methods
│   │   └── types/
│   │       └── order.ts                # Order-specific types
│   │
│   ├── subcontractors/
│   │   ├── components/
│   │   ├── hooks/
│   │   └── services/
│   │
│   └── dashboard/
│       ├── components/
│       └── hooks/
│
├── shared/                       # Shared across features
│   ├── components/
│   │   ├── ui/                         # shadcn/ui components
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── badge.tsx              # Status badges
│   │   │   └── dialog.tsx
│   │   ├── layout/
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── PageLayout.tsx
│   │   └── common/
│   │       ├── LoadingSpinner.tsx
│   │       ├── ErrorBoundary.tsx
│   │       └── StatusBadge.tsx        # Reusable status display
│   │
│   ├── hooks/
│   │   ├── useAuth.ts                  # Authentication state
│   │   ├── useLocalStorage.ts
│   │   └── useDebounce.ts
│   │
│   ├── services/
│   │   ├── api.ts                      # Base API configuration
│   │   ├── auth.ts                     # Authentication service
│   │   └── realtime.ts                 # SSE service
│   │
│   ├── stores/
│   │   ├── authStore.ts                # Zustand auth store
│   │   ├── uiStore.ts                  # UI state (modals, loading)
│   │   └── settingsStore.ts            # User preferences
│   │
│   └── utils/
│       ├── formatters.ts               # Data formatting
│       ├── validators.ts               # Form validation
│       └── constants.ts                # App constants
│
├── lib/                          # Third-party configurations
│   ├── queryClient.ts                  # TanStack Query setup
│   ├── axios.ts                        # HTTP client config
│   └── validations.ts                  # Zod schemas
│
├── types/                        # Global type definitions
│   ├── api.ts                          # API response types
│   ├── common.ts                       # Shared types
│   └── index.ts                        # Type exports
│
├── styles/                       # Global styles
│   └── globals.css                     # Tailwind imports + custom CSS
│
├── main.tsx                      # React app entry point
└── App.tsx                       # Root app component
```

## 🔄 STATE MANAGEMENT ARCHITECTURE

### Zustand Store Organization

```typescript
// shared/stores/authStore.ts
interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => void;
}

// shared/stores/uiStore.ts  
interface UIState {
  isLoading: boolean;
  activeModal: string | null;
  sidebarOpen: boolean;
  setLoading: (loading: boolean) => void;
  openModal: (modalId: string) => void;
  closeModal: () => void;
}

// features/orders/hooks/useOrders.ts (TanStack Query)
const useOrders = (filters?: OrderFilters) => {
  return useQuery({
    queryKey: ['orders', filters],
    queryFn: () => orderApi.getOrders(filters),
    staleTime: 30000, // 30 seconds
  });
};
```

## 📡 REAL-TIME DATA FLOW

### Server-Sent Events Integration

```typescript
// shared/services/realtime.ts
class RealtimeService {
  private eventSource: EventSource | null = null;
  
  connect() {
    this.eventSource = new EventSource('/api/events');
    this.eventSource.onmessage = this.handleOrderUpdate;
  }
  
  private handleOrderUpdate = (event: MessageEvent) => {
    const update = JSON.parse(event.data);
    queryClient.setQueryData(['orders'], (old) => 
      updateOrderInList(old, update)
    );
  };
}

// features/orders/hooks/useOrderRealtime.ts  
const useOrderRealtime = () => {
  useEffect(() => {
    const realtime = new RealtimeService();
    realtime.connect();
    return () => realtime.disconnect();
  }, []);
};
```

## 🎨 COMPONENT INTEGRATION WITH UI/UX DECISION

### OrderCard Implementation (Matches UI/UX Decision)

```typescript
// features/orders/components/OrderCard.tsx
import { Card } from '@/shared/components/ui/card';
import { Badge } from '@/shared/components/ui/badge';
import { Button } from '@/shared/components/ui/button';

export const OrderCard: React.FC<OrderCardProps> = ({ order, onAssign, onViewDetails }) => {
  const statusColor = getOrderStatusColor(order.status); // From style guide
  
  return (
    <Card className="bg-white rounded-lg border border-slate-200 p-6 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">
            Order #{order.id.slice(0, 8)}
          </h3>
          <Badge className={statusColor}>
            {order.status.replace('_', ' ').toUpperCase()}
          </Badge>
        </div>
        <div className="text-right">
          <p className="text-sm text-slate-500">Client Price</p>
          <p className="text-lg font-bold text-emerald-600">
            €{order.clientPrice.toLocaleString()}
          </p>
        </div>
      </div>
      
      {/* Route Information - Style Guide Typography */}
      <div className="space-y-2 mb-4">
        <div className="flex items-center text-sm text-slate-600">
          <MapPin className="w-4 h-4 mr-2 text-slate-400" />
          <span className="font-medium">From:</span>
          <span className="ml-1">{order.pickupCity}</span>
        </div>
        <div className="flex items-center text-sm text-slate-600">
          <MapPin className="w-4 h-4 mr-2 text-slate-400" />
          <span className="font-medium">To:</span>
          <span className="ml-1">{order.deliveryCity}</span>
        </div>
      </div>
      
      {/* Actions - Style Guide Button Patterns */}
      <div className="flex gap-2 pt-4 border-t border-slate-100">
        <Button
          variant="outline"
          size="sm"
          onClick={() => onViewDetails(order.id)}
          className="flex-1"
        >
          View Details
        </Button>
        {order.status === 'pending' && (
          <Button
            onClick={() => onAssign(order.id)}
            size="sm"
            className="flex-1 bg-blue-600 hover:bg-blue-700"
          >
            Assign Carrier
          </Button>
        )}
      </div>
    </Card>
  );
};
```

## ✅ ARCHITECTURE VALIDATION

### Requirements Alignment
- ✅ **Card-focused UI**: Component structure supports card layout decision
- ✅ **Real-time updates**: SSE integration with TanStack Query invalidation  
- ✅ **State management**: Zustand for UI state, TanStack Query for server state
- ✅ **Scalability**: Feature-based organization supports team growth
- ✅ **Style guide integration**: Direct mapping to defined component patterns
- ✅ **Form handling**: React Hook Form + Zod integration planned
- ✅ **Accessibility**: Semantic HTML and proper ARIA in component structure

### Development Benefits
- **Type Safety**: Full TypeScript coverage with shared type definitions
- **Code Reusability**: Shared components and hooks across features
- **Testing Strategy**: Isolated feature testing with shared utilities
- **Performance**: Optimized with React.memo, useMemo, and efficient queries
- **Developer Experience**: Clear mental model and predictable file locations

