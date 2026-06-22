export function formatCurrency(amount: number, currency = 'USD'): string {
  try {
    return new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency,
      maximumFractionDigits: 2,
    }).format(amount);
  } catch {
    return `$${amount.toFixed(2)}`;
  }
}

export function titleCase(value: string): string {
  return value.replace(/\b\w/g, (c) => c.toUpperCase());
}
