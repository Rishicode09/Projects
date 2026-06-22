import { cache, cacheKeys } from '@/lib/cache';
import { demoSettings } from '@/lib/demo/demoDb';
import { env } from '@/lib/env';
import { appError, err, ok, type Result } from '@/lib/result';
import { supabase } from '@/lib/supabase';
import type { NotificationPreferences, UserSettings } from '@/types/models';

const TABLE = 'user_settings';

export const DEFAULT_NOTIFICATION_PREFS: NotificationPreferences = {
  warranty_30_day: true,
  warranty_7_day: true,
  return_1_day: true,
};

function defaults(userId: string): UserSettings {
  return {
    user_id: userId,
    notifications: DEFAULT_NOTIFICATION_PREFS,
    is_premium: false,
    analytics_opt_in: false,
    updated_at: new Date().toISOString(),
  };
}

export class SettingsRepository {
  async get(userId: string): Promise<Result<UserSettings>> {
    if (!env.isConfigured) {
      return ok(await demoSettings.get(userId));
    }

    const { data, error } = await supabase
      .from(TABLE)
      .select('*')
      .eq('user_id', userId)
      .maybeSingle();

    if (error) {
      const cached = await cache.get<UserSettings>(cacheKeys.settings(userId));
      return ok(cached ?? defaults(userId));
    }

    const settings = (data as UserSettings | null) ?? defaults(userId);
    await cache.set(cacheKeys.settings(userId), settings);
    return ok(settings);
  }

  async upsert(settings: UserSettings): Promise<Result<UserSettings>> {
    if (!env.isConfigured) {
      return ok(await demoSettings.upsert(settings));
    }

    const payload = { ...settings, updated_at: new Date().toISOString() };
    const { data, error } = await supabase
      .from(TABLE)
      .upsert(payload, { onConflict: 'user_id' })
      .select('*')
      .single();

    if (error || !data) {
      return err(appError('settings/save-failed', error?.message ?? 'Could not save settings'));
    }
    const saved = data as UserSettings;
    await cache.set(cacheKeys.settings(saved.user_id), saved);
    return ok(saved);
  }
}

export const settingsRepository = new SettingsRepository();
