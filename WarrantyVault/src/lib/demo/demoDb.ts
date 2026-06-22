import AsyncStorage from '@react-native-async-storage/async-storage';

import { addDays, addMonths, toIsoDate } from '@/lib/date';
import { uid } from '@/lib/id';
import type {
  NotificationPreferences,
  Product,
  ProductDraft,
  ProductUpdate,
  UserSettings,
} from '@/types/models';

// Inlined (rather than imported from SettingsRepository) to avoid a circular
// import, since SettingsRepository delegates to demoSettings below.
const DEMO_NOTIFICATION_PREFS: NotificationPreferences = {
  warranty_30_day: true,
  warranty_7_day: true,
  return_1_day: true,
};

/**
 * Local, AsyncStorage-backed data layer used when Supabase isn't configured.
 * Mirrors the repository surface so ProductRepository / SettingsRepository can
 * delegate to it transparently in demo mode.
 */
const productsKey = (userId: string) => `demo:db:products:${userId}`;
const settingsKey = (userId: string) => `demo:db:settings:${userId}`;
const seededKey = (userId: string) => `demo:db:seeded:${userId}`;

async function readProducts(userId: string): Promise<Product[]> {
  const raw = await AsyncStorage.getItem(productsKey(userId));
  return raw ? (JSON.parse(raw) as Product[]) : [];
}

async function writeProducts(userId: string, products: Product[]): Promise<void> {
  await AsyncStorage.setItem(productsKey(userId), JSON.stringify(products));
}

export const demoProducts = {
  list: readProducts,

  async getById(userId: string, id: string): Promise<Product | null> {
    const products = await readProducts(userId);
    return products.find((p) => p.id === id) ?? null;
  },

  async create(userId: string, draft: ProductDraft): Promise<Product> {
    const now = new Date().toISOString();
    const product: Product = {
      ...draft,
      id: uid(),
      user_id: userId,
      created_at: now,
      updated_at: now,
    };
    const products = await readProducts(userId);
    await writeProducts(userId, [product, ...products]);
    return product;
  },

  async update(userId: string, id: string, patch: ProductUpdate): Promise<Product | null> {
    const products = await readProducts(userId);
    const index = products.findIndex((p) => p.id === id);
    if (index < 0) return null;
    const updated: Product = {
      ...products[index]!,
      ...patch,
      updated_at: new Date().toISOString(),
    };
    products[index] = updated;
    await writeProducts(userId, products);
    return updated;
  },

  async remove(userId: string, id: string): Promise<void> {
    const products = await readProducts(userId);
    await writeProducts(
      userId,
      products.filter((p) => p.id !== id)
    );
  },
};

export const demoSettings = {
  async get(userId: string): Promise<UserSettings> {
    const raw = await AsyncStorage.getItem(settingsKey(userId));
    if (raw) return JSON.parse(raw) as UserSettings;
    return {
      user_id: userId,
      notifications: DEMO_NOTIFICATION_PREFS,
      is_premium: false,
      analytics_opt_in: false,
      updated_at: new Date().toISOString(),
    };
  },

  async upsert(settings: UserSettings): Promise<UserSettings> {
    const saved = { ...settings, updated_at: new Date().toISOString() };
    await AsyncStorage.setItem(settingsKey(settings.user_id), JSON.stringify(saved));
    return saved;
  },
};

/** Seeds a couple of sample products for a freshly created demo account. */
export async function seedDemoData(userId: string): Promise<void> {
  if (await AsyncStorage.getItem(seededKey(userId))) return;
  const today = toIsoDate(new Date());

  const samples: ProductDraft[] = [
    {
      name: 'Sony WH-1000XM5 Headphones',
      brand: 'Sony',
      category: 'electronics',
      retailer: 'Best Buy',
      purchase_date: addDays(today, -40),
      purchase_price: 399.99,
      warranty_expiry: addMonths(today, 22),
      return_expiry: addDays(today, -10),
      receipt_url: null,
    },
    {
      name: 'Dyson V15 Vacuum',
      brand: 'Dyson',
      category: 'appliances',
      retailer: 'Dyson.com',
      purchase_date: addDays(today, -15),
      purchase_price: 749.0,
      warranty_expiry: addDays(today, 20),
      return_expiry: addDays(today, 15),
      receipt_url: null,
    },
  ];

  for (const draft of samples) {
    await demoProducts.create(userId, draft);
  }
  await AsyncStorage.setItem(seededKey(userId), '1');
}
