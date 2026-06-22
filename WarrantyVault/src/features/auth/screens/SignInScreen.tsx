import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { View } from 'react-native';

import { Button, Input, Screen, Text } from '@/components/ui';
import type { AuthStackParamList } from '@/app/navigation/types';

import { useAuthForm } from '../hooks/useAuthForm';

type Props = NativeStackScreenProps<AuthStackParamList, 'SignIn'>;

export function SignInScreen({ navigation }: Props) {
  const { email, setEmail, password, setPassword, loading, error, submit } =
    useAuthForm('signIn');

  return (
    <Screen className="justify-center">
      <Text variant="display" className="mb-1">
        Warranty Vault
      </Text>
      <Text muted className="mb-8">
        Never miss a warranty or return deadline again.
      </Text>

      <Input
        label="Email"
        value={email}
        onChangeText={setEmail}
        autoCapitalize="none"
        keyboardType="email-address"
        textContentType="emailAddress"
        placeholder="you@example.com"
      />
      <Input
        label="Password"
        value={password}
        onChangeText={setPassword}
        secureTextEntry
        textContentType="password"
        placeholder="••••••••"
        error={error}
      />

      <Button title="Sign in" loading={loading} onPress={submit} className="mt-2" />

      <View className="mt-6 flex-row justify-between">
        <Text className="text-primary" onPress={() => navigation.navigate('SignUp')}>
          Create account
        </Text>
        <Text className="text-primary" onPress={() => navigation.navigate('ResetPassword')}>
          Forgot password?
        </Text>
      </View>
    </Screen>
  );
}
