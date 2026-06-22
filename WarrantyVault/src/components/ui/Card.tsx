import { View, type ViewProps } from 'react-native';

interface Props extends ViewProps {
  className?: string;
}

/** Elevated surface following Material card conventions. */
export function Card({ className = '', ...rest }: Props) {
  return (
    <View
      className={`rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800 ${className}`}
      {...rest}
    />
  );
}
