/** Date helpers. All persisted dates are ISO `YYYY-MM-DD` strings. */

export function toIsoDate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

export function parseIsoDate(iso: string): Date {
  // Anchor to midday UTC to avoid timezone off-by-one when displaying.
  return new Date(`${iso}T12:00:00.000Z`);
}

export function addDays(iso: string, days: number): string {
  const d = parseIsoDate(iso);
  d.setUTCDate(d.getUTCDate() + days);
  return toIsoDate(d);
}

export function addMonths(iso: string, months: number): string {
  const d = parseIsoDate(iso);
  d.setUTCMonth(d.getUTCMonth() + months);
  return toIsoDate(d);
}

/** Whole days from today until `iso` (negative if in the past). */
export function daysUntil(iso: string, now: Date = new Date()): number {
  const target = parseIsoDate(iso).getTime();
  const today = parseIsoDate(toIsoDate(now)).getTime();
  return Math.round((target - today) / (1000 * 60 * 60 * 24));
}

export function isFuture(iso: string, now: Date = new Date()): boolean {
  return daysUntil(iso, now) >= 0;
}

export function formatDisplayDate(iso: string | null): string {
  if (!iso) return '—';
  return parseIsoDate(iso).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}
