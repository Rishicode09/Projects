import type { Product } from '@/types/models';

import { computeDashboardStats } from '../dashboard.utils';

const now = new Date('2026-06-22T12:00:00.000Z');

function make(overrides: Partial<Product>): Product {
  return {
    id: Math.random().toString(),
    user_id: 'u1',
    name: 'Item',
    brand: null,
    category: 'other',
    retailer: null,
    purchase_date: '2026-01-01',
    purchase_price: 100,
    warranty_expiry: null,
    return_expiry: null,
    receipt_url: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('computeDashboardStats', () => {
  it('counts only active warranties toward protected value', () => {
    const products = [
      make({ warranty_expiry: '2026-12-31', purchase_price: 200 }), // active
      make({ warranty_expiry: '2026-01-01', purchase_price: 999 }), // expired
      make({ warranty_expiry: null, purchase_price: 500 }), // no warranty
    ];
    const stats = computeDashboardStats(products, now);
    expect(stats.activeWarranties).toBe(1);
    expect(stats.totalProtectedValue).toBe(200);
  });

  it('flags warranties expiring within 30 days', () => {
    const products = [
      make({ warranty_expiry: '2026-07-10' }), // ~18 days out
      make({ warranty_expiry: '2026-12-31' }), // far out
    ];
    const stats = computeDashboardStats(products, now);
    expect(stats.expiringSoon).toBe(1);
  });

  it('estimates savings at 15% of protected value', () => {
    const products = [make({ warranty_expiry: '2026-12-31', purchase_price: 1000 })];
    const stats = computeDashboardStats(products, now);
    expect(stats.savingsEstimate).toBe(150);
  });

  it('returns the 5 most recent additions', () => {
    const products = Array.from({ length: 8 }, (_, i) =>
      make({ created_at: `2026-01-0${(i % 9) + 1}T00:00:00Z` })
    );
    const stats = computeDashboardStats(products, now);
    expect(stats.recentAdditions).toHaveLength(5);
  });
});
