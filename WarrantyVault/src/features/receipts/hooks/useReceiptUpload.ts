import * as DocumentPicker from 'expo-document-picker';
import * as ImagePicker from 'expo-image-picker';
import { useState } from 'react';

import { useAuthStore } from '@/features/auth/store/authStore';
import { deriveWarrantyExpiry } from '@/services/ocr';
import { createOcrService } from '@/services/ocr';
import { storageService } from '@/services/storage/StorageService';
import { addDays } from '@/lib/date';
import { env } from '@/lib/env';
import type { ProductDraft } from '@/types/models';

type Phase = 'idle' | 'uploading' | 'processing' | 'done' | 'error';

export interface ReceiptResult {
  receiptUrl: string;
  draft: ProductDraft;
}

const DEFAULT_RETURN_WINDOW_DAYS = 30;

/**
 * Orchestrates the full receipt capture flow: pick a file (photo or PDF) →
 * upload to Storage → run OCR → map the extraction into a `ProductDraft` the
 * form can pre-fill. Each step surfaces a phase for UI feedback.
 */
export function useReceiptUpload() {
  const userId = useAuthStore((s) => s.user?.id);
  const [phase, setPhase] = useState<Phase>('idle');
  const [error, setError] = useState<string | null>(null);

  async function pickImage(): Promise<{ uri: string; mimeType: string } | null> {
    const res = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.8,
    });
    if (res.canceled || !res.assets[0]) return null;
    const asset = res.assets[0];
    return { uri: asset.uri, mimeType: asset.mimeType ?? 'image/jpeg' };
  }

  async function pickDocument(): Promise<{ uri: string; mimeType: string } | null> {
    const res = await DocumentPicker.getDocumentAsync({
      type: ['image/*', 'application/pdf'],
      copyToCacheDirectory: true,
    });
    if (res.canceled || !res.assets[0]) return null;
    const asset = res.assets[0];
    return { uri: asset.uri, mimeType: asset.mimeType ?? 'application/pdf' };
  }

  async function process(source: { uri: string; mimeType: string }): Promise<ReceiptResult | null> {
    if (!userId) {
      setError('You must be signed in to upload receipts.');
      setPhase('error');
      return null;
    }

    setError(null);

    // In demo mode (no Supabase) we keep the local file URI instead of
    // uploading to cloud storage.
    let receiptUrl = source.uri;
    if (env.isConfigured) {
      setPhase('uploading');
      const upload = await storageService.upload({ userId, ...source });
      if (!upload.ok) {
        setError(upload.error.message);
        setPhase('error');
        return null;
      }
      receiptUrl = upload.value.signedUrl;
    }

    setPhase('processing');
    const ocr = createOcrService();
    const extracted = await ocr.extract(source);
    if (!extracted.ok) {
      setError(extracted.error.message);
      setPhase('error');
      return null;
    }

    const data = extracted.value;
    const purchaseDate = data.purchase_date ?? new Date().toISOString().slice(0, 10);
    const draft: ProductDraft = {
      name: data.items[0]?.name ?? 'New product',
      brand: null,
      category: 'other',
      retailer: data.retailer,
      purchase_date: purchaseDate,
      purchase_price: data.items[0]?.price ?? data.total_amount ?? 0,
      warranty_expiry: deriveWarrantyExpiry(purchaseDate, data.warranty_months),
      return_expiry: addDays(purchaseDate, DEFAULT_RETURN_WINDOW_DAYS),
      receipt_url: receiptUrl,
    };

    setPhase('done');
    return { receiptUrl, draft };
  }

  return { phase, error, pickImage, pickDocument, process };
}
