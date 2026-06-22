import AsyncStorage from '@react-native-async-storage/async-storage';
import { createClient } from '@supabase/supabase-js';

import { env } from './env';

/**
 * Singleton Supabase client. AsyncStorage is used as the auth storage adapter
 * so sessions persist across app restarts. `detectSessionInUrl` is disabled
 * because there is no browser URL on native.
 */
export const supabase = createClient(env.supabaseUrl, env.supabaseAnonKey, {
  auth: {
    storage: AsyncStorage,
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: false,
  },
});

export const RECEIPTS_BUCKET = 'receipts';
