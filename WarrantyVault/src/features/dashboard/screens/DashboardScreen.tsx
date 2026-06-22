import { RefreshControl, ScrollView, View } from 'react-native';

import { Card, Screen, Text } from '@/components/ui';
import { ProductCard } from '@/features/products/components/ProductCard';
import { formatCurrency } from '@/lib/format';
import type { DashboardScreenProps } from '@/app/navigation/types';

import { useDashboard } from '../hooks/useDashboard';

type Props = DashboardScreenProps;

function StatCard({ label, value, tone = '' }: { label: string; value: string; tone?: string }) {
  return (
    <Card className="mr-3 min-w-[150px] flex-1">
      <Text variant="caption" muted>
        {label}
      </Text>
      <Text variant="title" className={`mt-1 ${tone}`}>
        {value}
      </Text>
    </Card>
  );
}

export function DashboardScreen({ navigation }: Props) {
  const { stats, loading, reload } = useDashboard();

  return (
    <Screen padded={false}>
      <ScrollView
        contentContainerStyle={{ padding: 16, paddingBottom: 40 }}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={reload} />}
      >
        <Text variant="display" className="mb-4">
          Dashboard
        </Text>

        <View className="mb-3 flex-row">
          <StatCard label="Active warranties" value={String(stats.activeWarranties)} />
          <StatCard
            label="Expiring (30d)"
            value={String(stats.expiringSoon)}
            tone={stats.expiringSoon > 0 ? 'text-warning' : ''}
          />
        </View>
        <View className="mb-6 flex-row">
          <StatCard label="Protected value" value={formatCurrency(stats.totalProtectedValue)} />
          <StatCard
            label="Est. savings"
            value={formatCurrency(stats.savingsEstimate)}
            tone="text-success"
          />
        </View>

        <Text variant="subtitle" className="mb-3">
          Recent additions
        </Text>
        {stats.recentAdditions.length === 0 ? (
          <Text muted>Nothing here yet. Add a receipt to get started.</Text>
        ) : (
          stats.recentAdditions.map((product) => (
            <ProductCard
              key={product.id}
              product={product}
              onPress={(p) => navigation.navigate('ProductDetail', { productId: p.id })}
            />
          ))
        )}
      </ScrollView>
    </Screen>
  );
}
