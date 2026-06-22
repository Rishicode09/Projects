import AsyncStorage from '@react-native-async-storage/async-storage';

/**
 * Tiny JSON cache over AsyncStorage backing the offline-first strategy:
 * repositories read from cache first, then revalidate against the network and
 * write fresh data back.
 */
export const cache = {
  async get<T>(key: string): Promise<T | null> {
    try {
      const raw = await AsyncStorage.getItem(key);
      return raw ? (JSON.parse(raw) as T) : null;
    } catch {
      return null;
    }
  },

  async set<T>(key: string, value: T): Promise<void> {
    try {
      await AsyncStorage.setItem(key, JSON.stringify(value));
    } catch {
      // Cache writes are best-effort; ignore quota/serialization failures.
    }
  },

  async remove(key: string): Promise<void> {
    try {
      await AsyncStorage.removeItem(key);
    } catch {
      /* noop */
    }
  },
};

export const cacheKeys = {
  products: (userId: string) => `cache:products:${userId}`,
  settings: (userId: string) => `cache:settings:${userId}`,
};
