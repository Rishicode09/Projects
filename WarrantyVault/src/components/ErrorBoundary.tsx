import React from 'react';
import { View } from 'react-native';

import { Button, Text } from './ui';

interface Props {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

interface State {
  error: Error | null;
}

/**
 * App-level error boundary. Catches render-time exceptions so a single broken
 * screen can't blank the whole app, and offers a recovery action.
 */
export class ErrorBoundary extends React.Component<Props, State> {
  override state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  override componentDidCatch(error: Error, info: React.ErrorInfo): void {
    // eslint-disable-next-line no-console
    console.error('[ErrorBoundary]', error, info.componentStack);
  }

  reset = (): void => this.setState({ error: null });

  override render(): React.ReactNode {
    if (!this.state.error) return this.props.children;
    if (this.props.fallback) return this.props.fallback;

    return (
      <View className="flex-1 items-center justify-center bg-background-light p-6 dark:bg-background-dark">
        <Text variant="title" className="mb-2 text-center">
          Something went wrong
        </Text>
        <Text muted className="mb-6 text-center">
          {this.state.error.message}
        </Text>
        <Button title="Try again" onPress={this.reset} />
      </View>
    );
  }
}
