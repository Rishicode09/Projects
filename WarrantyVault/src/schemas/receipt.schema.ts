import { z } from 'zod';

/**
 * Validates the JSON returned by an OCR provider before it is trusted by the
 * app. AI/edge-function output is untrusted input — always parse it.
 */
export const extractedLineItemSchema = z.object({
  name: z.string().min(1),
  price: z.number().nonnegative().nullable(),
});

export const extractedReceiptSchema = z.object({
  retailer: z.string().nullable(),
  purchase_date: z
    .string()
    .regex(/^\d{4}-\d{2}-\d{2}$/)
    .nullable(),
  items: z.array(extractedLineItemSchema).default([]),
  total_amount: z.number().nonnegative().nullable(),
  warranty_months: z.number().int().nonnegative().nullable(),
  warranty_text: z.string().nullable(),
  confidence: z.number().min(0).max(1).default(0),
});

export type ExtractedReceiptParsed = z.infer<typeof extractedReceiptSchema>;
