/**
 * Integration test for the critical "scan receipt → create product" flow.
 *
 * It exercises the real OCR abstraction (mock provider), the warranty-expiry
 * derivation, Zod validation, and the dashboard stat computation — i.e. the
 * pieces a new product passes through — without requiring a live Supabase
 * backend.
 */
import { addDays } from '@/lib/date';
import { computeDashboardStats } from '@/features/dashboard/dashboard.utils';
import { productDraftSchema } from '@/schemas/product.schema';
import { MockOcrService, deriveWarrantyExpiry } from '@/services/ocr';
import type { Product, ProductDraft } from '@/types/models';

describe('receipt → product flow', () => {
  const ocr = new MockOcrService(0);

  it('turns an extracted receipt into a valid product draft', async () => {
    const extracted = await ocr.extract({ uri: 'file:///r.jpg', mimeType: 'image/jpeg' });
    expect(extracted.ok).toBe(true);
    if (!extracted.ok) return;

    const data = extracted.value;
    const purchaseDate = data.purchase_date!;
    const draft: ProductDraft = {
      name: data.items[0]!.name,
      brand: null,
      category: 'electronics',
      retailer: data.retailer,
      purchase_date: purchaseDate,
      purchase_price: data.items[0]!.price ?? 0,
      warranty_expiry: deriveWarrantyExpiry(purchaseDate, data.warranty_months),
      return_expiry: addDays(purchaseDate, 30),
      receipt_url: 'https://example.com/signed-url',
    };

    const parsed = productDraftSchema.safeParse(draft);
    expect(parsed.success).toBe(true);
  });

  it('a created product shows up in dashboard stats', async () => {
    const extracted = await ocr.extract({ uri: 'file:///r.jpg', mimeType: 'image/jpeg' });
    if (!extracted.ok) throw new Error('extraction failed');

    const purchaseDate = extracted.value.purchase_date!;
    const product: Product = {
      id: 'p1',
      user_id: 'u1',
      name: extracted.value.items[0]!.name,
      brand: null,
      category: 'electronics',
      retailer: extracted.value.retailer,
      purchase_date: purchaseDate,
      purchase_price: extracted.value.items[0]!.price ?? 0,
      warranty_expiry: deriveWarrantyExpiry(purchaseDate, extracted.value.warranty_months),
      return_expiry: addDays(purchaseDate, 30),
      receipt_url: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    const stats = computeDashboardStats([product]);
    expect(stats.activeWarranties).toBe(1);
    expect(stats.totalProtectedValue).toBe(product.purchase_price);
  });
});
