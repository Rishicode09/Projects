import { TextInput, View, type TextInputProps } from 'react-native';
import { styled } from 'nativewind';

import { Text } from './Text';

const StyledInput = styled(TextInput);
const StyledView = styled(View);

interface Props extends TextInputProps {
  label?: string;
  error?: string | null;
  className?: string;
}

export function Input({ label, error, className = '', ...rest }: Props) {
  return (
    <StyledView className="mb-4">
      {label ? (
        <Text variant="caption" muted className="mb-1.5">
          {label}
        </Text>
      ) : null}
      <StyledInput
        accessibilityLabel={label}
        placeholderTextColor="#94A3B8"
        className={`min-h-[48px] rounded-2xl border bg-white px-4 text-base text-slate-900 dark:bg-slate-800 dark:text-slate-100 ${
          error ? 'border-danger' : 'border-slate-300 dark:border-slate-600'
        } ${className}`}
        {...rest}
      />
      {error ? (
        <Text variant="caption" className="mt-1 text-danger">
          {error}
        </Text>
      ) : null}
    </StyledView>
  );
}
