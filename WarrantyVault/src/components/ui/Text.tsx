import { Text as RNText, type TextProps } from 'react-native';

type Variant = 'display' | 'title' | 'subtitle' | 'body' | 'caption';

const VARIANT_CLASS: Record<Variant, string> = {
  display: 'text-4xl font-extrabold tracking-tight',
  title: 'text-2xl font-bold tracking-tight',
  subtitle: 'text-base font-semibold',
  body: 'text-base',
  caption: 'text-sm',
};

interface Props extends TextProps {
  variant?: Variant;
  muted?: boolean;
  className?: string;
}

/** Themed text primitive. Defaults to light foreground for the vibrant dark UI. */
export function Text({ variant = 'body', muted, className = '', ...rest }: Props) {
  const color = muted ? 'text-slate-300/80' : 'text-white';
  return <RNText className={`${VARIANT_CLASS[variant]} ${color} ${className}`} {...rest} />;
}
