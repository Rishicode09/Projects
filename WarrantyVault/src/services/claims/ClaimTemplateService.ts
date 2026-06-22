import { formatCurrency } from '@/lib/format';
import { formatDisplayDate } from '@/lib/date';
import type { Product } from '@/types/models';

export type ClaimTone = 'standard' | 'firm';

export interface ClaimInput {
  product: Product;
  customerName: string;
  issueDescription: string;
  tone?: ClaimTone;
}

/**
 * Pure template generator for warranty claim letters. No I/O — the UI handles
 * copy/share. Deterministic output keeps it trivially testable.
 */
export class ClaimTemplateService {
  generate(input: ClaimInput): string {
    const { product, customerName, issueDescription, tone = 'standard' } = input;
    const retailer = product.brand ?? product.retailer ?? 'Customer Support';
    const closing =
      tone === 'firm'
        ? 'I expect a resolution within 14 business days as required under the product warranty.'
        : 'I would appreciate your guidance on the next steps to resolve this under warranty.';

    return [
      `To: ${retailer} Warranty Department`,
      `Re: Warranty claim for ${product.name}`,
      '',
      `Dear ${retailer} Team,`,
      '',
      `I am writing to file a warranty claim for my ${product.name}` +
        (product.brand ? ` (${product.brand})` : '') +
        `, purchased on ${formatDisplayDate(product.purchase_date)}` +
        (product.retailer ? ` from ${product.retailer}` : '') +
        ` for ${formatCurrency(product.purchase_price)}.`,
      '',
      `Issue: ${issueDescription}`,
      '',
      product.warranty_expiry
        ? `This product is covered under warranty until ${formatDisplayDate(product.warranty_expiry)}.`
        : 'This product should still be covered under its manufacturer warranty.',
      '',
      closing,
      '',
      'Please find the original receipt attached for your reference.',
      '',
      'Sincerely,',
      customerName,
    ].join('\n');
  }
}

export const claimTemplateService = new ClaimTemplateService();
