import { View, type ViewProps } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { styled } from 'nativewind';

const StyledSafeArea = styled(SafeAreaView);
const StyledView = styled(View);

interface Props extends ViewProps {
  className?: string;
  padded?: boolean;
}

/** Root screen container handling safe areas + themed background. */
export function Screen({ className = '', padded = true, children, ...rest }: Props) {
  return (
    <StyledSafeArea className="flex-1 bg-background-light dark:bg-background-dark" edges={['top']}>
      <StyledView className={`flex-1 ${padded ? 'px-4' : ''} ${className}`} {...rest}>
        {children}
      </StyledView>
    </StyledSafeArea>
  );
}
