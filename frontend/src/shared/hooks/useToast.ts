import { toast as sonnerToast } from 'sonner';

export interface ToastProps {
  title: string;
  description?: string;
  variant?: 'default' | 'destructive' | 'success' | 'warning';
  duration?: number;
}

export const useToast = () => {
  const toast = ({ title, description, variant = 'default', duration = 4000 }: ToastProps) => {
    switch (variant) {
      case 'destructive':
        return sonnerToast.error(title, {
          description,
          duration,
        });
      case 'success':
        return sonnerToast.success(title, {
          description,
          duration,
        });
      case 'warning':
        return sonnerToast.warning(title, {
          description,
          duration,
        });
      default:
        return sonnerToast(title, {
          description,
          duration,
        });
    }
  };

  return { toast };
}; 