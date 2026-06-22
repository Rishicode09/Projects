import type { Result } from '@/lib/result';
import type { ExtractedReceipt } from '@/types/models';

export interface OcrInput {
  /** Local URI or remote URL of the receipt image/PDF. */
  uri: string;
  /** MIME type, used to branch on PDF vs image handling. */
  mimeType: string;
}

/**
 * Abstraction over receipt OCR + extraction. Implementations must return a
 * validated, strongly typed `ExtractedReceipt`. Swapping providers (mock vs.
 * Supabase Edge Function vs. a future on-device model) requires no changes to
 * callers — see `createOcrService`.
 */
export interface OcrService {
  readonly name: string;
  extract(input: OcrInput): Promise<Result<ExtractedReceipt>>;
}
