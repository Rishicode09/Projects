import * as FileSystem from 'expo-file-system';

import { RECEIPTS_BUCKET, supabase } from '@/lib/supabase';
import { appError, err, ok, tryAsync, type Result } from '@/lib/result';

export interface UploadInput {
  userId: string;
  uri: string;
  mimeType: string;
}

export interface UploadResult {
  path: string;
  /** Signed URL valid for `signedUrlTtl` seconds. */
  signedUrl: string;
}

const EXT_BY_MIME: Record<string, string> = {
  'image/jpeg': 'jpg',
  'image/png': 'png',
  'image/heic': 'heic',
  'application/pdf': 'pdf',
};

/**
 * Handles receipt file uploads to the private `receipts` Storage bucket and
 * issues short-lived signed URLs. Files are namespaced by user id; RLS on the
 * bucket enforces that a user can only access their own folder.
 */
export class StorageService {
  constructor(private readonly signedUrlTtl = 60 * 60) {}

  async upload({ userId, uri, mimeType }: UploadInput): Promise<Result<UploadResult>> {
    const ext = EXT_BY_MIME[mimeType] ?? 'bin';
    const path = `${userId}/${Date.now()}.${ext}`;

    const read = await tryAsync(
      () => FileSystem.readAsStringAsync(uri, { encoding: FileSystem.EncodingType.Base64 }),
      'storage/read-failed'
    );
    if (!read.ok) return read;

    const bytes = decodeBase64(read.value);
    const { error } = await supabase.storage
      .from(RECEIPTS_BUCKET)
      .upload(path, bytes, { contentType: mimeType, upsert: false });

    if (error) return err(appError('storage/upload-failed', error.message, error));

    return this.getSignedUrl(path);
  }

  async getSignedUrl(path: string): Promise<Result<UploadResult>> {
    const { data, error } = await supabase.storage
      .from(RECEIPTS_BUCKET)
      .createSignedUrl(path, this.signedUrlTtl);

    if (error || !data) {
      return err(appError('storage/sign-failed', error?.message ?? 'Could not sign URL'));
    }
    return ok({ path, signedUrl: data.signedUrl });
  }

  async remove(path: string): Promise<Result<void>> {
    const { error } = await supabase.storage.from(RECEIPTS_BUCKET).remove([path]);
    if (error) return err(appError('storage/delete-failed', error.message, error));
    return ok(undefined);
  }
}

function decodeBase64(base64: string): Uint8Array {
  // global.atob is available in the Hermes/React Native runtime via the URL polyfill.
  const binary = globalThis.atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

export const storageService = new StorageService();
