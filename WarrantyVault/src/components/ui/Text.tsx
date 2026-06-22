import { Text as RNText, type TextProps } from 'react-native';

type Variant = 'display' | 'title' | 'subtitle' | 'body' | 'caption';

const VARIANT_CLASS: Record<Variant, string> = {
  display: 'text-3xl font-bold',
  title: 'text-xl font-semibold',
  subtitle: 'text-base font-semibold',
  body: 'text-base',
  caption: 'text-sm',
};

interface Props extends TextProps {
  variant?: Variant;
  muted?: boolean;
  className?: string;
}

/** Themed text primitive. Defaults to dark-mode-aware foreground colors. */
export function Text({ variant = 'body', muted, className = '', ...rest }: Props) {
  const color = muted ? 'text-slate-500 dark:text-slate-400' : 'text-slate-900 dark:text-slate-100';
  return <RNText className={`${VARIANT_CLASS[variant]} ${color} ${className}`} {...rest} />;
}
