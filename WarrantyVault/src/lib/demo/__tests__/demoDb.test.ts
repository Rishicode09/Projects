import AsyncStorage from '@react-native-async-storage/async-storage';

import type { ProductDraft } from '@/types/models';

import { demoProducts, seedDemoData } from '../demoDb';

const draft: ProductDraft = {
  name: 'Test Item',
  brand: 'Acme',
  category: 'electronics',
  retailer: 'Shop',
  purchase_date: '2026-01-01',
  purchase_price: 100,
  warranty_expiry: '2027-01-01',
  return_expiry: '2026-01-31',
  receipt_url: null,
};

describe('demoProducts (offline data layer)', () => {
  beforeEach(async () => {
    await AsyncStorage.clear();
  });

  it('creates and lists products for a user', async () => {
    const created = await demoProducts.create('user-1', draft);
    expect(created.id).toBeTruthy();
    expect(created.user_id).toBe('user-1');

    const list = await demoProducts.list('user-1');
    expect(list).toHaveLength(1);
    expect(list[0]!.name).toBe('Test Item');
  });

  it('updates an existing product', async () => {
    const created = await demoProducts.create('user-1', draft);
    const updated = await demoProducts.update('user-1', created.id, { purchase_price: 250 });
    expect(updated?.purchase_price).toBe(250);
  });

  it('removes a product', async () => {
    const created = await demoProducts.create('user-1', draft);
    await demoProducts.remove('user-1', created.id);
    expect(await demoProducts.list('user-1')).toHaveLength(0);
  });

  it('isolates products by user', async () => {
    await demoProducts.create('user-1', draft);
    expect(await demoProducts.list('user-2')).toHaveLength(0);
  });

  it('seeds sample data once per user', async () => {
    await seedDemoData('user-1');
    const first = await demoProducts.list('user-1');
    expect(first.length).toBeGreaterThan(0);

    await seedDemoData('user-1'); // second call is a no-op
    const second = await demoProducts.list('user-1');
    expect(second).toHaveLength(first.length);
  });
});
