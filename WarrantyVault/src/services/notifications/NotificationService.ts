import * as Notifications from 'expo-notifications';

import { daysUntil, parseIsoDate } from '@/lib/date';
import type { NotificationPreferences, Product } from '@/types/models';

export interface ScheduledReminder {
  id: string;
  productId: string;
  kind: ReminderKind;
  fireDate: string; // ISO date
}

export type ReminderKind = 'warranty_30_day' | 'warranty_7_day' | 'return_1_day';

interface ReminderPlan {
  kind: ReminderKind;
  /** Target date the reminder fires on (ISO). */
  fireDate: string;
  title: string;
  body: string;
}

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

/**
 * Schedules local push notifications for warranty/return deadlines. The service
 * computes a plan from a product + preferences, then schedules only the
 * reminders that are still in the future and enabled.
 */
export class NotificationService {
  async requestPermissions(): Promise<boolean> {
    const { granted } = await Notifications.getPermissionsAsync();
    if (granted) return true;
    const res = await Notifications.requestPermissionsAsync();
    return res.granted;
  }

  /** Builds the reminder plan for a product (pure — easy to unit test). */
  buildPlan(product: Product, prefs: NotificationPreferences): ReminderPlan[] {
    const plans: ReminderPlan[] = [];
    const label = product.name;

    if (product.warranty_expiry) {
      if (prefs.warranty_30_day) {
        plans.push({
          kind: 'warranty_30_day',
          fireDate: shift(product.warranty_expiry, -30),
          title: 'Warranty expiring soon',
          body: `${label} warranty expires in 30 days.`,
        });
      }
      if (prefs.warranty_7_day) {
        plans.push({
          kind: 'warranty_7_day',
          fireDate: shift(product.warranty_expiry, -7),
          title: 'Warranty expiring this week',
          body: `${label} warranty expires in 7 days.`,
        });
      }
    }

    if (product.return_expiry && prefs.return_1_day) {
      plans.push({
        kind: 'return_1_day',
        fireDate: shift(product.return_expiry, -1),
        title: 'Return window closing',
        body: `Tomorrow is the last day to return ${label}.`,
      });
    }

    // Only keep reminders that fire today or later.
    return plans.filter((p) => daysUntil(p.fireDate) >= 0);
  }

  async scheduleForProduct(
    product: Product,
    prefs: NotificationPreferences
  ): Promise<ScheduledReminder[]> {
    if (!(await this.requestPermissions())) return [];

    const plans = this.buildPlan(product, prefs);
    const scheduled: ScheduledReminder[] = [];

    for (const plan of plans) {
      const trigger = parseIsoDate(plan.fireDate);
      trigger.setUTCHours(9, 0, 0, 0); // fire at 9am local-ish
      const id = await Notifications.scheduleNotificationAsync({
        content: {
          title: plan.title,
          body: plan.body,
          data: { productId: product.id, kind: plan.kind },
        },
        trigger: { date: trigger },
      });
      scheduled.push({ id, productId: product.id, kind: plan.kind, fireDate: plan.fireDate });
    }
    return scheduled;
  }

  async cancel(notificationId: string): Promise<void> {
    await Notifications.cancelScheduledNotificationAsync(notificationId);
  }

  async cancelAll(): Promise<void> {
    await Notifications.cancelAllScheduledNotificationsAsync();
  }
}

function shift(iso: string, days: number): string {
  const d = parseIsoDate(iso);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

export const notificationService = new NotificationService();
