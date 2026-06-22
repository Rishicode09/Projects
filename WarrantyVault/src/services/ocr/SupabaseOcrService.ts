import { supabase } from '@/lib/supabase';
import { appError, err, ok, type Result } from '@/lib/result';
import { extractedReceiptSchema } from '@/schemas/receipt.schema';
import type { ExtractedReceipt } from '@/types/models';

import type { OcrInput, OcrService } from './OcrService';

/**
 * Production OCR implementation. Delegates to the `process-receipt` Supabase
 * Edge Function, which holds the AI provider key server-side. The function is
 * expected to return JSON matching `extractedReceiptSchema`.
 */
export class SupabaseOcrService implements OcrService {
  readonly name = 'supabase';

  async extract(input: OcrInput): Promise<Result<ExtractedReceipt>> {
    const { data, error } = await supabase.functions.invoke('process-receipt', {
      body: { uri: input.uri, mimeType: input.mimeType },
    });

    if (error) {
      return err(appError('ocr/edge-function', error.message, error));
    }

    const parsed = extractedReceiptSchema.safeParse(data);
    if (!parsed.success) {
      return err(
        appError('ocr/parse-failed', 'OCR service returned unexpected data', parsed.error)
      );
    }
    return ok(parsed.data);
  }
}
