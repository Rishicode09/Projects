import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { Alert, ScrollView, View } from 'react-native';

import { Button, Card, Screen, Text } from '@/components/ui';
import { useAuthStore } from '@/features/auth/store/authStore';
import { daysUntil, formatDisplayDate } from '@/lib/date';
import { formatCurrency, titleCase } from '@/lib/format';
import type { MainStackParamList } from '@/core/navigation/types';

import { useProductStore } from '../store/productStore';

type Props = NativeStackScreenProps<MainStackParamList, 'ProductDetail'>;

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View className="flex-row justify-between border-b border-slate-100 py-3 dark:border-slate-700">
      <Text muted>{label}</Text>
      <Text className="font-medium">{value}</Text>
    </View>
  );
}

export function ProductDetailScreen({ navigation, route }: Props) {
  const userId = useAuthStore((s) => s.user?.id);
  const product = useProductStore((s) =>
    s.products.find((p) => p.id === route.params.productId)
  );
  const remove = useProductStore((s) => s.remove);

  if (!product) {
    return (
      <Screen className="justify-center">
        <Text className="text-center">Product not found.</Text>
      </Screen>
    );
  }

  const warrantyDays = product.warranty_expiry ? daysUntil(product.warranty_expiry) : null;

  function confirmDelete() {
    Alert.alert('Delete product', 'This cannot be undone.', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: async () => {
          if (userId && product) {
            await remove(product.id, userId);
            navigation.goBack();
          }
        },
      },
    ]);
  }

  return (
    <Screen padded={false}>
      <ScrollView contentContainerStyle={{ padding: 16 }}>
        <Text variant="title" className="mb-1">
          {product.name}
        </Text>
        <Text muted className="mb-4">
          {titleCase(product.category)}
        </Text>

        <Card className="mb-4">
          <Row label="Brand" value={product.brand ?? '—'} />
          <Row label="Retailer" value={product.retailer ?? '—'} />
          <Row label="Purchased" value={formatDisplayDate(product.purchase_date)} />
          <Row label="Price" value={formatCurrency(product.purchase_price)} />
          <Row label="Warranty until" value={formatDisplayDate(product.warranty_expiry)} />
          <Row label="Return until" value={formatDisplayDate(product.return_expiry)} />
          {warrantyDays !== null ? (
            <Row
              label="Warranty status"
              value={warrantyDays < 0 ? 'Expired' : `${warrantyDays} days left`}
            />
          ) : null}
        </Card>

        <Button
          title="File a warranty claim"
          onPress={() => navigation.navigate('ClaimAssistant', { productId: product.id })}
          className="mb-3"
        />
        <Button
          title="Edit"
          variant="secondary"
          onPress={() => navigation.navigate('ProductForm', { productId: product.id })}
          className="mb-3"
        />
        <Button title="Delete" variant="danger" onPress={confirmDelete} />
      </ScrollView>
    </Screen>
  );
}
