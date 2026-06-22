import { addDays, addMonths, daysUntil, isFuture, toIsoDate } from '../date';

describe('date helpers', () => {
  const now = new Date('2026-06-22T12:00:00.000Z');

  it('formats a Date as ISO date', () => {
    expect(toIsoDate(now)).toBe('2026-06-22');
  });

  it('adds days across month boundaries', () => {
    expect(addDays('2026-06-22', 10)).toBe('2026-07-02');
  });

  it('adds months', () => {
    expect(addMonths('2026-06-22', 12)).toBe('2027-06-22');
  });

  it('computes whole days until a future date', () => {
    expect(daysUntil('2026-06-29', now)).toBe(7);
  });

  it('returns negative days for past dates', () => {
    expect(daysUntil('2026-06-12', now)).toBe(-10);
  });

  it('detects future dates inclusive of today', () => {
    expect(isFuture('2026-06-22', now)).toBe(true);
    expect(isFuture('2026-06-21', now)).toBe(false);
  });
});
