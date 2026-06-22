import { cache, cacheKeys } from '@/lib/cache';
import { appError, err, ok, type Result } from '@/lib/result';
import { supabase } from '@/lib/supabase';
import { productDraftSchema, productUpdateSchema } from '@/schemas/product.schema';
import type { Product, ProductDraft, ProductUpdate } from '@/types/models';

const TABLE = 'products';

/**
 * Data-access for products. Offline-first: `list` returns cached data
 * immediately when the network fails, and successful network reads refresh the
 * cache. All writes validate input with Zod before hitting the database.
 */
export class ProductRepository {
  async list(userId: string): Promise<Result<Product[]>> {
    const { data, error } = await supabase
      .from(TABLE)
      .select('*')
      .eq('user_id', userId)
      .order('created_at', { ascending: false });

    if (error) {
      const cached = await cache.get<Product[]>(cacheKeys.products(userId));
      if (cached) return ok(cached);
      return err(appError('products/list-failed', error.message, error));
    }

    const products = (data ?? []) as Product[];
    await cache.set(cacheKeys.products(userId), products);
    return ok(products);
  }

  async getById(id: string): Promise<Result<Product>> {
    const { data, error } = await supabase.from(TABLE).select('*').eq('id', id).single();
    if (error || !data) {
      return err(appError('products/not-found', error?.message ?? 'Product not found'));
    }
    return ok(data as Product);
  }

  async create(userId: string, draft: ProductDraft): Promise<Result<Product>> {
    const parsed = productDraftSchema.safeParse(draft);
    if (!parsed.success) {
      return err(appError('products/invalid', parsed.error.issues[0]?.message ?? 'Invalid product'));
    }

    const { data, error } = await supabase
      .from(TABLE)
      .insert({ ...parsed.data, user_id: userId })
      .select('*')
      .single();

    if (error || !data) {
      return err(appError('products/create-failed', error?.message ?? 'Could not create product'));
    }
    await this.invalidate(userId);
    return ok(data as Product);
  }

  async update(id: string, patch: ProductUpdate): Promise<Result<Product>> {
    const parsed = productUpdateSchema.safeParse(patch);
    if (!parsed.success) {
      return err(appError('products/invalid', parsed.error.issues[0]?.message ?? 'Invalid update'));
    }

    const { data, error } = await supabase
      .from(TABLE)
      .update({ ...parsed.data, updated_at: new Date().toISOString() })
      .eq('id', id)
      .select('*')
      .single();

    if (error || !data) {
      return err(appError('products/update-failed', error?.message ?? 'Could not update product'));
    }
    const product = data as Product;
    await this.invalidate(product.user_id);
    return ok(product);
  }

  async remove(id: string, userId: string): Promise<Result<void>> {
    const { error } = await supabase.from(TABLE).delete().eq('id', id);
    if (error) return err(appError('products/delete-failed', error.message, error));
    await this.invalidate(userId);
    return ok(undefined);
  }

  private async invalidate(userId: string): Promise<void> {
    await cache.remove(cacheKeys.products(userId));
  }
}

export const productRepository = new ProductRepository();
