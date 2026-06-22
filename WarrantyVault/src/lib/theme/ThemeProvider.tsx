import { useColorScheme } from 'nativewind';
import React, { createContext, useContext, useMemo } from 'react';

import { darkTheme, lightTheme, type ThemeColors } from './colors';

interface ThemeContextValue {
  colors: ThemeColors;
  isDark: boolean;
  scheme: 'light' | 'dark';
  toggle: () => void;
  setScheme: (scheme: 'light' | 'dark' | 'system') => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const { colorScheme, setColorScheme, toggleColorScheme } = useColorScheme();
  const isDark = colorScheme === 'dark';

  const value = useMemo<ThemeContextValue>(
    () => ({
      colors: isDark ? darkTheme : lightTheme,
      isDark,
      scheme: isDark ? 'dark' : 'light',
      toggle: toggleColorScheme,
      setScheme: setColorScheme,
    }),
    [isDark, setColorScheme, toggleColorScheme]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used within a ThemeProvider');
  return ctx;
}
