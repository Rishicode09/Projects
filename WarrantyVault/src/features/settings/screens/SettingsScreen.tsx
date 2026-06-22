import { ScrollView, Switch, View } from 'react-native';

import { Button, Card, Screen, Text } from '@/components/ui';
import { useAuthStore } from '@/features/auth/store/authStore';
import { useTheme } from '@/lib/theme/ThemeProvider';
import type { NotificationPreferences } from '@/types/models';

import { useSettings } from '../hooks/useSettings';

function ToggleRow({
  label,
  description,
  value,
  onValueChange,
}: {
  label: string;
  description?: string;
  value: boolean;
  onValueChange: (v: boolean) => void;
}) {
  return (
    <View className="flex-row items-center justify-between border-b border-slate-100 py-3 dark:border-slate-700">
      <View className="flex-1 pr-3">
        <Text className="font-medium">{label}</Text>
        {description ? (
          <Text variant="caption" muted>
            {description}
          </Text>
        ) : null}
      </View>
      <Switch value={value} onValueChange={onValueChange} accessibilityLabel={label} />
    </View>
  );
}

const NOTIF_ROWS: { key: keyof NotificationPreferences; label: string; description: string }[] = [
  { key: 'warranty_30_day', label: '30 days before warranty', description: 'Heads-up a month out' },
  { key: 'warranty_7_day', label: '7 days before warranty', description: 'Final week reminder' },
  { key: 'return_1_day', label: '1 day before return', description: 'Last chance to return' },
];

export function SettingsScreen() {
  const { settings, toggleNotification, setFlag } = useSettings();
  const signOut = useAuthStore((s) => s.signOut);
  const { isDark, toggle } = useTheme();

  return (
    <Screen padded={false}>
      <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 40 }}>
        <Text variant="display" className="mb-4">
          Settings
        </Text>

        <Text variant="subtitle" className="mb-2">
          Notifications
        </Text>
        <Card className="mb-6">
          {NOTIF_ROWS.map((row) => (
            <ToggleRow
              key={row.key}
              label={row.label}
              description={row.description}
              value={settings?.notifications[row.key] ?? false}
              onValueChange={() => toggleNotification(row.key)}
            />
          ))}
        </Card>

        <Text variant="subtitle" className="mb-2">
          Appearance
        </Text>
        <Card className="mb-6">
          <ToggleRow label="Dark mode" value={isDark} onValueChange={toggle} />
        </Card>

        <Text variant="subtitle" className="mb-2">
          Privacy
        </Text>
        <Card className="mb-6">
          <ToggleRow
            label="Share anonymous analytics"
            description="Help improve Warranty Vault"
            value={settings?.analytics_opt_in ?? false}
            onValueChange={(v) => setFlag('analytics_opt_in', v)}
          />
        </Card>

        <Text variant="subtitle" className="mb-2">
          Premium
        </Text>
        <Card className="mb-6">
          <Text muted className="mb-3">
            {settings?.is_premium
              ? 'You have Premium. Thank you!'
              : 'Unlock unlimited products, cloud backup, and family sharing.'}
          </Text>
          {!settings?.is_premium ? (
            <Button title="Upgrade to Premium" onPress={() => setFlag('is_premium', true)} />
          ) : null}
        </Card>

        <Button title="Sign out" variant="danger" onPress={signOut} />
      </ScrollView>
    </Screen>
  );
}
