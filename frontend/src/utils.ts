/**
 * Format a number as ILS currency.
 */
export function formatILS(amount: number): string {
  return new Intl.NumberFormat('he-IL', {
    style: 'currency',
    currency: 'ILS',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)
}

/**
 * Format a number as percentage.
 */
export function formatPercent(value: number, decimals = 2): string {
  return `${value.toFixed(decimals)}%`
}

/**
 * Translate route name to Hebrew.
 */
export function routeNameHebrew(route: string): string {
  const map: Record<string, string> = {
    linear_mutav: 'ליניארי מוטב',
    regular: 'רגיל (מדרגות)',
    linear_with_prisa: 'ליניארי + פריסה',
    linear: 'ליניארי מוטב',
    exempt_49b2: 'פטור 49ב(2)',
  }
  return map[route] ?? route
}

/**
 * Translate currency to Hebrew.
 */
export function currencyLabel(currency: string): string {
  const map: Record<string, string> = {
    ILS: '₪ שקל',
    USD: '$ דולר',
    EUR: '€ אירו',
    GBP: '£ לירה שטרלינג',
    ILP: 'לי"ר ישראלית',
    ILR: 'שקל ישן',
  }
  return map[currency] ?? currency
}
