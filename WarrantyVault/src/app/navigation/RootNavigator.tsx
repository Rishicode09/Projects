import { DarkTheme, DefaultTheme, NavigationContainer } from '@react-navigation/native';
import { useEffect } from 'react';
import { ActivityIndicator, View } from 'react-native';

import { useAuthStore } from '@/features/auth/store/authStore';
import { useTheme } from '@/lib/theme/ThemeProvider';

import { AuthNavigator } from './AuthNavigator';
import { MainNavigator } from './MainNavigator';

/** Switches between auth and main flows based on session presence. */
export function RootNavigator() {
  const { session, initializing, initialize } = useAuthStore();
  const { isDark, colors } = useTheme();

  useEffect(() => {
    void initialize();
  }, [initialize]);

  const navTheme = isDark ? DarkTheme : DefaultTheme;

  if (initializing) {
    return (
      <View
        className="flex-1 items-center justify-center"
        style={{ backgroundColor: colors.background }}
      >
        <ActivityIndicator color={colors.primary} size="large" />
      </View>
    );
  }

  return (
    <NavigationContainer theme={navTheme}>
      {session ? <MainNavigator /> : <AuthNavigator />}
    </NavigationContainer>
  );
}
