import './global.css';

import { AppProviders } from '@/core/providers/AppProviders';
import { RootNavigator } from '@/core/navigation/RootNavigator';
import { assertEnv } from '@/lib/env';

assertEnv();

export default function App() {
  return (
    <AppProviders>
      <RootNavigator />
    </AppProviders>
  );
}
