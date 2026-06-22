import { LinearGradient } from 'expo-linear-gradient';
import { RefreshControl, ScrollView, View } from 'react-native';
import Animated, { FadeInDown } from 'react-native-reanimated';

import { Screen, Text } from '@/components/ui';
import { ProductCard } from '@/features/products/components/ProductCard';
import { formatCurrency } from '@/lib/format';
import type { DashboardScreenProps } from '@/core/navigation/types';

import { useDashboard } from '../hooks/useDashboard';

type Props = DashboardScreenProps;

interface StatProps {
  label: string;
  value: string;
  colors: [string, string, ...string[]];
  delay: number;
}

function StatCard({ label, value, colors, delay }: StatProps) {
  return (
    <Animated.View
      entering={FadeInDown.duration(500).delay(delay).springify()}
      className="mr-3 flex-1 overflow-hidden rounded-3xl"
    >
      <LinearGradient colors={colors} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={{ padding: 16 }}>
        <Text variant="caption" className="text-white/80">
          {label}
        </Text>
        <Text variant="title" className="mt-1 text-white">
          {value}
        </Text>
      </LinearGradient>
    </Animated.View>
  );
}

export function DashboardScreen({ navigation }: Props) {
  const { stats, loading, reload } = useDashboard();

  return (
    <Screen padded={false}>
      <ScrollView
        contentContainerStyle={{ padding: 16, paddingBottom: 40 }}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={reload} tintColor="#fff" />}
      >
        <Animated.View entering={FadeInDown.duration(500)}>
          <Text variant="caption" muted>
            Welcome back 👋
          </Text>
          <Text variant="display" className="mb-5">
            Dashboard
          </Text>
        </Animated.View>

        <View className="mb-3 flex-row">
          <StatCard
            label="Active warranties"
            value={String(stats.activeWarranties)}
            colors={['#6366F1', '#8B5CF6']}
            delay={80}
          />
          <StatCard
            label="Expiring (30d)"
            value={String(stats.expiringSoon)}
            colors={['#F59E0B', '#EF4444']}
            delay={140}
          />
        </View>
        <View className="mb-7 flex-row">
          <StatCard
            label="Protected value"
            value={formatCurrency(stats.totalProtectedValue)}
            colors={['#0EA5E9', '#22D3EE']}
            delay={200}
          />
          <StatCard
            label="Est. savings"
            value={formatCurrency(stats.savingsEstimate)}
            colors={['#10B981', '#34D399']}
            delay={260}
          />
        </View>

        <Text variant="subtitle" className="mb-3">
          Recent additions
        </Text>
        {stats.recentAdditions.length === 0 ? (
          <Text muted>Nothing here yet. Add a receipt to get started.</Text>
        ) : (
          stats.recentAdditions.map((product, i) => (
            <ProductCard
              key={product.id}
              product={product}
              index={i}
              onPress={(p) => navigation.navigate('ProductDetail', { productId: p.id })}
            />
          ))
        )}
      </ScrollView>
    </Screen>
  );
}
