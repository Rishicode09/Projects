import type { Product } from '@/types/models';

import { ClaimTemplateService } from '../ClaimTemplateService';

const product: Product = {
  id: 'p1',
  user_id: 'u1',
  name: 'Sony WH-1000XM5',
  brand: 'Sony',
  category: 'electronics',
  retailer: 'Best Buy',
  purchase_date: '2026-01-15',
  purchase_price: 399.99,
  warranty_expiry: '2028-01-15',
  return_expiry: null,
  receipt_url: null,
  created_at: '2026-01-15T00:00:00Z',
  updated_at: '2026-01-15T00:00:00Z',
};

describe('ClaimTemplateService', () => {
  const service = new ClaimTemplateService();

  it('includes the product, customer, and issue', () => {
    const letter = service.generate({
      product,
      customerName: 'Jane Doe',
      issueDescription: 'Left earcup stopped working.',
    });
    expect(letter).toContain('Sony WH-1000XM5');
    expect(letter).toContain('Jane Doe');
    expect(letter).toContain('Left earcup stopped working.');
    expect(letter).toContain('Best Buy');
  });

  it('uses firmer language for the firm tone', () => {
    const firm = service.generate({
      product,
      customerName: 'Jane Doe',
      issueDescription: 'Fault',
      tone: 'firm',
    });
    expect(firm).toContain('14 business days');
  });

  it('mentions the warranty expiry when present', () => {
    const letter = service.generate({ product, customerName: 'A', issueDescription: 'x' });
    expect(letter).toMatch(/covered under warranty until/i);
  });
});
