import type { BottomTabScreenProps } from '@react-navigation/bottom-tabs';
import type { CompositeScreenProps } from '@react-navigation/native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import type { ProductDraft } from '@/types/models';

export type AuthStackParamList = {
  SignIn: undefined;
  SignUp: undefined;
  ResetPassword: undefined;
};

/**
 * Main stack. The tab navigator is nested under `Tabs`; screens reachable from
 * any tab (detail, forms, claim) live at the stack level so they push over tabs.
 */
export type MainStackParamList = {
  Tabs: undefined;
  ProductDetail: { productId: string };
  ProductForm: { productId?: string; draft?: ProductDraft };
  AddReceipt: undefined;
  ClaimAssistant: { productId: string };
};

export type TabParamList = {
  DashboardTab: undefined;
  ProductsTab: undefined;
  SettingsTab: undefined;
};

/**
 * Tab screens live inside the stack, so they can navigate to both tab routes
 * and the parent stack routes — modeled with CompositeScreenProps.
 */
export type DashboardScreenProps = CompositeScreenProps<
  BottomTabScreenProps<TabParamList, 'DashboardTab'>,
  NativeStackScreenProps<MainStackParamList>
>;

export type ProductsScreenProps = CompositeScreenProps<
  BottomTabScreenProps<TabParamList, 'ProductsTab'>,
  NativeStackScreenProps<MainStackParamList>
>;
