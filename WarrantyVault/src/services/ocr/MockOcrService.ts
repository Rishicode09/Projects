import { addMonths, toIsoDate } from '@/lib/date';
import { appError, err, ok, type Result } from '@/lib/result';
import { extractedReceiptSchema } from '@/schemas/receipt.schema';
import type { ExtractedReceipt } from '@/types/models';

import type { OcrInput, OcrService } from './OcrService';

const SAMPLE_RETAILERS = ['Best Buy', 'Apple Store', 'IKEA', 'Home Depot', 'Amazon'];
const SAMPLE_ITEMS = [
  { name: 'Wireless Headphones', price: 199.99, warranty: 12 },
  { name: 'Espresso Machine', price: 449.0, warranty: 24 },
  { name: 'Office Chair', price: 329.5, warranty: 60 },
  { name: 'Cordless Drill', price: 129.0, warranty: 36 },
  { name: '4K Monitor', price: 379.99, warranty: 36 },
];

/**
 * Deterministic, offline OCR implementation used for development, demos and
 * tests. It fabricates a plausible receipt from a hash of the input URI so the
 * same input always yields the same result.
 */
export class MockOcrService implements OcrService {
  readonly name = 'mock';

  constructor(private readonly latencyMs = 600) {}

  async extract(input: OcrInput): Promise<Result<ExtractedReceipt>> {
    if (!input.uri) {
      return err(appError('ocr/invalid-input', 'No receipt URI provided'));
    }

    await new Promise((resolve) => setTimeout(resolve, this.latencyMs));

    const seed = hash(input.uri);
    const retailer = SAMPLE_RETAILERS[seed % SAMPLE_RETAILERS.length]!;
    const primary = SAMPLE_ITEMS[seed % SAMPLE_ITEMS.length]!;
    const secondary = SAMPLE_ITEMS[(seed + 2) % SAMPLE_ITEMS.length]!;
    const purchaseDate = toIsoDate(new Date());

    const candidate = {
      retailer,
      purchase_date: purchaseDate,
      items: [
        { name: primary.name, price: primary.price },
        { name: secondary.name, price: secondary.price },
      ],
      total_amount: Number((primary.price + secondary.price).toFixed(2)),
      warranty_months: primary.warranty,
      warranty_text: `${primary.warranty}-month manufacturer warranty`,
      confidence: 0.92,
    };

    // Even the mock validates its own output so the contract is enforced.
    const parsed = extractedReceiptSchema.safeParse(candidate);
    if (!parsed.success) {
      return err(appError('ocr/parse-failed', 'Mock produced invalid data'));
    }
    return ok(parsed.data);
  }
}

/** Derived warranty expiry helper used by callers of the extraction result. */
export function deriveWarrantyExpiry(
  purchaseDate: string,
  warrantyMonths: number | null
): string | null {
  if (!warrantyMonths) return null;
  return addMonths(purchaseDate, warrantyMonths);
}

function hash(value: string): number {
  let h = 0;
  for (let i = 0; i < value.length; i += 1) {
    h = (h << 5) - h + value.charCodeAt(i);
    h |= 0;
  }
  return Math.abs(h);
}
