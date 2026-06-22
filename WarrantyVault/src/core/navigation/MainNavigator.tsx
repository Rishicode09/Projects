import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';

import { ClaimAssistantScreen } from '@/features/claims/screens/ClaimAssistantScreen';
import { DashboardScreen } from '@/features/dashboard/screens/DashboardScreen';
import { ProductDetailScreen } from '@/features/products/screens/ProductDetailScreen';
import { ProductFormScreen } from '@/features/products/screens/ProductFormScreen';
import { ProductListScreen } from '@/features/products/screens/ProductListScreen';
import { AddReceiptScreen } from '@/features/receipts/screens/AddReceiptScreen';
import { SettingsScreen } from '@/features/settings/screens/SettingsScreen';

import type { MainStackParamList, TabParamList } from './types';

const Tab = createBottomTabNavigator<TabParamList>();
const Stack = createNativeStackNavigator<MainStackParamList>();

// Dark, vibrant chrome to match the animated background.
const CHROME = {
  surface: 'rgba(15,23,42,0.92)',
  border: 'rgba(255,255,255,0.08)',
  active: '#C4B5FD',
  inactive: '#64748B',
  text: '#F8FAFC',
};

function Tabs() {
  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: CHROME.active,
        tabBarInactiveTintColor: CHROME.inactive,
        tabBarStyle: {
          position: 'absolute',
          backgroundColor: CHROME.surface,
          borderTopColor: CHROME.border,
        },
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
  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: CHROME.surface },
        headerTintColor: CHROME.text,
        headerShadowVisible: false,
        contentStyle: { backgroundColor: 'transparent' },
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
