import { z } from 'zod';

export const productCategorySchema = z.enum([
  'electronics',
  'appliances',
  'furniture',
  'tools',
  'clothing',
  'automotive',
  'other',
]);

const isoDate = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/, 'Expected an ISO date (YYYY-MM-DD)');

export const productDraftSchema = z.object({
  name: z.string().min(1, 'Name is required').max(120),
  brand: z.string().max(80).nullable().default(null),
  category: productCategorySchema.default('other'),
  retailer: z.string().max(120).nullable().default(null),
  purchase_date: isoDate,
  purchase_price: z
    .number({ invalid_type_error: 'Price must be a number' })
    .nonnegative('Price cannot be negative'),
  warranty_expiry: isoDate.nullable().default(null),
  return_expiry: isoDate.nullable().default(null),
  receipt_url: z.string().url().nullable().default(null),
});

export const productSchema = productDraftSchema.extend({
  id: z.string().uuid(),
  user_id: z.string().uuid(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const productUpdateSchema = productDraftSchema.partial();

export type ProductDraftInput = z.input<typeof productDraftSchema>;
export type ProductDraftParsed = z.output<typeof productDraftSchema>;
