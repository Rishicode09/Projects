import Constants from 'expo-constants';

/**
 * Central, validated access to environment configuration. Reading through this
 * module (instead of `process.env` directly) gives us one place to fail loudly
 * when configuration is missing.
 */
type OcrProvider = 'mock' | 'supabase';

function read(key: string, fallback?: string): string {
  // EXPO_PUBLIC_* vars are inlined at build time; Constants is the fallback.
  const value =
    process.env[key] ??
    (Constants.expoConfig?.extra as Record<string, string> | undefined)?.[key];
  if (value && !value.startsWith('process.env')) return value;
  if (fallback !== undefined) return fallback;
  return '';
}

// Valid-but-non-functional placeholders so `createClient` never throws at
// import time. `assertEnv()` surfaces a clear warning when real values are
// missing; network calls simply fail until configured.
const PLACEHOLDER_URL = 'https://placeholder.supabase.co';
const PLACEHOLDER_KEY = 'placeholder-anon-key';

const rawUrl = read('EXPO_PUBLIC_SUPABASE_URL');
const rawKey = read('EXPO_PUBLIC_SUPABASE_ANON_KEY');

export const env = {
  supabaseUrl: rawUrl || PLACEHOLDER_URL,
  supabaseAnonKey: rawKey || PLACEHOLDER_KEY,
  isConfigured: Boolean(rawUrl && rawKey),
  ocrProvider: (read('EXPO_PUBLIC_OCR_PROVIDER', 'mock') as OcrProvider) || 'mock',
};

export function assertEnv(): void {
  if (!env.isConfigured) {
    // eslint-disable-next-line no-console
    console.warn(
      '[WarrantyVault] Supabase env vars are not set. Copy .env.example to .env and fill them in.'
    );
  }
}
