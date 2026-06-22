import { ActivityIndicator, Pressable, type PressableProps } from 'react-native';
import { styled } from 'nativewind';

import { Text } from './Text';

const StyledPressable = styled(Pressable);

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';

const BG: Record<ButtonVariant, string> = {
  primary: 'bg-primary active:opacity-80',
  secondary: 'bg-secondary active:opacity-80',
  ghost: 'bg-transparent border border-slate-300 dark:border-slate-600 active:opacity-70',
  danger: 'bg-danger active:opacity-80',
};

const FG: Record<ButtonVariant, string> = {
  primary: 'text-white',
  secondary: 'text-white',
  ghost: 'text-slate-900 dark:text-slate-100',
  danger: 'text-white',
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
  return (
    <StyledPressable
      accessibilityRole="button"
      accessibilityState={{ disabled: !!isDisabled, busy: loading }}
      disabled={isDisabled}
      className={`min-h-[48px] flex-row items-center justify-center rounded-2xl px-5 ${BG[variant]} ${
        isDisabled ? 'opacity-50' : ''
      } ${className}`}
      {...rest}
    >
      {loading ? (
        <ActivityIndicator color="#fff" />
      ) : (
        <Text className={`font-semibold ${FG[variant]}`}>{title}</Text>
      )}
    </StyledPressable>
  );
}
