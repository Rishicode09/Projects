import { Pressable, View } from 'react-native';
import { styled } from 'nativewind';

import { Card, Text } from '@/components/ui';
import { daysUntil, formatDisplayDate } from '@/lib/date';
import { formatCurrency } from '@/lib/format';
import type { Product } from '@/types/models';

const StyledPressable = styled(Pressable);
const StyledView = styled(View);

interface Props {
  product: Product;
  onPress: (product: Product) => void;
}

/** Computes a human warranty status + the badge color class. */
function warrantyStatus(product: Product): { label: string; tone: string } {
  if (!product.warranty_expiry) return { label: 'No warranty', tone: 'text-slate-400' };
  const days = daysUntil(product.warranty_expiry);
  if (days < 0) return { label: 'Expired', tone: 'text-danger' };
  if (days <= 30) return { label: `${days}d left`, tone: 'text-warning' };
  return { label: 'Active', tone: 'text-success' };
}

export function ProductCard({ product, onPress }: Props) {
  const status = warrantyStatus(product);

  return (
    <StyledPressable
      accessibilityRole="button"
      accessibilityLabel={`${product.name}, ${status.label}`}
      onPress={() => onPress(product)}
      className="mb-3 active:opacity-70"
    >
      <Card>
        <StyledView className="flex-row items-start justify-between">
          <StyledView className="flex-1 pr-3">
            <Text variant="subtitle" numberOfLines={1}>
              {product.name}
            </Text>
            <Text variant="caption" muted numberOfLines={1}>
              {product.brand ? `${product.brand} · ` : ''}
              {product.retailer ?? 'Unknown retailer'}
            </Text>
          </StyledView>
          <Text variant="caption" className={`font-semibold ${status.tone}`}>
            {status.label}
          </Text>
        </StyledView>

        <StyledView className="mt-3 flex-row justify-between">
          <Text variant="caption" muted>
            {formatCurrency(product.purchase_price)}
          </Text>
          <Text variant="caption" muted>
            Warranty: {formatDisplayDate(product.warranty_expiry)}
          </Text>
        </StyledView>
      </Card>
    </StyledPressable>
  );
}
