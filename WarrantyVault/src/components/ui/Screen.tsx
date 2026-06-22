import { View, type ViewProps } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

interface Props extends ViewProps {
  className?: string;
  padded?: boolean;
}

/**
 * Root screen container handling the top safe area + themed background. Uses
 * insets directly (rather than SafeAreaView) so NativeWind classes apply to a
 * plain View.
 */
export function Screen({ className = '', padded = true, children, ...rest }: Props) {
  const insets = useSafeAreaInsets();
  return (
    <View
      className="flex-1 bg-background-light dark:bg-background-dark"
      style={{ paddingTop: insets.top }}
    >
      <View className={`flex-1 ${padded ? 'px-4' : ''} ${className}`} {...rest}>
        {children}
      </View>
    </View>
  );
}
