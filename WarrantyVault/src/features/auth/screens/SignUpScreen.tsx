import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { View } from 'react-native';

import { Button, Input, Screen, Text } from '@/components/ui';
import type { AuthStackParamList } from '@/app/navigation/types';

import { useAuthForm } from '../hooks/useAuthForm';

type Props = NativeStackScreenProps<AuthStackParamList, 'SignUp'>;

export function SignUpScreen({ navigation }: Props) {
  const { email, setEmail, password, setPassword, loading, error, info, submit } =
    useAuthForm('signUp');

  return (
    <Screen className="justify-center">
      <Text variant="display" className="mb-1">
        Create account
      </Text>
      <Text muted className="mb-8">
        Start protecting your purchases in seconds.
      </Text>

      <Input
        label="Email"
        value={email}
        onChangeText={setEmail}
        autoCapitalize="none"
        keyboardType="email-address"
        placeholder="you@example.com"
      />
      <Input
        label="Password"
        value={password}
        onChangeText={setPassword}
        secureTextEntry
        placeholder="At least 8 characters"
        error={error}
      />

      {info ? (
        <Text className="mb-3 text-success">{info}</Text>
      ) : null}

      <Button title="Sign up" loading={loading} onPress={submit} className="mt-2" />

      <View className="mt-6 flex-row justify-center">
        <Text muted>Already have an account? </Text>
        <Text className="text-primary" onPress={() => navigation.navigate('SignIn')}>
          Sign in
        </Text>
      </View>
    </Screen>
  );
}
