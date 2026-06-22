import { View, type ViewProps } from 'react-native';

interface Props extends ViewProps {
  className?: string;
}

/**
 * Glassmorphism surface: translucent white over the animated backdrop with a
 * bright hairline border for that frosted, lit-from-within look.
 */
export function Card({ className = '', style, ...rest }: Props) {
  return (
    <View
      className={`rounded-3xl border border-white/15 bg-white/10 p-4 ${className}`}
      style={[
        {
          shadowColor: '#000',
          shadowOpacity: 0.3,
          shadowRadius: 16,
          shadowOffset: { width: 0, height: 8 },
          elevation: 6,
        },
        style,
      ]}
      {...rest}
    />
  );
}
