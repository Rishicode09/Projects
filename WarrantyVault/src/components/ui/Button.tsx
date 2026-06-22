import { LinearGradient } from 'expo-linear-gradient';
import { ActivityIndicator, Pressable, StyleSheet, type PressableProps } from 'react-native';

import { Text } from './Text';

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';

const GRADIENTS: Partial<Record<ButtonVariant, [string, string, ...string[]]>> = {
  primary: ['#6366F1', '#A855F7', '#EC4899'],
  secondary: ['#0EA5E9', '#22D3EE'],
};

const SOLID: Partial<Record<ButtonVariant, string>> = {
  ghost: 'border border-white/25 bg-white/5 active:opacity-70',
  danger: 'bg-danger active:opacity-80',
};

interface Props extends PressableProps {
  title: string;
  variant?: ButtonVariant;
  loading?: boolean;
  className?: string;
}

export function Button({
  title,
  variant = 'primary',
  loading = false,
  disabled,
  className = '',
  ...rest
}: Props) {
  const isDisabled = disabled || loading;
  const gradient = GRADIENTS[variant];

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: !!isDisabled, busy: loading }}
      disabled={isDisabled}
      className={`min-h-[52px] flex-row items-center justify-center overflow-hidden rounded-2xl px-5 ${
        SOLID[variant] ?? 'active:opacity-90'
      } ${isDisabled ? 'opacity-50' : ''} ${className}`}
      {...rest}
    >
      {gradient ? (
        <LinearGradient
          colors={gradient}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={StyleSheet.absoluteFill}
        />
      ) : null}
      {loading ? (
        <ActivityIndicator color="#fff" />
      ) : (
        <Text className="font-bold text-white">{title}</Text>
      )}
    </Pressable>
  );
}
