import { useEffect } from 'react';

import { useAuthStore } from '@/features/auth/store/authStore';
import { useProductStore } from '../store/productStore';

/** Loads the current user's products and exposes the store slice. */
export function useProducts() {
  const userId = useAuthStore((s) => s.user?.id);
  const { products, loading, error, load } = useProductStore();

  useEffect(() => {
    if (userId) void load(userId);
  }, [userId, load]);

  return {
    products,
    loading,
    error,
    reload: () => (userId ? load(userId) : Promise.resolve()),
  };
}
