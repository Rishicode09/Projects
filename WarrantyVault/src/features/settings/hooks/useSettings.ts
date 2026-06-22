import { useCallback, useEffect, useState } from 'react';

import { useAuthStore } from '@/features/auth/store/authStore';
import { settingsRepository } from '@/repositories/SettingsRepository';
import type { NotificationPreferences, UserSettings } from '@/types/models';

/** Loads and mutates the current user's settings with optimistic updates. */
export function useSettings() {
  const userId = useAuthStore((s) => s.user?.id);
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!userId) return;
    let active = true;
    void settingsRepository.get(userId).then((res) => {
      if (active && res.ok) {
        setSettings(res.value);
        setLoading(false);
      }
    });
    return () => {
      active = false;
    };
  }, [userId]);

  const save = useCallback(async (next: UserSettings) => {
    setSettings(next); // optimistic
    const res = await settingsRepository.upsert(next);
    if (res.ok) setSettings(res.value);
  }, []);

  const toggleNotification = useCallback(
    (key: keyof NotificationPreferences) => {
      if (!settings) return;
      void save({
        ...settings,
        notifications: { ...settings.notifications, [key]: !settings.notifications[key] },
      });
    },
    [settings, save]
  );

  const setFlag = useCallback(
    (key: 'is_premium' | 'analytics_opt_in', value: boolean) => {
      if (!settings) return;
      void save({ ...settings, [key]: value });
    },
    [settings, save]
  );

  return { settings, loading, toggleNotification, setFlag };
}
