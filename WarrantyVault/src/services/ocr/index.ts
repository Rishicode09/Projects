import { env } from '@/lib/env';

import { MockOcrService } from './MockOcrService';
import type { OcrService } from './OcrService';
import { SupabaseOcrService } from './SupabaseOcrService';

let instance: OcrService | null = null;

/**
 * Factory + singleton. Provider is selected by EXPO_PUBLIC_OCR_PROVIDER so the
 * rest of the app depends only on the `OcrService` interface.
 */
export function createOcrService(): OcrService {
  if (instance) return instance;
  instance = env.ocrProvider === 'supabase' ? new SupabaseOcrService() : new MockOcrService();
  return instance;
}

/** Test seam for injecting a fake implementation. */
export function __setOcrService(service: OcrService | null): void {
  instance = service;
}

export type { OcrService, OcrInput } from './OcrService';
export { MockOcrService, deriveWarrantyExpiry } from './MockOcrService';
export { SupabaseOcrService } from './SupabaseOcrService';
