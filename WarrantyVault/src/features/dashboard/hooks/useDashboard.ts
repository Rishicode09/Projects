import { useMemo } from 'react';

import { useProducts } from '@/features/products/hooks/useProducts';
import type { DashboardStats } from '@/types/models';

import { computeDashboardStats } from '../dashboard.utils';

export function useDashboard(): {
  stats: DashboardStats;
  loading: boolean;
  reload: () => Promise<void>;
} {
  const { products, loading, reload } = useProducts();
  const stats = useMemo(() => computeDashboardStats(products), [products]);
  return { stats, loading, reload };
}
