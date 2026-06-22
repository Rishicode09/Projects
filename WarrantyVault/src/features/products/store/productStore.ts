import { create } from 'zustand';

import { notificationService } from '@/services/notifications/NotificationService';
import { productRepository } from '@/repositories/ProductRepository';
import { settingsRepository } from '@/repositories/SettingsRepository';
import type { Product, ProductDraft, ProductUpdate } from '@/types/models';

interface ProductState {
  products: Product[];
  loading: boolean;
  error: string | null;
  load: (userId: string) => Promise<void>;
  add: (userId: string, draft: ProductDraft) => Promise<Product | null>;
  edit: (id: string, patch: ProductUpdate) => Promise<Product | null>;
  remove: (id: string, userId: string) => Promise<void>;
}

/**
 * Source of truth for the product list in the UI. Wraps the repository and, on
 * mutations, (re)schedules notifications according to the user's preferences.
 */
export const useProductStore = create<ProductState>((set, get) => ({
  products: [],
  loading: false,
  error: null,

  load: async (userId) => {
    set({ loading: true, error: null });
    const result = await productRepository.list(userId);
    if (result.ok) {
      set({ products: result.value, loading: false });
    } else {
      set({ error: result.error.message, loading: false });
    }
  },

  add: async (userId, draft) => {
    const result = await productRepository.create(userId, draft);
    if (!result.ok) {
      set({ error: result.error.message });
      return null;
    }
    const product = result.value;
    set({ products: [product, ...get().products] });
    await scheduleReminders(userId, product);
    return product;
  },

  edit: async (id, patch) => {
    const result = await productRepository.update(id, patch);
    if (!result.ok) {
      set({ error: result.error.message });
      return null;
    }
    const updated = result.value;
    set({ products: get().products.map((p) => (p.id === id ? updated : p)) });
    await scheduleReminders(updated.user_id, updated);
    return updated;
  },

  remove: async (id, userId) => {
    set({ products: get().products.filter((p) => p.id !== id) });
    await productRepository.remove(id, userId);
  },
}));

async function scheduleReminders(userId: string, product: Product): Promise<void> {
  const settings = await settingsRepository.get(userId);
  if (!settings.ok) return;
  await notificationService.scheduleForProduct(product, settings.value.notifications);
}
