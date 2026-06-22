import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import * as Clipboard from 'expo-clipboard';
import { useMemo, useState } from 'react';
import { Alert, ScrollView, Share, View } from 'react-native';

import { Button, Card, Input, Screen, Text } from '@/components/ui';
import { useAuthStore } from '@/features/auth/store/authStore';
import { useProductStore } from '@/features/products/store/productStore';
import { claimTemplateService, type ClaimTone } from '@/services/claims/ClaimTemplateService';
import type { MainStackParamList } from '@/app/navigation/types';

type Props = NativeStackScreenProps<MainStackParamList, 'ClaimAssistant'>;

export function ClaimAssistantScreen({ route }: Props) {
  const product = useProductStore((s) =>
    s.products.find((p) => p.id === route.params.productId)
  );
  const userEmail = useAuthStore((s) => s.user?.email ?? 'A valued customer');

  const [name, setName] = useState(userEmail);
  const [issue, setIssue] = useState('');
  const [tone, setTone] = useState<ClaimTone>('standard');

  const letter = useMemo(() => {
    if (!product) return '';
    return claimTemplateService.generate({
      product,
      customerName: name,
      issueDescription: issue || 'The product has developed a fault during normal use.',
      tone,
    });
  }, [product, name, issue, tone]);

  if (!product) {
    return (
      <Screen className="justify-center">
        <Text className="text-center">Product not found.</Text>
      </Screen>
    );
  }

  async function copy() {
    await Clipboard.setStringAsync(letter);
    Alert.alert('Copied', 'The claim letter is on your clipboard.');
  }

  async function share() {
    await Share.share({ message: letter });
  }

  return (
    <Screen padded={false}>
      <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 40 }}>
        <Text variant="title" className="mb-1">
          Claim assistant
        </Text>
        <Text muted className="mb-4">
          Generate a ready-to-send warranty claim for {product.name}.
        </Text>

        <Input label="Your name" value={name} onChangeText={setName} />
        <Input
          label="Describe the issue"
          value={issue}
          onChangeText={setIssue}
          multiline
          numberOfLines={3}
          placeholder="e.g. The screen flickers intermittently after 4 months of use."
        />

        <View className="mb-4 flex-row">
          <Button
            title="Standard"
            variant={tone === 'standard' ? 'primary' : 'ghost'}
            onPress={() => setTone('standard')}
            className="mr-2 flex-1"
          />
          <Button
            title="Firm"
            variant={tone === 'firm' ? 'primary' : 'ghost'}
            onPress={() => setTone('firm')}
            className="flex-1"
          />
        </View>

        <Card className="mb-4">
          <Text variant="caption" className="leading-5">
            {letter}
          </Text>
        </Card>

        <Button title="Copy to clipboard" onPress={copy} className="mb-3" />
        <Button title="Share" variant="secondary" onPress={share} />
      </ScrollView>
    </Screen>
  );
}
