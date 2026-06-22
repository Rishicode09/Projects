import { demoAuth } from '@/lib/demo/demoAuth';
import { env } from '@/lib/env';
import { appError, err, ok, type Result } from '@/lib/result';
import { supabase } from '@/lib/supabase';
import { signInSchema, signUpSchema, resetPasswordSchema } from '@/schemas/auth.schema';

/**
 * Auth facade. When Supabase isn't configured (`env.isConfigured === false`) it
 * transparently falls back to a local demo backend so the app is fully usable
 * offline. With real keys, it uses Supabase Auth.
 */
const friendlyNetworkError =
  'Could not reach the server. Check your connection, or run in demo mode (no Supabase keys set).';

function toMessage(raw: string): string {
  if (/fetch|network/i.test(raw)) return friendlyNetworkError;
  return raw;
}

export const authService = {
  async signUp(email: string, password: string): Promise<Result<void>> {
    const parsed = signUpSchema.safeParse({ email, password });
    if (!parsed.success) {
      return err(appError('auth/invalid', parsed.error.issues[0]?.message ?? 'Invalid input'));
    }
    if (!env.isConfigured) {
      try {
        await demoAuth.signUp(parsed.data.email, parsed.data.password);
        return ok(undefined);
      } catch (e) {
        return err(appError('auth/sign-up-failed', (e as Error).message));
      }
    }
    const { error } = await supabase.auth.signUp(parsed.data);
    if (error) return err(appError('auth/sign-up-failed', toMessage(error.message), error));
    return ok(undefined);
  },

  async signIn(email: string, password: string): Promise<Result<void>> {
    const parsed = signInSchema.safeParse({ email, password });
    if (!parsed.success) {
      return err(appError('auth/invalid', parsed.error.issues[0]?.message ?? 'Invalid input'));
    }
    if (!env.isConfigured) {
      try {
        await demoAuth.signIn(parsed.data.email, parsed.data.password);
        return ok(undefined);
      } catch (e) {
        return err(appError('auth/sign-in-failed', (e as Error).message));
      }
    }
    const { error } = await supabase.auth.signInWithPassword(parsed.data);
    if (error) return err(appError('auth/sign-in-failed', toMessage(error.message), error));
    return ok(undefined);
  },

  async resetPassword(email: string): Promise<Result<void>> {
    const parsed = resetPasswordSchema.safeParse({ email });
    if (!parsed.success) {
      return err(appError('auth/invalid', parsed.error.issues[0]?.message ?? 'Invalid email'));
    }
    if (!env.isConfigured) {
      // No mail server in demo mode; treat as a no-op success.
      return ok(undefined);
    }
    const { error } = await supabase.auth.resetPasswordForEmail(parsed.data.email, {
      redirectTo: 'warrantyvault://reset-password',
    });
    if (error) return err(appError('auth/reset-failed', toMessage(error.message), error));
    return ok(undefined);
  },
};
