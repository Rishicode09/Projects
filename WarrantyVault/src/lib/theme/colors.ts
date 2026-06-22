/**
 * Theme tokens shared between NativeWind (tailwind.config.js) and imperative
 * styling (e.g. navigation themes, status bar). Keep in sync with the Tailwind
 * palette.
 */
export const palette = {
  primary: '#4F46E5',
  secondary: '#0EA5E9',
  success: '#16A34A',
  warning: '#F59E0B',
  danger: '#DC2626',
};

export const lightTheme = {
  background: '#F8FAFC',
  surface: '#FFFFFF',
  text: '#0F172A',
  textMuted: '#64748B',
  border: '#E2E8F0',
  ...palette,
};

export const darkTheme = {
  background: '#0F172A',
  surface: '#1E293B',
  text: '#F1F5F9',
  textMuted: '#94A3B8',
  border: '#334155',
  ...palette,
};

export type ThemeColors = typeof lightTheme;
