/**
 * Formats a number into a localized currency string.
 * @param amount - The number to format
 * @param currency - The currency code (e.g., 'IDR', 'USD')
 * @param locale - The locale string (e.g., 'id-ID', 'en-US')
 */
export function formatCurrency(
  amount: number,
  currency: string = 'IDR',
  locale: string = 'id-ID'
): string {
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(amount);
}