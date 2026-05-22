/**
 * currency.js — Stratos Garage currency formatting utilities.
 * All monetary values on this platform are in Indian Rupees (INR).
 */

/**
 * Format a numeric value as Indian Rupees with the ₹ symbol.
 * Uses the Indian locale for proper lakh/crore number grouping.
 *
 * Examples:
 *   formatINR(25999)   → "₹25,999"
 *   formatINR(1500000) → "₹15,00,000"
 *   formatINR(0)       → "₹0"
 *   formatINR(null)    → "₹0"
 *
 * @param {number|string|null|undefined} value
 * @param {boolean} [showPaise=false] - Show decimal paise (e.g., ₹25,999.00)
 * @returns {string}
 */
export function formatINR(value, showPaise = false) {
  const num = parseFloat(value) || 0;
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: showPaise ? 2 : 0,
    maximumFractionDigits: showPaise ? 2 : 0,
  }).format(num);
}

/**
 * Quick shorthand — returns the ₹ symbol + raw value without Intl processing.
 * Use for already-formatted strings from the API.
 * @param {string|number} value
 */
export function rupee(value) {
  return `\u20b9${value}`;
}
