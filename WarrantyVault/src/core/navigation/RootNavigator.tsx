import { DarkTheme, NavigationContainer } from '@react-navigation/native';
import { useEffect } from 'react';
import { ActivityIndicator, View } from 'react-native';

import { useAuthStore } from '@/features/auth/store/authStore';

import { AuthNavigator } from './AuthNavigator';
import { MainNavigator } from './MainNavigator';

// Dark, transparent navigation theme so the animated gradient shows through
// and there's never a white flash between screens.
const navTheme = {
  ...DarkTheme,
  colors: {
    ...DarkTheme.colors,
    background: '#0B1026',
    card: 'rgba(15,23,42,0.92)',
    border: 'rgba(255,255,255,0.08)',
    text: '#F8FAFC',
    primary: '#C4B5FD',
  },
};

/** Switches between auth and main flows based on session presence. */
export function RootNavigator() {
  const { session, initializing, initialize } = useAuthStore();

  useEffect(() => {
    void initialize();
  }, [initialize]);

  if (initializing) {
    return (
      <View className="flex-1 items-center justify-center" style={{ backgroundColor: '#0B1026' }}>
        <ActivityIndicator color="#C4B5FD" size="large" />
      </View>
    );
  }

  return (
    <NavigationContainer theme={navTheme}>
      {session ? <MainNavigator /> : <AuthNavigator />}
    </NavigationContainer>
  );
}
