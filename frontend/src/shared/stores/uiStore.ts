import { create } from 'zustand'

interface UIState {
  // Loading states
  isLoading: boolean
  loadingMessage: string
  
  // Modal states
  activeModal: string | null
  modalData: any
  
  // Sidebar state
  sidebarOpen: boolean
  
  // Notifications
  notifications: Array<{
    id: string
    type: 'info' | 'success' | 'warning' | 'error'
    title: string
    message?: string
    duration?: number
  }>
  
  // Actions
  setLoading: (loading: boolean, message?: string) => void
  openModal: (modalId: string, data?: any) => void
  closeModal: () => void
  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void
  addNotification: (notification: Omit<UIState['notifications'][0], 'id'>) => void
  removeNotification: (id: string) => void
  clearNotifications: () => void
}

export const useUIStore = create<UIState>((set, get) => ({
  // Initial state
  isLoading: false,
  loadingMessage: '',
  activeModal: null,
  modalData: null,
  sidebarOpen: false,
  notifications: [],
  
  // Actions
  setLoading: (isLoading, loadingMessage = '') => 
    set({ isLoading, loadingMessage }),
  
  openModal: (activeModal, modalData = null) => 
    set({ activeModal, modalData }),
  
  closeModal: () => 
    set({ activeModal: null, modalData: null }),
  
  toggleSidebar: () => 
    set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  
  setSidebarOpen: (sidebarOpen) => 
    set({ sidebarOpen }),
  
  addNotification: (notification) => {
    const id = Math.random().toString(36).substring(2)
    const newNotification = { ...notification, id }
    
    set((state) => ({
      notifications: [...state.notifications, newNotification]
    }))
    
    // Auto-remove notification after duration
    if (notification.duration !== 0) {
      const duration = notification.duration || 5000
      setTimeout(() => {
        get().removeNotification(id)
      }, duration)
    }
  },
  
  removeNotification: (id) =>
    set((state) => ({
      notifications: state.notifications.filter(n => n.id !== id)
    })),
  
  clearNotifications: () => 
    set({ notifications: [] })
})) 