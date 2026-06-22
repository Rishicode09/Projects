import { appError, err, ok, type Result } from '@/lib/result';
import { supabase } from '@/lib/supabase';
import { signInSchema, signUpSchema, resetPasswordSchema } from '@/schemas/auth.schema';

/** Thin, validated wrapper over Supabase Auth. */
export const authService = {
  async signUp(email: string, password: string): Promise<Result<void>> {
    const parsed = signUpSchema.safeParse({ email, password });
    if (!parsed.success) {
      return err(appError('auth/invalid', parsed.error.issues[0]?.message ?? 'Invalid input'));
    }
    const { error } = await supabase.auth.signUp(parsed.data);
    if (error) return err(appError('auth/sign-up-failed', error.message, error));
    return ok(undefined);
  },

  async signIn(email: string, password: string): Promise<Result<void>> {
    const parsed = signInSchema.safeParse({ email, password });
    if (!parsed.success) {
      return err(appError('auth/invalid', parsed.error.issues[0]?.message ?? 'Invalid input'));
    }
    const { error } = await supabase.auth.signInWithPassword(parsed.data);
    if (error) return err(appError('auth/sign-in-failed', error.message, error));
    return ok(undefined);
  },

  async resetPassword(email: string): Promise<Result<void>> {
    const parsed = resetPasswordSchema.safeParse({ email });
    if (!parsed.success) {
      return err(appError('auth/invalid', parsed.error.issues[0]?.message ?? 'Invalid email'));
    }
    const { error } = await supabase.auth.resetPasswordForEmail(parsed.data.email, {
      redirectTo: 'warrantyvault://reset-password',
    });
    if (error) return err(appError('auth/reset-failed', error.message, error));
    return ok(undefined);
  },
};
