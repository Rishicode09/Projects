import { extractedReceiptSchema } from '@/schemas/receipt.schema';

import { MockOcrService, deriveWarrantyExpiry } from '../MockOcrService';

describe('MockOcrService', () => {
  const service = new MockOcrService(0); // zero latency in tests

  it('returns an error for empty input', async () => {
    const res = await service.extract({ uri: '', mimeType: 'image/jpeg' });
    expect(res.ok).toBe(false);
  });

  it('produces schema-valid output', async () => {
    const res = await service.extract({ uri: 'file:///receipt1.jpg', mimeType: 'image/jpeg' });
    expect(res.ok).toBe(true);
    if (res.ok) {
      expect(() => extractedReceiptSchema.parse(res.value)).not.toThrow();
      expect(res.value.items.length).toBeGreaterThan(0);
      expect(res.value.confidence).toBeGreaterThan(0);
    }
  });

  it('is deterministic for the same input', async () => {
    const a = await service.extract({ uri: 'file:///same.jpg', mimeType: 'image/jpeg' });
    const b = await service.extract({ uri: 'file:///same.jpg', mimeType: 'image/jpeg' });
    expect(a).toEqual(b);
  });
});

describe('deriveWarrantyExpiry', () => {
  it('returns null when no warranty months', () => {
    expect(deriveWarrantyExpiry('2026-01-01', null)).toBeNull();
  });

  it('adds the warranty months to the purchase date', () => {
    expect(deriveWarrantyExpiry('2026-01-01', 24)).toBe('2028-01-01');
  });
});
