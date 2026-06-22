import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';

import { ClaimAssistantScreen } from '@/features/claims/screens/ClaimAssistantScreen';
import { DashboardScreen } from '@/features/dashboard/screens/DashboardScreen';
import { ProductDetailScreen } from '@/features/products/screens/ProductDetailScreen';
import { ProductFormScreen } from '@/features/products/screens/ProductFormScreen';
import { ProductListScreen } from '@/features/products/screens/ProductListScreen';
import { AddReceiptScreen } from '@/features/receipts/screens/AddReceiptScreen';
import { SettingsScreen } from '@/features/settings/screens/SettingsScreen';
import { useTheme } from '@/lib/theme/ThemeProvider';

import type { MainStackParamList, TabParamList } from './types';

const Tab = createBottomTabNavigator<TabParamList>();
const Stack = createNativeStackNavigator<MainStackParamList>();

function Tabs() {
  const { colors } = useTheme();
  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarStyle: { backgroundColor: colors.surface, borderTopColor: colors.border },
      }}
    >
      <Tab.Screen
        name="DashboardTab"
        component={DashboardScreen}
        options={{ title: 'Home' }}
      />
      <Tab.Screen
        name="ProductsTab"
        component={ProductListScreen}
        options={{ title: 'Products' }}
      />
      <Tab.Screen
        name="SettingsTab"
        component={SettingsScreen}
        options={{ title: 'Settings' }}
      />
    </Tab.Navigator>
  );
}

export function MainNavigator() {
  const { colors } = useTheme();
  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: colors.surface },
        headerTintColor: colors.text,
        headerShadowVisible: false,
      }}
    >
      <Stack.Screen name="Tabs" component={Tabs} options={{ headerShown: false }} />
      <Stack.Screen name="ProductDetail" component={ProductDetailScreen} options={{ title: 'Details' }} />
      <Stack.Screen name="ProductForm" component={ProductFormScreen} options={{ title: 'Product' }} />
      <Stack.Screen name="AddReceipt" component={AddReceiptScreen} options={{ title: 'Add receipt' }} />
      <Stack.Screen name="ClaimAssistant" component={ClaimAssistantScreen} options={{ title: 'Claim' }} />
    </Stack.Navigator>
  );
}
