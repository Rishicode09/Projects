import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { View } from 'react-native';

import { Button, Card, Screen, Text } from '@/components/ui';
import type { MainStackParamList } from '@/app/navigation/types';

import { useReceiptUpload } from '../hooks/useReceiptUpload';

type Props = NativeStackScreenProps<MainStackParamList, 'AddReceipt'>;

const PHASE_LABEL: Record<string, string> = {
  uploading: 'Uploading receipt…',
  processing: 'Reading receipt with AI…',
};

export function AddReceiptScreen({ navigation }: Props) {
  const { phase, error, pickImage, pickDocument, process } = useReceiptUpload();
  const busy = phase === 'uploading' || phase === 'processing';

  async function handle(pick: () => Promise<{ uri: string; mimeType: string } | null>) {
    const source = await pick();
    if (!source) return;
    const result = await process(source);
    if (result) {
      // Hand the AI-extracted draft to the form for review/confirmation.
      navigation.replace('ProductForm', { draft: result.draft });
    }
  }

  return (
    <Screen className="justify-center">
      <Text variant="title" className="mb-1">
        Add a receipt
      </Text>
      <Text muted className="mb-6">
        Upload a photo, screenshot, or PDF. We&apos;ll extract the details
        automatically and you can review them before saving.
      </Text>

      <Card className="mb-6">
        <Button
          title="Choose photo / screenshot"
          onPress={() => handle(pickImage)}
          loading={busy}
          className="mb-3"
        />
        <Button
          title="Choose PDF / file"
          variant="secondary"
          onPress={() => handle(pickDocument)}
          loading={busy}
        />
      </Card>

      {busy ? (
        <View className="items-center">
          <Text muted>{PHASE_LABEL[phase]}</Text>
        </View>
      ) : null}

      {error ? <Text className="text-center text-danger">{error}</Text> : null}

      <Button
        title="Enter manually instead"
        variant="ghost"
        onPress={() => navigation.replace('ProductForm', {})}
        className="mt-6"
      />
    </Screen>
  );
}
