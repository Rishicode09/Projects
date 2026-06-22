import { FlatList, RefreshControl, View } from 'react-native';

import { Button, Screen, Text } from '@/components/ui';
import type { ProductsScreenProps } from '@/core/navigation/types';

import { ProductCard } from '../components/ProductCard';
import { useProducts } from '../hooks/useProducts';

type Props = ProductsScreenProps;

export function ProductListScreen({ navigation }: Props) {
  const { products, loading, error, reload } = useProducts();

  return (
    <Screen padded={false}>
      <View className="flex-row items-center justify-between px-4 pb-2 pt-2">
        <Text variant="title">My Products</Text>
        <Button
          title="+ Add"
          variant="ghost"
          onPress={() => navigation.navigate('AddReceipt')}
          className="min-h-[40px] px-4"
        />
      </View>

      {error ? (
        <Text className="px-4 text-danger">{error}</Text>
      ) : null}

      <FlatList
        data={products}
        keyExtractor={(item) => item.id}
        contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 32 }}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={reload} />}
        renderItem={({ item, index }) => (
          <ProductCard
            product={item}
            index={index}
            onPress={(p) => navigation.navigate('ProductDetail', { productId: p.id })}
          />
        )}
        ListEmptyComponent={
          loading ? null : (
            <View className="mt-24 items-center px-8">
              <Text variant="subtitle" className="mb-2 text-center">
                No products yet
              </Text>
              <Text muted className="mb-6 text-center">
                Snap a receipt and we&apos;ll track the warranty for you.
              </Text>
              <Button title="Add your first receipt" onPress={() => navigation.navigate('AddReceipt')} />
            </View>
          )
        }
      />
    </Screen>
  );
}
