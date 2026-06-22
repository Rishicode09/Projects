import { TextInput, View, type TextInputProps } from 'react-native';

import { Text } from './Text';

interface Props extends TextInputProps {
  label?: string;
  error?: string | null;
  className?: string;
}

export function Input({ label, error, className = '', ...rest }: Props) {
  return (
    <View className="mb-4">
      {label ? (
        <Text variant="caption" muted className="mb-1.5">
          {label}
        </Text>
      ) : null}
      <TextInput
        accessibilityLabel={label}
        placeholderTextColor="#94A3B8"
        className={`min-h-[52px] rounded-2xl border bg-white/10 px-4 text-base text-white ${
          error ? 'border-danger' : 'border-white/20'
        } ${className}`}
        {...rest}
      />
      {error ? (
        <Text variant="caption" className="mt-1 text-danger">
          {error}
        </Text>
      ) : null}
    </View>
  );
}
