import { View, type ViewProps } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { AnimatedBackground } from './AnimatedBackground';

interface Props extends ViewProps {
  className?: string;
  padded?: boolean;
  /** Render the animated vibrant backdrop (default true). */
  animated?: boolean;
}

/**
 * Root screen container. Renders the animated gradient backdrop behind a
 * transparent content layer and applies the top safe-area inset.
 */
export function Screen({ className = '', padded = true, animated = true, children, ...rest }: Props) {
  const insets = useSafeAreaInsets();
  return (
    <View className="flex-1 bg-background-dark">
      {animated ? <AnimatedBackground /> : null}
      <View className="flex-1" style={{ paddingTop: insets.top }}>
        <View className={`flex-1 ${padded ? 'px-4' : ''} ${className}`} {...rest}>
          {children}
        </View>
      </View>
    </View>
  );
}
