import { daysUntil, isFuture } from '@/lib/date';
import type { DashboardStats, Product } from '@/types/models';

const EXPIRING_WINDOW_DAYS = 30;

/**
 * Pure computation of dashboard metrics from a product list. Kept separate from
 * any hook/store so it can be unit tested with fixed `now` values.
 */
export function computeDashboardStats(
  products: Product[],
  now: Date = new Date()
): DashboardStats {
  let activeWarranties = 0;
  let expiringSoon = 0;
  let totalProtectedValue = 0;

  for (const product of products) {
    if (product.warranty_expiry && isFuture(product.warranty_expiry, now)) {
      activeWarranties += 1;
      totalProtectedValue += product.purchase_price;
      const days = daysUntil(product.warranty_expiry, now);
      if (days <= EXPIRING_WINDOW_DAYS) expiringSoon += 1;
    }
  }

  const recentAdditions = [...products]
    .sort((a, b) => b.created_at.localeCompare(a.created_at))
    .slice(0, 5);

  // Savings estimate: protecting an item under warranty avoids ~paying for an
  // out-of-pocket repair, estimated at 15% of purchase price.
  const savingsEstimate = Number((totalProtectedValue * 0.15).toFixed(2));

  return {
    activeWarranties,
    expiringSoon,
    totalProtectedValue: Number(totalProtectedValue.toFixed(2)),
    recentAdditions,
    savingsEstimate,
  };
}
