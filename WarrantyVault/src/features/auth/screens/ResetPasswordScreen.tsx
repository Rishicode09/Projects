import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { View } from 'react-native';

import { Button, Input, Screen, Text } from '@/components/ui';
import type { AuthStackParamList } from '@/app/navigation/types';

import { useAuthForm } from '../hooks/useAuthForm';

type Props = NativeStackScreenProps<AuthStackParamList, 'ResetPassword'>;

export function ResetPasswordScreen({ navigation }: Props) {
  const { email, setEmail, loading, error, info, submit } = useAuthForm('reset');

  return (
    <Screen className="justify-center">
      <Text variant="display" className="mb-1">
        Reset password
      </Text>
      <Text muted className="mb-8">
        We&apos;ll email you a secure link to set a new password.
      </Text>

      <Input
        label="Email"
        value={email}
        onChangeText={setEmail}
        autoCapitalize="none"
        keyboardType="email-address"
        placeholder="you@example.com"
        error={error}
      />

      {info ? <Text className="mb-3 text-success">{info}</Text> : null}

      <Button title="Send reset link" loading={loading} onPress={submit} className="mt-2" />

      <View className="mt-6 flex-row justify-center">
        <Text className="text-primary" onPress={() => navigation.navigate('SignIn')}>
          Back to sign in
        </Text>
      </View>
    </Screen>
  );
}
