import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useMemo, useState } from 'react';
import { ScrollView } from 'react-native';

import { Button, Input, Screen, Text } from '@/components/ui';
import { useAuthStore } from '@/features/auth/store/authStore';
import { productDraftSchema } from '@/schemas/product.schema';
import type { MainStackParamList } from '@/core/navigation/types';
import type { ProductDraft } from '@/types/models';

import { useProductStore } from '../store/productStore';

type Props = NativeStackScreenProps<MainStackParamList, 'ProductForm'>;

const EMPTY: ProductDraft = {
  name: '',
  brand: null,
  category: 'other',
  retailer: null,
  purchase_date: new Date().toISOString().slice(0, 10),
  purchase_price: 0,
  warranty_expiry: null,
  return_expiry: null,
  receipt_url: null,
};

export function ProductFormScreen({ navigation, route }: Props) {
  const userId = useAuthStore((s) => s.user?.id);
  const { add, edit, products } = useProductStore();

  const existing = useMemo(
    () => products.find((p) => p.id === route.params?.productId),
    [products, route.params?.productId]
  );

  const [draft, setDraft] = useState<ProductDraft>(
    route.params?.draft ?? (existing ? toDraft(existing) : EMPTY)
  );
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

  function set<K extends keyof ProductDraft>(key: K, value: ProductDraft[K]) {
    setDraft((d) => ({ ...d, [key]: value }));
  }

  async function onSave() {
    const parsed = productDraftSchema.safeParse(draft);
    if (!parsed.success) {
      const next: Record<string, string> = {};
      for (const issue of parsed.error.issues) next[String(issue.path[0])] = issue.message;
      setErrors(next);
      return;
    }
    if (!userId) return;
    setErrors({});
    setSaving(true);
    const result = existing
      ? await edit(existing.id, parsed.data)
      : await add(userId, parsed.data);
    setSaving(false);
    if (result) navigation.goBack();
  }

  return (
    <Screen padded={false}>
      <ScrollView contentContainerStyle={{ padding: 16 }}>
        <Text variant="title" className="mb-4">
          {existing ? 'Edit product' : 'New product'}
        </Text>

        <Input label="Name" value={draft.name} onChangeText={(v) => set('name', v)} error={errors.name} />
        <Input label="Brand" value={draft.brand ?? ''} onChangeText={(v) => set('brand', v || null)} />
        <Input
          label="Retailer"
          value={draft.retailer ?? ''}
          onChangeText={(v) => set('retailer', v || null)}
        />
        <Input
          label="Purchase date (YYYY-MM-DD)"
          value={draft.purchase_date}
          onChangeText={(v) => set('purchase_date', v)}
          error={errors.purchase_date}
        />
        <Input
          label="Purchase price"
          keyboardType="decimal-pad"
          value={String(draft.purchase_price)}
          onChangeText={(v) => set('purchase_price', Number(v) || 0)}
          error={errors.purchase_price}
        />
        <Input
          label="Warranty expiry (YYYY-MM-DD)"
          value={draft.warranty_expiry ?? ''}
          onChangeText={(v) => set('warranty_expiry', v || null)}
          error={errors.warranty_expiry}
        />
        <Input
          label="Return deadline (YYYY-MM-DD)"
          value={draft.return_expiry ?? ''}
          onChangeText={(v) => set('return_expiry', v || null)}
          error={errors.return_expiry}
        />

        <Button title="Save" loading={saving} onPress={onSave} className="mt-2" />
      </ScrollView>
    </Screen>
  );
}

function toDraft(p: ProductDraft): ProductDraft {
  return {
    name: p.name,
    brand: p.brand,
    category: p.category,
    retailer: p.retailer,
    purchase_date: p.purchase_date,
    purchase_price: p.purchase_price,
    warranty_expiry: p.warranty_expiry,
    return_expiry: p.return_expiry,
    receipt_url: p.receipt_url,
  };
}
