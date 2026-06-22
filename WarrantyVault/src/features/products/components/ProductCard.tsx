import { Pressable, View } from 'react-native';
import Animated, { FadeInDown } from 'react-native-reanimated';

import { Card, Text } from '@/components/ui';
import { daysUntil, formatDisplayDate } from '@/lib/date';
import { formatCurrency } from '@/lib/format';
import type { Product } from '@/types/models';

interface Props {
  product: Product;
  onPress: (product: Product) => void;
  /** Stagger index for the entrance animation. */
  index?: number;
}

/** Computes a human warranty status + the badge color class. */
function warrantyStatus(product: Product): { label: string; tone: string; dot: string } {
  if (!product.warranty_expiry)
    return { label: 'No warranty', tone: 'text-slate-400', dot: 'bg-slate-500' };
  const days = daysUntil(product.warranty_expiry);
  if (days < 0) return { label: 'Expired', tone: 'text-danger', dot: 'bg-danger' };
  if (days <= 30) return { label: `${days}d left`, tone: 'text-warning', dot: 'bg-warning' };
  return { label: 'Active', tone: 'text-success', dot: 'bg-success' };
}

export function ProductCard({ product, onPress, index = 0 }: Props) {
  const status = warrantyStatus(product);

  return (
    <Animated.View entering={FadeInDown.duration(450).delay(index * 70).springify()}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={`${product.name}, ${status.label}`}
        onPress={() => onPress(product)}
        className="mb-3 active:opacity-80"
      >
        <Card>
          <View className="flex-row items-start justify-between">
            <View className="flex-1 pr-3">
              <Text variant="subtitle" numberOfLines={1}>
                {product.name}
              </Text>
              <Text variant="caption" muted numberOfLines={1}>
                {product.brand ? `${product.brand} · ` : ''}
                {product.retailer ?? 'Unknown retailer'}
              </Text>
            </View>
            <View className="flex-row items-center">
              <View className={`mr-1.5 h-2 w-2 rounded-full ${status.dot}`} />
              <Text variant="caption" className={`font-semibold ${status.tone}`}>
                {status.label}
              </Text>
            </View>
          </View>

          <View className="mt-3 flex-row justify-between">
            <Text variant="caption" muted>
              {formatCurrency(product.purchase_price)}
            </Text>
            <Text variant="caption" muted>
              Warranty: {formatDisplayDate(product.warranty_expiry)}
            </Text>
          </View>
        </Card>
      </Pressable>
    </Animated.View>
  );
}
