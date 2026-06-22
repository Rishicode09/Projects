/**
 * Domain models. These mirror the Postgres schema (see supabase/migrations).
 * Keep field names in snake_case to match the database rows returned by
 * supabase-js, avoiding a mapping layer in the repositories.
 */

export type ProductCategory =
  | 'electronics'
  | 'appliances'
  | 'furniture'
  | 'tools'
  | 'clothing'
  | 'automotive'
  | 'other';

export interface Product {
  id: string;
  user_id: string;
  name: string;
  brand: string | null;
  category: ProductCategory;
  retailer: string | null;
  purchase_date: string; // ISO date (YYYY-MM-DD)
  purchase_price: number;
  warranty_expiry: string | null; // ISO date
  return_expiry: string | null; // ISO date
  receipt_url: string | null;
  created_at: string;
  updated_at: string;
}

/** Fields the user/AI supplies when creating a product. */
export type ProductDraft = Omit<
  Product,
  'id' | 'user_id' | 'created_at' | 'updated_at'
>;

export type ProductUpdate = Partial<ProductDraft>;

export interface NotificationPreferences {
  warranty_30_day: boolean;
  warranty_7_day: boolean;
  return_1_day: boolean;
}

export interface UserSettings {
  user_id: string;
  notifications: NotificationPreferences;
  is_premium: boolean;
  analytics_opt_in: boolean;
  updated_at: string;
}

/** Structured result produced by the OCR / AI receipt processing pipeline. */
export interface ExtractedLineItem {
  name: string;
  price: number | null;
}

export interface ExtractedReceipt {
  retailer: string | null;
  purchase_date: string | null; // ISO date
  items: ExtractedLineItem[];
  total_amount: number | null;
  warranty_months: number | null;
  warranty_text: string | null;
  /** 0..1 confidence reported by the OCR provider. */
  confidence: number;
}

export interface DashboardStats {
  activeWarranties: number;
  expiringSoon: number; // within 30 days
  totalProtectedValue: number;
  recentAdditions: Product[];
  savingsEstimate: number;
}
