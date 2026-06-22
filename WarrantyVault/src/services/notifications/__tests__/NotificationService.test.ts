import type { NotificationPreferences, Product } from '@/types/models';

import { NotificationService } from '../NotificationService';

const allOn: NotificationPreferences = {
  warranty_30_day: true,
  warranty_7_day: true,
  return_1_day: true,
};

function product(overrides: Partial<Product>): Product {
  return {
    id: 'p1',
    user_id: 'u1',
    name: 'Widget',
    brand: null,
    category: 'other',
    retailer: null,
    purchase_date: '2026-01-01',
    purchase_price: 10,
    warranty_expiry: null,
    return_expiry: null,
    receipt_url: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('NotificationService.buildPlan', () => {
  const service = new NotificationService();

  it('schedules 30- and 7-day warranty reminders for a future warranty', () => {
    // Far-future warranty so both reminders are still upcoming.
    const future = new Date();
    future.setFullYear(future.getFullYear() + 1);
    const iso = future.toISOString().slice(0, 10);

    const plan = service.buildPlan(product({ warranty_expiry: iso }), allOn);
    const kinds = plan.map((p) => p.kind);
    expect(kinds).toContain('warranty_30_day');
    expect(kinds).toContain('warranty_7_day');
  });

  it('omits reminders whose fire date is already in the past', () => {
    const plan = service.buildPlan(product({ warranty_expiry: '2020-01-01' }), allOn);
    expect(plan).toHaveLength(0);
  });

  it('respects disabled preferences', () => {
    const future = new Date();
    future.setFullYear(future.getFullYear() + 1);
    const iso = future.toISOString().slice(0, 10);

    const plan = service.buildPlan(product({ warranty_expiry: iso }), {
      ...allOn,
      warranty_7_day: false,
    });
    expect(plan.map((p) => p.kind)).not.toContain('warranty_7_day');
  });

  it('schedules a return reminder one day before the deadline', () => {
    const future = new Date();
    future.setMonth(future.getMonth() + 2);
    const iso = future.toISOString().slice(0, 10);

    const plan = service.buildPlan(product({ return_expiry: iso }), allOn);
    expect(plan.map((p) => p.kind)).toContain('return_1_day');
  });
});
